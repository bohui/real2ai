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
from urllib.parse import urlsplit
import socket
from contextlib import asynccontextmanager

# Make backend app imports available


# Ensure we can import app modules if needed later
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


# Load environment variables from common locations
def _load_env_files() -> None:
    candidates = [
        os.getenv("DOTENV_PATH"),
        # Repo root when running from project root
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env")),
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", ".env.local")
        ),
        # Backend dir
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env.local")),
        # Current working directory
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.getcwd(), ".env.local"),
    ]

    loaded_any = False
    for path in candidates:
        if not path:
            continue
        try:
            if os.path.isfile(path):
                load_dotenv(dotenv_path=path, override=False)
                loaded_any = True
        except Exception:
            # Ignore malformed dotenv files
            pass

    if not loaded_any:
        # Fallback to default behavior (loads from CWD if present)
        load_dotenv()


_load_env_files()


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
    "analyses",
    # User-scoped document processing tables (depend on documents)
    "user_document_paragraphs",
    "user_document_diagrams",
    "user_document_pages",
    # Legacy document-derived tables (may still exist in some databases)
    "document_analyses",
    "document_diagrams",
    "document_entities",
    "document_pages",
    # Task registry and checkpoints
    "task_checkpoints",
    "task_registry",
    # Property system tables (children first, then parents)
    "user_saved_properties",
    "property_searches",
    "property_reports",
    "property_api_usage",
    "market_insights",
    "property_valuations",
    "property_market_data",
    "property_risk_assessments",
    "comparable_sales",
    "property_sales_history",
    "property_rental_history",
    # Parent tables
    "properties",
    "contracts",
    "documents",
    # Shared artifact tables (content-addressed cache - no foreign keys)
    "artifact_paragraphs",
    "artifact_diagrams",
    "artifact_pages",
    "text_extraction_artifacts",
    # Other shared tables
    "usage_logs",
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
    db_url: str | None
    use_service_role: bool = True

    async def _table_exists(self, conn: asyncpg.Connection, table: str) -> bool:
        """Check table existence without raising when missing.

        Uses to_regclass which returns NULL if the relation does not exist.
        """
        try:
            exists = await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", table)
            return bool(exists)
        except Exception as e:
            # If existence check itself fails, be conservative and treat as missing
            logger.debug(f"Existence check failed for {table}: {e}")
            return False

    @asynccontextmanager
    async def _direct_connection(self):
        if not self.db_url:
            raise ValueError("DATABASE_URL not configured for direct connection mode")
        conn = await asyncpg.connect(self.db_url)
        try:
            yield conn
        finally:
            await conn.close()

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
        # Import here to avoid heavy imports when not needed
        from app.database.connection import get_service_role_connection

        connection_ctx = (
            get_service_role_connection()
            if self.use_service_role
            else self._direct_connection()
        )

        async with connection_ctx as conn:
            for table in tables:
                try:
                    # Skip quickly if table doesn't exist to avoid transaction aborts
                    if not await self._table_exists(conn, table):
                        logger.info(f"Skipping missing table: {table}")
                        continue

                    count_before = await self._get_row_count(conn, table)
                    logger.info(f"Deleting from {table} (rows before: {count_before})")
                    async with conn.transaction():
                        await conn.execute(f"DELETE FROM {table}")

                    count_after = await self._get_row_count(conn, table)
                    if count_after == 0:
                        logger.info(f"Cleared {table}")
                    else:
                        logger.warning(
                            f"{table} still has {count_after} rows after delete"
                        )
                except asyncpg.exceptions.UndefinedTableError:
                    logger.info(f"Skipping missing table: {table}")
                except Exception as e:
                    logger.error(f"Error clearing table {table}: {e}")

    async def clear_with_truncate(
        self, tables: Sequence[str], restart_identity: bool = True
    ) -> None:
        """Fast truncate with CASCADE across selected tables.

        Note: CASCADE may remove referencing rows in other tables; use with care.
        """
        from app.database.connection import get_service_role_connection

        connection_ctx = (
            get_service_role_connection()
            if self.use_service_role
            else self._direct_connection()
        )

        async with connection_ctx as conn:
            opts = []
            if restart_identity:
                opts.append("RESTART IDENTITY")
            opts.append("CASCADE")
            opts_sql = " ".join(opts)

            for table in tables:
                try:
                    if not await self._table_exists(conn, table):
                        logger.info(f"Skipping missing table during TRUNCATE: {table}")
                        continue
                    async with conn.transaction():
                        logger.warning("Executing TRUNCATE on: %s", table)
                        await conn.execute(f"TRUNCATE TABLE {table} {opts_sql}")
                except asyncpg.exceptions.UndefinedTableError:
                    logger.info(f"Skipping missing table during TRUNCATE: {table}")
                except Exception as e:
                    logger.error(f"Error truncating table {table}: {e}")


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
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--service",
        dest="service",
        action="store_true",
        help="Use application service-role connection (default)",
    )
    group.add_argument(
        "--no-service",
        dest="service",
        action="store_false",
        help="Use direct DATABASE_URL connection",
    )
    parser.set_defaults(service=True)

    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    def _build_db_url_from_supabase_env() -> str | None:
        supabase_url = os.getenv("SUPABASE_URL", "").strip()
        service_key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
        if not supabase_url or not service_key:
            return None
        # Extract the project id from the Supabase URL
        host = supabase_url.replace("https://", "").replace("http://", "").strip()
        if not host or "." not in host:
            return None
        project_id = host.split(".")[0]
        if not project_id:
            return None
        return f"postgresql://postgres:{service_key}@db.{project_id}.supabase.co:5432/postgres"

    def _sanitize_dsn(dsn: str) -> str:
        try:
            parts = urlsplit(dsn)
            # Mask password if present
            netloc = parts.netloc
            if "@" in netloc:
                creds, hostpart = netloc.split("@", 1)
                if ":" in creds:
                    user, _pwd = creds.split(":", 1)
                    netloc = f"{user}:***@{hostpart}"
                else:
                    netloc = f"***@{hostpart}"
            masked = parts._replace(netloc=netloc).geturl()
            return masked
        except Exception:
            return "[unable to sanitize DSN]"

    # Resolve connection mode and DSN
    use_service_role = args.service

    db_url = None
    if not use_service_role:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            fallback = _build_db_url_from_supabase_env()
            if fallback:
                db_url = fallback
                logger.info(
                    "Using database URL derived from Supabase environment variables"
                )
            else:
                logger.error(
                    "DATABASE_URL not set and could not derive from SUPABASE_URL/SUPABASE_SERVICE_KEY"
                )
                sys.exit(1)

        # Basic hostname validation to provide clearer errors before connecting
        try:
            parts = urlsplit(db_url)
            hostname = parts.hostname
            if not hostname:
                raise ValueError("No hostname found in DATABASE_URL")
            socket.getaddrinfo(hostname, None)
        except Exception as e:
            # If local Docker host alias fails on host, try rewriting to 127.0.0.1
            try:
                parts = urlsplit(db_url)
                if parts.hostname in {
                    "host.docker.internal",
                    "docker.for.mac.host.internal",
                }:
                    netloc = parts.netloc.replace(parts.hostname, "127.0.0.1")
                    db_url = parts._replace(netloc=netloc).geturl()
                    logger.warning(
                        "Rewriting DATABASE_URL host %s to 127.0.0.1 for local resolution",
                        parts.hostname,
                    )
                else:
                    raise e
            except Exception:
                logger.error(
                    "Invalid or unreachable database host in DATABASE_URL: %s | Error: %s",
                    _sanitize_dsn(db_url),
                    e,
                )
                sys.exit(1)
    else:
        # For service-role mode, patch env if local Docker host alias is present to avoid DNS issues
        env_db_url = os.getenv("DATABASE_URL", "")
        if env_db_url:
            try:
                parts = urlsplit(env_db_url)
                if parts.hostname in {
                    "host.docker.internal",
                    "docker.for.mac.host.internal",
                }:
                    patched = parts._replace(
                        netloc=parts.netloc.replace(parts.hostname, "127.0.0.1")
                    ).geturl()
                    os.environ["DATABASE_URL"] = patched
                    logger.warning(
                        "Patched DATABASE_URL host %s to 127.0.0.1 for service-role connection",
                        parts.hostname,
                    )
            except Exception:
                pass

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

    cleaner = DatabaseCleaner(db_url=db_url, use_service_role=use_service_role)

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
