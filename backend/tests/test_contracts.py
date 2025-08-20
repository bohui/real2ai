"""
Test contract analysis endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.api
class TestContractAnalysis:
    """Test contract analysis functionality"""

    def test_start_contract_analysis_success(
        self, client: TestClient, mock_db_client, sample_document_data
    ):
        """Test successful contract analysis start"""
        from app.router.contracts import get_user_document_service
        from app.main import app as fastapi_app

        # Create mock document service
        mock_document_service = AsyncMock()
        mock_document_service.get_user_client.return_value = mock_db_client

        # Mock the document service dependency
        async def mock_get_user_document_service():
            return mock_document_service

        fastapi_app.dependency_overrides[get_user_document_service] = (
            mock_get_user_document_service
        )

        # Create separate mock chains for each table
        mock_documents_table = MagicMock()
        mock_contracts_table = MagicMock()
        mock_analyses_table = MagicMock()

        # Set up the return values for each table
        def get_table(table_name):
            if table_name == "documents":
                return mock_documents_table
            elif table_name == "contracts":
                return mock_contracts_table
            elif table_name == "analyses":
                return mock_analyses_table
            return MagicMock()

        mock_db_client.table.side_effect = get_table

        # Mock document fetch
        mock_documents_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_document_data]
        )

        # Mock contract creation
        contract_data = {"id": "test-contract-id"}
        mock_contracts_table.insert.return_value.execute.return_value = MagicMock(
            data=[contract_data]
        )

        # Mock analysis creation
        analysis_data = {"id": "test-analysis-id"}
        mock_analyses_table.insert.return_value.execute.return_value = MagicMock(
            data=[analysis_data]
        )

        # Use valid UUID to satisfy repository parsing in router
        valid_doc_id = "00000000-0000-0000-0000-000000000001"
        request_data = {
            "document_id": valid_doc_id,
            "analysis_options": {
                "include_financial_analysis": True,
                "include_risk_assessment": True,
                "include_compliance_check": True,
                "include_recommendations": True,
            },
        }

        try:
            # Patch repository calls, task manager, background task, and notifications to avoid external deps
            with (
                patch(
                    "app.router.contracts.DocumentsRepository.get_document",
                    new_callable=AsyncMock,
                ) as mock_get_document,
                patch(
                    "app.router.contracts.ContractsRepository.upsert_contract_by_content_hash",
                    new_callable=AsyncMock,
                ) as mock_upsert_contract,
                patch(
                    "app.router.contracts.AnalysesRepository.upsert_analysis",
                    new_callable=AsyncMock,
                ) as mock_upsert_analysis,
                patch(
                    "app.core.task_context.task_manager.initialize",
                    new_callable=AsyncMock,
                ) as mock_tm_init,
                patch(
                    "app.core.task_context.task_manager.launch_user_task",
                    new_callable=AsyncMock,
                ) as mock_launch,
                patch(
                    "app.router.contracts.notification_system.send_notification",
                    new_callable=AsyncMock,
                ) as mock_notify,
                patch(
                    "app.tasks.background_tasks.comprehensive_document_analysis",
                    new_callable=AsyncMock,
                ) as mock_bg_task,
            ):

                fake_doc = MagicMock()
                fake_doc.id = valid_doc_id
                fake_doc.user_id = "00000000-0000-0000-0000-000000000002"
                fake_doc.original_filename = sample_document_data.get(
                    "filename", "test.pdf"
                )
                fake_doc.storage_path = sample_document_data.get(
                    "storage_path", "documents/path.pdf"
                )
                fake_doc.file_type = sample_document_data.get("file_type", "pdf")
                fake_doc.file_size = sample_document_data.get("file_size", 1024)
                fake_doc.content_hash = "abc123"
                fake_doc.processing_status = "uploaded"
                mock_get_document.return_value = fake_doc

                mock_upsert_contract.return_value = MagicMock(id="test-contract-id")
                mock_upsert_analysis.return_value = MagicMock(id="test-analysis-id")
                mock_tm_init.return_value = None
                mock_launch.return_value = MagicMock(id="task-123")
                mock_notify.return_value = None

                response = client.post("/api/contracts/analyze", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["contract_id"] == "test-contract-id"
            assert data["analysis_id"] == "test-analysis-id"
            # Endpoint queues work; expect queued status and eta=3
            assert data["status"] == "queued"
            assert data["estimated_completion_minutes"] == 3
        finally:
            # Clean up dependency override
            fastapi_app.dependency_overrides.pop(get_user_document_service, None)

    def test_start_contract_analysis_no_credits(self, client: TestClient):
        """Test contract analysis with no credits remaining"""
        # Override the dependency to return a user with no credits
        from app.core.auth import get_current_user, User
        from app.router.contracts import get_user_document_service
        from app.main import app as fastapi_app

        def no_credits_user():
            return User(
                id="test-user-id",
                email="test@real2ai.com",
                australian_state="NSW",
                user_type="lawyer",
                subscription_status="free",
                credits_remaining=0,  # No credits
                preferences={},
            )

        # Create mock document service
        mock_document_service = AsyncMock()

        # Mock the document service dependency
        async def mock_get_user_document_service():
            return mock_document_service

        fastapi_app.dependency_overrides[get_current_user] = no_credits_user
        fastapi_app.dependency_overrides[get_user_document_service] = (
            mock_get_user_document_service
        )

        try:
            request_data = {
                "document_id": "test-doc-id",
                "analysis_options": {"include_financial_analysis": True},
            }

            response = client.post("/api/contracts/analyze", json=request_data)

            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["category"] == "contract_analysis"
            assert data["detail"]["error_code"] == "SYS_001"
        finally:
            # Clean up - this will be overridden again by the client fixture anyway
            fastapi_app.dependency_overrides.pop(get_user_document_service, None)

    def test_start_contract_analysis_document_not_found(
        self, client: TestClient, mock_db_client
    ):
        """Test contract analysis with nonexistent document"""
        from app.router.contracts import get_user_document_service
        from app.main import app as fastapi_app

        # Create mock document service
        mock_document_service = AsyncMock()
        mock_document_service.get_user_client.return_value = mock_db_client

        # Mock the document service dependency
        async def mock_get_user_document_service():
            return mock_document_service

        fastapi_app.dependency_overrides[get_user_document_service] = (
            mock_get_user_document_service
        )

        try:
            # Use a valid UUID, but patch repository to return None
            valid_missing_id = "00000000-0000-0000-0000-000000000099"
            with patch(
                "app.router.contracts.DocumentsRepository.get_document",
                new_callable=AsyncMock,
            ) as mock_get_document:
                mock_get_document.return_value = None
                request_data = {"document_id": valid_missing_id, "analysis_options": {}}
                response = client.post("/api/contracts/analyze", json=request_data)

            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["category"] == "contract_analysis"
            assert data["detail"]["error_code"] == "SYS_001"
        finally:
            # Clean up dependency override
            fastapi_app.dependency_overrides.pop(get_user_document_service, None)

    def test_start_contract_analysis_minimal_options(
        self, client: TestClient, mock_db_client, sample_document_data
    ):
        """Test contract analysis with minimal options"""
        from app.router.contracts import get_user_document_service
        from app.main import app as fastapi_app

        # Create mock document service
        mock_document_service = AsyncMock()
        mock_document_service.get_user_client.return_value = mock_db_client

        # Mock the document service dependency
        async def mock_get_user_document_service():
            return mock_document_service

        fastapi_app.dependency_overrides[get_user_document_service] = (
            mock_get_user_document_service
        )

        try:
            # Create separate mock chains for each table
            mock_documents_table = MagicMock()
            mock_contracts_table = MagicMock()
            mock_analyses_table = MagicMock()

            # Set up the return values for each table
            def get_table(table_name):
                if table_name == "documents":
                    return mock_documents_table
                elif table_name == "contracts":
                    return mock_contracts_table
                elif table_name == "analyses":
                    return mock_analyses_table
                return MagicMock()

            mock_db_client.table.side_effect = get_table

            # Mock document fetch via repository path used by router
            valid_doc_id = "00000000-0000-0000-0000-000000000003"
            fake_doc = MagicMock()
            fake_doc.id = valid_doc_id
            fake_doc.user_id = "test-user-id"
            fake_doc.original_filename = sample_document_data.get(
                "filename", "test.pdf"
            )
            fake_doc.storage_path = sample_document_data.get(
                "storage_path", "documents/path.pdf"
            )
            fake_doc.file_type = sample_document_data.get("file_type", "pdf")
            fake_doc.file_size = sample_document_data.get("file_size", 1024)
            fake_doc.content_hash = "abc123"
            fake_doc.processing_status = "uploaded"

            # Mock contract creation
            mock_contracts_table.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": "test-contract-id"}]
            )

            # Mock analysis creation
            mock_analyses_table.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": "test-analysis-id"}]
            )

            request_data = {
                "document_id": valid_doc_id
                # No analysis_options provided - should use defaults
            }

            # Mock repo get_document and background task to prevent actual execution
            with (
                patch(
                    "app.router.contracts.DocumentsRepository.get_document",
                    new_callable=AsyncMock,
                ) as mock_get_document,
                patch(
                    "app.tasks.background_tasks.comprehensive_document_analysis",
                    new_callable=AsyncMock,
                ) as mock_bg_task,
                patch(
                    "app.router.contracts.ContractsRepository.upsert_contract_by_content_hash",
                    new_callable=AsyncMock,
                ) as mock_upsert_contract,
                patch(
                    "app.router.contracts.AnalysesRepository.upsert_analysis",
                    new_callable=AsyncMock,
                ) as mock_upsert_analysis,
                patch(
                    "app.services.cache.cache_service.CacheService.check_contract_cache",
                    new_callable=AsyncMock,
                ) as mock_cache_lookup,
                patch(
                    "app.core.task_context.task_manager.initialize",
                    new_callable=AsyncMock,
                ) as mock_tm_init,
                patch(
                    "app.core.task_context.task_manager.launch_user_task",
                    new_callable=AsyncMock,
                ) as mock_launch,
                patch(
                    "app.router.contracts.notification_system.send_notification",
                    new_callable=AsyncMock,
                ) as mock_notify,
            ):
                mock_get_document.return_value = fake_doc
                mock_upsert_contract.return_value = MagicMock(id="test-contract-id")
                mock_upsert_analysis.return_value = MagicMock(id="test-analysis-id")
                mock_cache_lookup.return_value = None  # force cache MISS
                mock_tm_init.return_value = None
                mock_launch.return_value = MagicMock(id="task-123")
                mock_notify.return_value = None
                response = client.post("/api/contracts/analyze", json=request_data)

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "queued"
                assert data["estimated_completion_minutes"] == 3
        finally:
            # Clean up dependency override
            fastapi_app.dependency_overrides.pop(get_user_document_service, None)


@pytest.mark.api
class TestGetContractAnalysis:
    """Test get contract analysis functionality"""

    def test_get_contract_analysis_success(
        self,
        client: TestClient,
        mock_db_client,
        sample_analysis_data,
        sample_contract_data,
        sample_document_data,
    ):
        """Test successful contract analysis retrieval"""
        # Use a valid UUID for contract id to satisfy UUID parsing in router
        valid_contract_id = "00000000-0000-0000-0000-000000000111"
        sample_contract_data["id"] = valid_contract_id
        sample_analysis_data["contract_id"] = valid_contract_id

        # Also ensure a valid UUID for document_id referenced by contract
        valid_doc_id = "00000000-0000-0000-0000-000000000222"
        sample_contract_data["document_id"] = valid_doc_id
        sample_document_data["id"] = valid_doc_id

        # Override current user to have a valid UUID string (router may cast to UUID)
        from app.core.auth import get_current_user, User
        from app.main import app as fastapi_app

        def uuid_user():
            return User(
                id="00000000-0000-0000-0000-000000000333",
                email="test@real2ai.com",
                australian_state="NSW",
                user_type="lawyer",
                subscription_status="free",
                credits_remaining=5,
                preferences={},
            )

        fastapi_app.dependency_overrides[get_current_user] = uuid_user

        try:
            # Create separate mock chains for each table query
            mock_analyses_table = MagicMock()
            mock_contracts_table = MagicMock()
            mock_documents_table = MagicMock()

            # Set up the return values for each table
            def get_table(table_name):
                if table_name == "analyses":
                    return mock_analyses_table
                elif table_name == "contracts":
                    return mock_contracts_table
                elif table_name == "documents":
                    return mock_documents_table
                return MagicMock()

            mock_db_client.table.side_effect = get_table

            # Mock analysis fetch
            mock_analyses_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[sample_analysis_data]
            )

            # Mock contract fetch
            mock_contracts_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[sample_contract_data]
            )

            # Mock document fetch with user verification
            mock_documents_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[sample_document_data]
            )

            response = client.get(f"/api/contracts/{valid_contract_id}/analysis")

            assert response.status_code == 200
            data = response.json()
            assert data["contract_id"] == valid_contract_id
            assert data["analysis_status"] == "completed"
            assert "analysis_result" in data
            assert "processing_time" in data
            assert "created_at" in data
        finally:
            fastapi_app.dependency_overrides.pop(get_current_user, None)

    def test_get_contract_analysis_not_found(self, client: TestClient, mock_db_client):
        """Test get analysis when analysis doesn't exist"""
        mock_db_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        response = client.get("/api/contracts/nonexistent-contract-id/analysis")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Analysis not found"

    def test_get_contract_analysis_unauthorized(
        self,
        client: TestClient,
        mock_db_client,
        sample_analysis_data,
        sample_contract_data,
    ):
        """Test get analysis when user doesn't own contract"""
        # Mock the 3 database calls in order:
        # 1. Get analysis (succeeds)
        # 2. Get contract (succeeds)
        # 3. Get document with user filter (fails - no access)
        mock_analysis_response = MagicMock(data=[sample_analysis_data])
        mock_contract_response = MagicMock(data=[sample_contract_data])
        mock_document_response = MagicMock(data=[])  # No document found for this user

        mock_db_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            mock_analysis_response,
            mock_contract_response,
            mock_document_response,
        ]

        response = client.get("/api/contracts/test-contract-id/analysis")

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Access denied"


@pytest.mark.api
class TestAnalysisReports:
    """Test analysis report functionality"""

    @patch("app.router.contracts.get_contract_analysis")
    @patch("app.tasks.background_tasks.generate_pdf_report")
    def test_download_analysis_report_pdf(
        self,
        mock_generate_pdf,
        mock_get_analysis,
        client: TestClient,
        sample_analysis_data,
    ):
        """Test PDF report download"""
        # Mock get_contract_analysis
        mock_get_analysis.return_value = sample_analysis_data

        # Mock PDF generation
        mock_generate_pdf.return_value = b"PDF content"

        response = client.get("/api/contracts/test-contract-id/report?format=pdf")

        assert response.status_code == 200
        data = response.json()
        assert "download_url" in data
        assert "/report.pdf" in data["download_url"]

    @patch("app.router.contracts.get_contract_analysis")
    def test_download_analysis_report_json(
        self, mock_get_analysis, client: TestClient, sample_analysis_data
    ):
        """Test JSON report download"""
        mock_get_analysis.return_value = sample_analysis_data

        response = client.get("/api/contracts/test-contract-id/report?format=json")

        assert response.status_code == 200
        data = response.json()
        # Should return the analysis data directly
        assert data["id"] == "test-analysis-id"
        assert data["status"] == "completed"


@pytest.mark.unit
class TestAnalysisDataStructure:
    """Test analysis data structure validation"""

    def test_analysis_result_structure(self, sample_analysis_data):
        """Test analysis result has expected structure"""
        analysis_result = sample_analysis_data["analysis_result"]

        required_sections = [
            "contract_terms",
            "risk_assessment",
            "compliance_check",
            "recommendations",
        ]

        for section in required_sections:
            assert section in analysis_result

    def test_risk_assessment_structure(self, sample_analysis_data):
        """Test risk assessment has expected structure"""
        risk_assessment = sample_analysis_data["analysis_result"]["risk_assessment"]

        required_fields = ["overall_risk_score", "risk_factors"]

        for field in required_fields:
            assert field in risk_assessment

        # Validate risk score range
        assert 1 <= risk_assessment["overall_risk_score"] <= 10

        # Validate risk factors structure
        for risk_factor in risk_assessment["risk_factors"]:
            required_factor_fields = ["factor", "severity", "description"]
            for field in required_factor_fields:
                assert field in risk_factor

    def test_compliance_check_structure(self, sample_analysis_data):
        """Test compliance check has expected structure"""
        compliance_check = sample_analysis_data["analysis_result"]["compliance_check"]

        required_fields = [
            "state_compliance",
            "compliance_issues",
            "cooling_off_compliance",
        ]

        for field in required_fields:
            assert field in compliance_check

        # Validate boolean fields
        assert isinstance(compliance_check["state_compliance"], bool)
        assert isinstance(compliance_check["cooling_off_compliance"], bool)

        # Validate list fields
        assert isinstance(compliance_check["compliance_issues"], list)

    def test_recommendations_structure(self, sample_analysis_data):
        """Test recommendations have expected structure"""
        recommendations = sample_analysis_data["analysis_result"]["recommendations"]

        assert isinstance(recommendations, list)

        for recommendation in recommendations:
            required_fields = [
                "priority",
                "category",
                "recommendation",
                "action_required",
            ]
            for field in required_fields:
                assert field in recommendation

            # Validate data types
            assert isinstance(recommendation["action_required"], bool)
            assert recommendation["priority"] in ["low", "medium", "high"]
            assert recommendation["category"] in ["legal", "financial", "practical"]
