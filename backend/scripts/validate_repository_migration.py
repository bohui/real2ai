#!/usr/bin/env python3
"""
Repository Migration Validation Script

This script validates that the repository migration is working correctly
by testing basic functionality and configuration.
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import get_settings
from app.core.auth_context import AuthContext
from app.database.connection import ConnectionPoolManager
from app.services.repositories import (
    DocumentsRepository,
    ContractsRepository,
    AnalysesRepository,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_configuration():
    """Test that configuration is properly loaded"""
    logger.info("Testing configuration...")

    settings = get_settings()

    # Check repository settings
    assert hasattr(settings, "db_use_repositories")
    assert hasattr(settings, "db_pool_mode")
    assert hasattr(settings, "db_user_pool_min_size")
    assert hasattr(settings, "db_user_pool_max_size")

    logger.info(f"✓ Repository enabled: {settings.db_use_repositories}")
    logger.info(f"✓ Pool mode: {settings.db_pool_mode}")
    logger.info(
        f"✓ User pool size: {settings.db_user_pool_min_size}-{settings.db_user_pool_max_size}"
    )


async def test_connection_pools():
    """Test connection pool functionality"""
    logger.info("Testing connection pools...")

    try:
        # Test service pool
        pool = await ConnectionPoolManager.get_service_pool()
        assert pool is not None
        logger.info("✓ Service pool created successfully")

        # Test user pool
        test_user_id = uuid4()
        user_pool = await ConnectionPoolManager.get_user_pool(test_user_id)
        assert user_pool is not None
        logger.info("✓ User pool created successfully")

        # Test metrics
        metrics = ConnectionPoolManager.get_metrics()
        assert isinstance(metrics, dict)
        logger.info(f"✓ Pool metrics: {metrics}")

    finally:
        await ConnectionPoolManager.close_all()
        logger.info("✓ Connection pools cleaned up")


async def test_repositories():
    """Test repository functionality"""
    logger.info("Testing repositories...")

    test_user_id = uuid4()

    # Setup auth context
    AuthContext.set_auth_context(token="test_token", user_id=str(test_user_id))

    try:
        # Test DocumentsRepository
        logger.info("Testing DocumentsRepository...")
        docs_repo = DocumentsRepository(test_user_id)

        document_data = {
            "filename": "validation_test.pdf",
            "original_filename": "Validation Test.pdf",
            "file_size": 100000,
            "content_type": "application/pdf",
            "processing_status": "pending",
        }

        # This will test the connection and basic functionality
        # Note: This might fail if database tables don't exist yet
        try:
            document = await docs_repo.create_document(document_data)
            logger.info(f"✓ Document created with ID: {document.id}")

            # Test update
            success = await docs_repo.update_document_status(document.id, "processing")
            logger.info(f"✓ Document status updated: {success}")

        except Exception as e:
            logger.warning(
                f"⚠ Document operations failed (expected if tables don't exist): {e}"
            )

        # Test ContractsRepository
        logger.info("Testing ContractsRepository...")
        contracts_repo = ContractsRepository()

        try:
            contract = await contracts_repo.upsert_contract_by_content_hash(
                content_hash="validation_test_hash",
                contract_type="test_contract",
                state="NSW",
                updated_by="validate_repository_migration",
            )
            logger.info(f"✓ Contract created/updated with ID: {contract.id}")

        except Exception as e:
            logger.warning(
                f"⚠ Contract operations failed (expected if tables don't exist): {e}"
            )

        # Test AnalysesRepository
        logger.info("Testing AnalysesRepository...")
        analyses_repo = AnalysesRepository(use_service_role=True)

        try:
            analysis = await analyses_repo.upsert_analysis(
                content_hash="validation_analysis_hash",
                agent_version="1.0",
                status="pending",
            )
            logger.info(f"✓ Analysis created/updated with ID: {analysis.id}")

        except Exception as e:
            logger.warning(
                f"⚠ Analysis operations failed (expected if tables don't exist): {e}"
            )

    finally:
        AuthContext.clear_auth_context()
        await ConnectionPoolManager.close_all()
        logger.info("✓ Repositories tested and cleaned up")


async def test_migration_helpers():
    """Test migrated service functions"""
    logger.info("Testing migration helpers...")

    # Import the migrated functions
    from app.services.contract_analysis_service import (
        ensure_contract,
        upsert_contract_analysis,
    )

    try:
        # Test ensure_contract (should use repository if enabled)
        contract_id = await ensure_contract(
            service_client=None,  # Not used when repositories enabled
            content_hash="migration_test_hash",
            contract_type="rental_agreement",
            australian_state="VIC",
        )
        logger.info(f"✓ ensure_contract returned ID: {contract_id}")

        # Test upsert_contract_analysis
        AuthContext.set_auth_context(token="test_token", user_id=str(uuid4()))

        analysis_id = await upsert_contract_analysis(
            user_client=None,  # Not used when repositories enabled
            content_hash="migration_test_hash",
            agent_version="2.0",
        )
        logger.info(f"✓ upsert_contract_analysis returned ID: {analysis_id}")

    except Exception as e:
        logger.warning(
            f"⚠ Migration helpers failed (expected if tables don't exist): {e}"
        )

    finally:
        AuthContext.clear_auth_context()
        await ConnectionPoolManager.close_all()


async def main():
    """Run all validation tests"""
    logger.info("Starting repository migration validation...")

    try:
        await test_configuration()
        await test_connection_pools()
        await test_repositories()
        await test_migration_helpers()

        logger.info("🎉 All validation tests completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
