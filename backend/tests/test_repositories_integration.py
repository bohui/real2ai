"""
Integration tests for repository pattern migration

These tests validate that the new repository pattern works correctly
with JWT-based RLS enforcement and connection management.
"""

import pytest
import asyncio
from uuid import UUID, uuid4
from datetime import datetime, timezone

from app.services.repositories import (
    DocumentsRepository,
    ContractsRepository,
    AnalysesRepository,
)
from app.database.connection import ConnectionPoolManager
from app.core.auth_context import AuthContext
from app.core.config import get_settings


@pytest.fixture
async def setup_auth_context():
    """Setup test auth context"""
    test_user_id = str(uuid4())
    test_token = "test_jwt_token"

    AuthContext.set_auth_context(token=test_token, user_id=test_user_id)

    yield test_user_id

    # Cleanup
    AuthContext.clear_auth_context()


@pytest.fixture
async def cleanup_pools():
    """Cleanup connection pools after tests"""
    yield
    await ConnectionPoolManager.close_all()


class TestDocumentsRepository:
    """Test DocumentsRepository functionality"""

    async def test_create_document(self, setup_auth_context, cleanup_pools):
        """Test document creation with repository"""
        user_id = UUID(setup_auth_context)
        repo = DocumentsRepository(user_id)

        document_data = {
            "filename": "test_document.pdf",
            "original_filename": "Original Test Document.pdf",
            "file_size": 1024000,
            "content_type": "application/pdf",
            "processing_status": "pending",
        }

        # Create document
        document = await repo.create_document(document_data)

        assert document is not None
        assert document.filename == "test_document.pdf"
        assert document.user_id == user_id
        assert document.processing_status == "pending"

    async def test_update_document_status(self, setup_auth_context, cleanup_pools):
        """Test document status updates"""
        user_id = UUID(setup_auth_context)
        repo = DocumentsRepository(user_id)

        # Create a document first
        document_data = {
            "filename": "status_test.pdf",
            "original_filename": "Status Test.pdf",
            "file_size": 500000,
            "content_type": "application/pdf",
        }

        document = await repo.create_document(document_data)

        # Update status
        success = await repo.update_document_status(
            document.id, "processing", processing_started_at=datetime.now(timezone.utc)
        )

        assert success is True

        # Verify update
        updated_document = await repo.get_document(document.id)
        assert updated_document.processing_status == "processing"
        assert updated_document.processing_started_at is not None

    async def test_list_user_documents(self, setup_auth_context, cleanup_pools):
        """Test listing user documents with filtering"""
        user_id = UUID(setup_auth_context)
        repo = DocumentsRepository(user_id)

        # Create multiple documents
        for i in range(3):
            document_data = {
                "filename": f"list_test_{i}.pdf",
                "original_filename": f"List Test {i}.pdf",
                "file_size": 100000 + i * 1000,
                "content_type": "application/pdf",
                "processing_status": "completed" if i % 2 == 0 else "pending",
            }
            await repo.create_document(document_data)

        # List all documents
        all_documents = await repo.list_user_documents(limit=10)
        assert len(all_documents) >= 3

        # List only completed documents
        completed_documents = await repo.list_user_documents(
            limit=10, status_filter="completed"
        )
        assert len(completed_documents) >= 2
        assert all(doc.processing_status == "completed" for doc in completed_documents)


class TestContractsRepository:
    """Test ContractsRepository functionality"""

    async def test_upsert_contract_by_content_hash(self, cleanup_pools):
        """Test contract upsert functionality"""
        repo = ContractsRepository()

        content_hash = f"test_hash_{uuid4().hex}"
        contract_type = "rental_agreement"
        australian_state = "NSW"

        # First upsert
        contract1 = await repo.upsert_contract_by_content_hash(
            content_hash=content_hash,
            contract_type=contract_type,
            state=australian_state,
            updated_by="tests_integration",
        )

        assert contract1 is not None
        assert contract1.content_hash == content_hash
        assert contract1.contract_type == contract_type
        assert contract1.australian_state == australian_state

        # Second upsert with same hash should return same contract
        contract2 = await repo.upsert_contract_by_content_hash(
            content_hash=content_hash,
            contract_type=contract_type,
            state=australian_state,
            updated_by="tests_integration",
        )

        assert contract1.id == contract2.id

    async def test_get_contract_by_content_hash(self, cleanup_pools):
        """Test retrieving contract by content hash"""
        repo = ContractsRepository()

        content_hash = f"retrieve_test_{uuid4().hex}"

        # Create contract
        created_contract = await repo.upsert_contract_by_content_hash(
            content_hash=content_hash,
            contract_type="lease_agreement",
            state="VIC",
            updated_by="tests_integration",
        )

        # Retrieve contract
        retrieved_contract = await repo.get_contract_by_content_hash(content_hash)

        assert retrieved_contract is not None
        assert retrieved_contract.id == created_contract.id
        assert retrieved_contract.content_hash == content_hash

        # Test non-existent contract
        non_existent = await repo.get_contract_by_content_hash("non_existent_hash")
        assert non_existent is None


class TestAnalysesRepository:
    """Test AnalysesRepository functionality"""

    async def test_upsert_analysis_service_role(self, cleanup_pools):
        """Test analysis upsert with service role"""
        repo = AnalysesRepository(use_service_role=True)

        content_hash = f"analysis_test_{uuid4().hex}"
        agent_version = "2.0"

        # Create analysis
        analysis = await repo.upsert_analysis(
            content_hash=content_hash,
            agent_version=agent_version,
            status="pending",
            result={"initial": "data"},
        )

        assert analysis is not None
        assert analysis.content_hash == content_hash
        assert analysis.agent_version == agent_version
        assert analysis.status == "pending"
        assert analysis.result == {"initial": "data"}

    async def test_upsert_analysis_user_scoped(self, setup_auth_context, cleanup_pools):
        """Test analysis upsert with user scope"""
        user_id = UUID(setup_auth_context)
        repo = AnalysesRepository(user_id=user_id, use_service_role=False)

        content_hash = f"user_analysis_{uuid4().hex}"
        agent_version = "1.5"

        # Create user-scoped analysis
        analysis = await repo.upsert_analysis(
            content_hash=content_hash,
            agent_version=agent_version,
            status="completed",
            result={"analysis": "complete", "score": 95},
        )

        assert analysis is not None
        assert analysis.content_hash == content_hash
        assert analysis.status == "completed"
        # User ID should be set for user-scoped analyses
        assert analysis.user_id is not None

    async def test_update_analysis_status(self, cleanup_pools):
        """Test updating analysis status and results"""
        repo = AnalysesRepository(use_service_role=True)

        content_hash = f"status_update_{uuid4().hex}"

        # Create analysis
        analysis = await repo.upsert_analysis(
            content_hash=content_hash, agent_version="1.0", status="processing"
        )

        # Update status and result
        success = await repo.update_analysis_status(
            analysis.id,
            status="completed",
            result={"final": "analysis", "confidence": 0.95},
            completed_at=datetime.now(timezone.utc),
        )

        assert success is True

        # Verify update
        updated_analysis = await repo.get_analysis_by_id(analysis.id)
        assert updated_analysis.status == "completed"
        assert updated_analysis.result == {"final": "analysis", "confidence": 0.95}
        assert updated_analysis.completed_at is not None


class TestConnectionPoolManagement:
    """Test connection pool functionality"""

    async def test_shared_pool_mode(self, setup_auth_context, cleanup_pools):
        """Test shared pool mode with session GUCs"""
        settings = get_settings()
        original_mode = settings.db_pool_mode

        try:
            # Force shared mode
            settings.db_pool_mode = "shared"

            user_id = UUID(setup_auth_context)
            repo = DocumentsRepository(user_id)

            # This should use shared pool with session GUCs
            document_data = {
                "filename": "shared_pool_test.pdf",
                "original_filename": "Shared Pool Test.pdf",
                "file_size": 256000,
                "content_type": "application/pdf",
            }

            document = await repo.create_document(document_data)
            assert document is not None
            assert document.user_id == user_id

        finally:
            settings.db_pool_mode = original_mode

    async def test_pool_metrics(self, cleanup_pools):
        """Test connection pool metrics"""
        metrics = ConnectionPoolManager.get_metrics()

        assert isinstance(metrics, dict)
        assert "active_user_pools" in metrics
        assert "evictions" in metrics
        assert "pool_hits" in metrics
        assert "pool_misses" in metrics

        # Metrics should be non-negative integers
        for key, value in metrics.items():
            assert isinstance(value, int)
            assert value >= 0


class TestRLSEnforcement:
    """Test Row Level Security enforcement"""

    async def test_user_isolation(self, cleanup_pools):
        """Test that users can only access their own documents"""
        # Create two different users
        user1_id = uuid4()
        user2_id = uuid4()

        # Setup auth context for user1
        AuthContext.set_auth_context(token="user1_token", user_id=str(user1_id))

        try:
            repo1 = DocumentsRepository(user1_id)

            # User1 creates a document
            document_data = {
                "filename": "user1_document.pdf",
                "original_filename": "User1 Document.pdf",
                "file_size": 100000,
                "content_type": "application/pdf",
            }

            user1_document = await repo1.create_document(document_data)
            assert user1_document.user_id == user1_id

            # Switch to user2 context
            AuthContext.set_auth_context(token="user2_token", user_id=str(user2_id))

            repo2 = DocumentsRepository(user2_id)

            # User2 should not be able to see user1's document
            user2_documents = await repo2.list_user_documents()
            user1_doc_ids = [
                doc.id for doc in user2_documents if doc.id == user1_document.id
            ]
            assert len(user1_doc_ids) == 0, "User2 should not see User1's documents"

            # User2 should not be able to get user1's document directly
            user1_doc_via_user2 = await repo2.get_document(user1_document.id)
            assert (
                user1_doc_via_user2 is None
            ), "User2 should not access User1's document by ID"

        finally:
            AuthContext.clear_auth_context()


@pytest.mark.asyncio
async def test_repository_integration_flow():
    """
    End-to-end integration test simulating document processing flow
    """
    user_id = uuid4()

    # Setup auth context
    AuthContext.set_auth_context(token="integration_test_token", user_id=str(user_id))

    try:
        # Initialize repositories
        docs_repo = DocumentsRepository(user_id)
        contracts_repo = ContractsRepository()
        analyses_repo = AnalysesRepository(use_service_role=True)

        # 1. Create document
        document_data = {
            "filename": "integration_contract.pdf",
            "original_filename": "Integration Test Contract.pdf",
            "file_size": 512000,
            "content_type": "application/pdf",
            "processing_status": "pending",
        }

        document = await docs_repo.create_document(document_data)
        assert document.processing_status == "pending"

        # 2. Update document to processing
        await docs_repo.update_document_status(
            document.id, "processing", processing_started_at=datetime.now(timezone.utc)
        )

        # 3. Create contract record
        content_hash = f"integration_{document.id.hex}"
        contract = await contracts_repo.upsert_contract_by_content_hash(
            content_hash=content_hash,
            contract_type="lease_agreement",
            state="QLD",
            updated_by="tests_integration",
        )

        # 4. Create analysis
        analysis = await analyses_repo.upsert_analysis(
            content_hash=content_hash, agent_version="2.1", status="processing"
        )

        # 5. Complete analysis
        await analyses_repo.update_analysis_status(
            analysis.id,
            status="completed",
            result={
                "contract_type": "lease_agreement",
                "key_terms": ["rent", "duration", "deposit"],
                "compliance_score": 0.92,
            },
            completed_at=datetime.now(timezone.utc),
        )

        # 6. Complete document processing
        await docs_repo.update_document_status(
            document.id, "completed", processing_completed_at=datetime.now(timezone.utc)
        )

        await docs_repo.update_document_metrics(
            document.id, {"total_pages": 12, "total_word_count": 3456}
        )

        # 7. Verify final state
        final_document = await docs_repo.get_document(document.id)
        final_analysis = await analyses_repo.get_analysis_by_content_hash(content_hash)

        assert final_document.processing_status == "completed"
        assert final_document.total_pages == 12
        assert final_document.total_word_count == 3456
        assert final_analysis.status == "completed"
        assert final_analysis.result["compliance_score"] == 0.92

    finally:
        AuthContext.clear_auth_context()
        await ConnectionPoolManager.close_all()


if __name__ == "__main__":
    # Run basic smoke test
    asyncio.run(test_repository_integration_flow())
    print("Repository integration tests completed successfully!")
