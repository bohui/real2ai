#!/usr/bin/env python3
"""
Database Clear Script for Real2.AI
Safely clears selected application tables for development/testing.

Usage examples:
  python clear_data.py                          # interactive confirm, safe delete mode
  python clear_data.py --yes                    # non-interactive, safe delete mode
  python clear_data.py --truncate --yes         # fast TRUNCATE CASCADE across selected tables
  python clear_data.py --tables documents,contracts --yes  # clear subset in dependency-safe order
"""

import os
import sys
import argparse
import asyncio
import logging
from dataclasses import dataclass
from typing import List, Sequence

import asyncpg
from dotenv import load_dotenv


# Ensure we can import app modules if needed later
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


# Load environment variables
load_dotenv()


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Dependency-safe deletion order: children first, then parents
DEFAULT_TABLE_ORDER: List[str] = [
    # Views and progress records referencing contracts/property
    "user_contract_views",
    "user_property_views",
    "analysis_progress",
    # Contract analysis data that depends on contracts/content_hash
    "contract_analyses",
    # Document-derived tables that depend on documents
    "document_analyses",
    "document_diagrams",
    "document_entities",
    "document_pages",
    # Task registry (independent; kept before parents just in case)
    "task_registry",
    # Parents last
    "contract_analyses",  # kept once above; harmless if repeated in TRUNCATE set
    "contracts",
    "documents",
]


def normalize_tables(tables_arg: str | None) -> List[str]:
    if not tables_arg:
        # Deduplicate while preserving order
        seen = set()
        ordered = []
        for t in DEFAULT_TABLE_ORDER:
            if t not in seen:
                seen.add(t)
                ordered.append(t)
        return ordered

    requested = [t.strip() for t in tables_arg.split(",") if t.strip()]
    # Validate and order by dependency order where possible
    order_index = {t: i for i, t in enumerate(DEFAULT_TABLE_ORDER)}
    unknown = [t for t in requested if t not in order_index]
    if unknown:
        raise ValueError(f"Unknown tables requested: {', '.join(unknown)}")
    # Sort requested by the known dependency-safe order
    return sorted(requested, key=lambda t: order_index[t])


@dataclass
class DatabaseCleaner:
    db_url: str

    async def get_db_connection(self) -> asyncpg.Connection:
        if not self.db_url:
            raise ValueError("DATABASE_URL not configured")
        return await asyncpg.connect(self.db_url)

    async def _get_row_count(self, conn: asyncpg.Connection, table: str) -> int:
        try:
            row = await conn.fetchrow(f"SELECT COUNT(*) AS count FROM {table}")
            return int(row["count"]) if row is not None else 0
        except Exception as e:
            logger.debug(f"Count failed for {table}: {e}")
            return -1

    async def clear_with_delete(self, tables: Sequence[str]) -> None:
        """Delete rows in dependency-safe order.

        This avoids unintended cascading into unrelated tables.
        """
        conn = await self.get_db_connection()
        try:
            async with conn.transaction():
                for table in tables:
                    count_before = await self._get_row_count(conn, table)
                    logger.info(f"Deleting from {table} (rows before: {count_before})")
                    await conn.execute(f"DELETE FROM {table}")
                    count_after = await self._get_row_count(conn, table)
                    if count_after == 0:
                        logger.info(f"Cleared {table}")
                    else:
                        logger.warning(
                            f"{table} still has {count_after} rows after delete"
                        )
        finally:
            await conn.close()

    async def clear_with_truncate(
        self, tables: Sequence[str], restart_identity: bool = True
    ) -> None:
        """Fast truncate with CASCADE across selected tables.

        Note: CASCADE may remove referencing rows in other tables; use with care.
        """
        conn = await self.get_db_connection()
        try:
            async with conn.transaction():
                opts = []
                if restart_identity:
                    opts.append("RESTART IDENTITY")
                opts.append("CASCADE")
                opts_sql = " ".join(opts)
                tables_sql = ", ".join(tables)
                logger.warning("Executing TRUNCATE on: %s", tables_sql)
                await conn.execute(f"TRUNCATE TABLE {tables_sql} {opts_sql}")
        finally:
            await conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clear selected application tables in the Real2.AI database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python clear_data.py --yes
  python clear_data.py --truncate --yes
  python clear_data.py --tables documents,contracts --yes
        """,
    )

    parser.add_argument(
        "--tables",
        help="Comma-separated list of tables to clear (defaults to safe dependency order)",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Use TRUNCATE ... CASCADE (fast, may cascade into other tables)",
    )
    parser.add_argument(
        "--no-restart-identity",
        action="store_true",
        help="When using --truncate, do not RESTART IDENTITY",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip interactive confirmation",
    )

    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set in environment")
        sys.exit(1)

    # Resolve target tables and ensure dependency-safe order
    tables = normalize_tables(args.tables)

    # Final confirmation
    if not args.yes:
        mode = "TRUNCATE (CASCADE)" if args.truncate else "DELETE"
        print("\n⚠️  You are about to CLEAR data from the following tables (in order):")
        for t in tables:
            print(f"  - {t}")
        print(f"\nMode: {mode}")
        confirm = input("Type 'CLEAR' to confirm: ")
        if confirm.strip() != "CLEAR":
            print("Operation cancelled")
            return

    cleaner = DatabaseCleaner(db_url=db_url)

    try:
        if args.truncate:
            await cleaner.clear_with_truncate(
                tables, restart_identity=not args.no_restart_identity
            )
        else:
            await cleaner.clear_with_delete(tables)
        logger.info("✅ Data clearing completed successfully")
    except Exception as e:
        logger.error(f"❌ Data clearing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
