#!/usr/bin/env python3
"""
Supabase Migration Management Script for Real2.AI
Handles database migrations, rollbacks, and schema management
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

import asyncio
import asyncpg
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages Supabase database migrations for Real2.AI"""

    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.db_url = os.getenv("DATABASE_URL")

        if not all([self.supabase_url, self.supabase_key]):
            raise ValueError(
                "Missing required environment variables: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY"
            )

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.migrations_dir = (
            Path(__file__).parent.parent.parent / "supabase" / "migrations"
        )

        # Ensure migrations directory exists
        self.migrations_dir.mkdir(parents=True, exist_ok=True)

    async def get_db_connection(self):
        """Get direct database connection for complex operations"""
        if not self.db_url:
            raise ValueError("DATABASE_URL not configured")
        return await asyncpg.connect(self.db_url)

    def get_migration_files(self) -> List[Path]:
        """Get all migration files sorted by timestamp"""
        migration_files = list(self.migrations_dir.glob("*.sql"))
        return sorted(migration_files)

    async def create_migration_table(self):
        """Create migration tracking table if it doesn't exist"""
        conn = await self.get_db_connection()
        try:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    execution_time_ms INTEGER,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                );
            """
            )
            logger.info("Migration tracking table ready")
        finally:
            await conn.close()

    def calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of migration file"""
        import hashlib

        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    async def get_applied_migrations(self) -> Dict[str, Dict]:
        """Get list of already applied migrations"""
        conn = await self.get_db_connection()
        try:
            rows = await conn.fetch(
                """
                SELECT version, filename, checksum, executed_at, success, error_message
                FROM schema_migrations
                ORDER BY version
            """
            )
            return {row["version"]: dict(row) for row in rows}
        except asyncpg.UndefinedTableError:
            logger.info("Migration table doesn't exist yet")
            return {}
        finally:
            await conn.close()

    async def apply_migration(self, file_path: Path) -> bool:
        """Apply a single migration file"""
        version = file_path.stem
        filename = file_path.name
        checksum = self.calculate_file_checksum(file_path)

        logger.info(f"Applying migration: {filename}")

        conn = await self.get_db_connection()
        start_time = datetime.now()

        try:
            # Read and execute migration
            with open(file_path, "r", encoding="utf-8") as f:
                migration_sql = f.read()

            # Execute in transaction
            async with conn.transaction():
                await conn.execute(migration_sql)

                # Record successful migration
                execution_time = int(
                    (datetime.now() - start_time).total_seconds() * 1000
                )
                await conn.execute(
                    """
                    INSERT INTO schema_migrations (version, filename, checksum, execution_time_ms, success)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (version) DO UPDATE SET
                        checksum = EXCLUDED.checksum,
                        execution_time_ms = EXCLUDED.execution_time_ms,
                        executed_at = NOW(),
                        success = EXCLUDED.success,
                        error_message = NULL
                """,
                    version,
                    filename,
                    checksum,
                    execution_time,
                    True,
                )

            logger.info(f"✅ Successfully applied {filename} ({execution_time}ms)")
            return True

        except Exception as e:
            # Record failed migration
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            error_message = str(e)

            try:
                await conn.execute(
                    """
                    INSERT INTO schema_migrations (version, filename, checksum, execution_time_ms, success, error_message)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (version) DO UPDATE SET
                        error_message = EXCLUDED.error_message,
                        success = FALSE,
                        executed_at = NOW()
                """,
                    version,
                    filename,
                    checksum,
                    execution_time,
                    False,
                    error_message,
                )
            except:
                pass  # If we can't log the error, continue

            logger.error(f"❌ Failed to apply {filename}: {error_message}")
            return False

        finally:
            await conn.close()

    async def migrate_up(self, target_version: Optional[str] = None) -> bool:
        """Apply all pending migrations up to target version"""
        await self.create_migration_table()

        migration_files = self.get_migration_files()
        applied_migrations = await self.get_applied_migrations()

        if not migration_files:
            logger.info("No migration files found")
            return True

        success_count = 0
        total_count = 0

        for migration_file in migration_files:
            version = migration_file.stem

            # Stop if we've reached target version
            if target_version and version > target_version:
                break

            total_count += 1

            # Skip if already applied successfully
            if version in applied_migrations:
                applied_migration = applied_migrations[version]
                if applied_migration["success"]:
                    # Check if file has changed
                    current_checksum = self.calculate_file_checksum(migration_file)
                    if current_checksum == applied_migration["checksum"]:
                        logger.info(
                            f"⏭️  Skipping {migration_file.name} (already applied)"
                        )
                        success_count += 1
                        continue
                    else:
                        logger.warning(
                            f"🔄 Migration {migration_file.name} has changed, re-applying"
                        )
                else:
                    logger.warning(
                        f"🔄 Retrying failed migration {migration_file.name}"
                    )

            # Apply migration
            if await self.apply_migration(migration_file):
                success_count += 1
            else:
                logger.error(f"Migration failed, stopping at {migration_file.name}")
                break

        logger.info(
            f"Migration summary: {success_count}/{total_count} migrations applied successfully"
        )
        return success_count == total_count

    async def migrate_down(self, target_version: str) -> bool:
        """Rollback migrations to target version (not implemented - dangerous)"""
        logger.error("Migration rollback not implemented for safety reasons")
        logger.info("To rollback, manually create a new migration that undoes changes")
        return False

    async def migration_status(self):
        """Show current migration status"""
        await self.create_migration_table()

        migration_files = self.get_migration_files()
        applied_migrations = await self.get_applied_migrations()

        print("\n📊 Migration Status")
        print("=" * 80)

        if not migration_files:
            print("No migration files found")
            return

        print(f"{'Version':<20} {'Filename':<30} {'Status':<10} {'Applied':<20}")
        print("-" * 80)

        for migration_file in migration_files:
            version = migration_file.stem
            filename = migration_file.name

            if version in applied_migrations:
                migration_info = applied_migrations[version]
                if migration_info["success"]:
                    status = "✅ Applied"
                    applied_at = migration_info["executed_at"].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                else:
                    status = "❌ Failed"
                    applied_at = migration_info["executed_at"].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
            else:
                status = "⏳ Pending"
                applied_at = "-"

            print(f"{version:<20} {filename:<30} {status:<10} {applied_at:<20}")

        # Summary
        applied_count = sum(1 for m in applied_migrations.values() if m["success"])
        failed_count = sum(1 for m in applied_migrations.values() if not m["success"])
        pending_count = len(migration_files) - len(applied_migrations)

        print("-" * 80)
        print(
            f"Summary: {applied_count} applied, {failed_count} failed, {pending_count} pending"
        )

    async def reset_database(self):
        """Drop all tables and re-run migrations (DANGEROUS)"""
        if not os.getenv("ALLOW_DATABASE_RESET", "").lower() in ["true", "1", "yes"]:
            logger.error(
                "Database reset not allowed. Set ALLOW_DATABASE_RESET=true to enable"
            )
            return False

        logger.warning("🚨 This will DROP ALL TABLES in the database!")
        confirmation = input("Type 'RESET' to confirm: ")

        if confirmation != "RESET":
            logger.info("Database reset cancelled")
            return False

        conn = await self.get_db_connection()
        try:
            # Drop all tables (be very careful!)
            await conn.execute(
                """
                DROP SCHEMA public CASCADE;
                CREATE SCHEMA public;
                GRANT ALL ON SCHEMA public TO postgres;
                GRANT ALL ON SCHEMA public TO public;
            """
            )
            logger.info("🗑️  Database reset complete")

            # Re-run all migrations
            return await self.migrate_up()

        finally:
            await conn.close()

    def create_migration(self, name: str) -> Path:
        """Create a new migration file"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{name.replace(' ', '_').replace('-', '_')}.sql"
        migration_file = self.migrations_dir / filename

        # Create migration template
        template = f"""-- Migration: {name}
-- Created: {datetime.now().isoformat()}
-- Description: Add your migration description here

-- Add your SQL statements here
-- Example:
-- ALTER TABLE profiles ADD COLUMN new_field TEXT;

-- Don't forget to add appropriate indexes and RLS policies if needed
"""

        with open(migration_file, "w", encoding="utf-8") as f:
            f.write(template)

        logger.info(f"📝 Created migration file: {migration_file}")
        return migration_file


async def main():
    parser = argparse.ArgumentParser(
        description="Supabase Migration Manager for Real2.AI"
    )
    parser.add_argument(
        "command",
        choices=["up", "down", "status", "reset", "create"],
        help="Migration command to execute",
    )
    parser.add_argument("--target", help="Target migration version")
    parser.add_argument(
        "--name", help="Name for new migration (use with create command)"
    )

    args = parser.parse_args()

    try:
        manager = MigrationManager()

        if args.command == "up":
            success = await manager.migrate_up(args.target)
            sys.exit(0 if success else 1)

        elif args.command == "down":
            if not args.target:
                logger.error("Target version required for rollback")
                sys.exit(1)
            success = await manager.migrate_down(args.target)
            sys.exit(0 if success else 1)

        elif args.command == "status":
            await manager.migration_status()

        elif args.command == "reset":
            success = await manager.reset_database()
            sys.exit(0 if success else 1)

        elif args.command == "create":
            if not args.name:
                logger.error("Migration name required for create command")
                sys.exit(1)
            manager.create_migration(args.name)

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
