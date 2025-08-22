"""
Tests for contracts repository with new taxonomy fields.

Tests the database operations for the contract type taxonomy system:
- Contract creation and updates with taxonomy fields
- Validation of cross-field dependencies
- Querying by taxonomy fields
- Statistics and analytics
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from app.services.repositories.contracts_repository import ContractsRepository
from app.models.supabase_models import Contract
from app.schema.enums import ContractType, PurchaseMethod, UseCategory, AustralianState


@pytest.fixture
def mock_connection():
    """Mock database connection"""
    mock_conn = AsyncMock()
    return mock_conn


@pytest.fixture
def contracts_repo():
    """Contracts repository instance"""
    user_id = uuid4()
    return ContractsRepository(user_id=user_id)


class TestContractTaxonomyRepository:
    """Test contract repository operations with taxonomy fields"""

    @pytest.mark.asyncio
    async def test_upsert_contract_with_purchase_method(
        self, contracts_repo, mock_connection
    ):
        """Test upserting contract with purchase method"""
        content_hash = "test_hash_123"
        contract_id = uuid4()

        # Mock database response
        mock_row = {
            "id": contract_id,
            "content_hash": content_hash,
            "contract_type": "purchase_agreement",
            "purchase_method": "auction",
            "use_category": None,
            "ocr_confidence": {"purchase_method": 0.92},
            "australian_state": "NSW",
            "contract_terms": {},
            "raw_text": None,
            "property_address": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        mock_connection.fetchrow.return_value = mock_row

        # Writes use service-role connection
        with patch(
            "app.services.repositories.contracts_repository.get_user_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await contracts_repo.upsert_contract_by_content_hash(
                content_hash=content_hash,
                contract_type="purchase_agreement",
                purchase_method="auction",
                ocr_confidence={"purchase_method": 0.92},
                state="NSW",
                updated_by="unit_test",
            )

            # Verify the query was called with correct parameters
            mock_connection.fetchrow.assert_called_once()
            call_args = mock_connection.fetchrow.call_args
            query = call_args[0][0]
            params = call_args[0][1:]

            assert "purchase_method" in query
            assert "use_category" in query
            assert "ocr_confidence" in query
            assert params[0] == content_hash
            assert params[1] == "purchase_agreement"
            assert params[2] == "auction"
            assert params[3] is None  # use_category

            # Verify the returned contract
            assert isinstance(result, Contract)
            assert result.id == contract_id
            assert result.contract_type == "purchase_agreement"
            assert result.purchase_method == "auction"
            assert result.use_category is None
            assert result.ocr_confidence == {"purchase_method": 0.92}

    @pytest.mark.asyncio
    async def test_upsert_contract_null_json_defaults_to_empty(
        self, contracts_repo, mock_connection
    ):
        """Ensure NULL jsonb from DB maps to empty dicts in model."""
        content_hash = "test_hash_null_json"
        contract_id = uuid4()

        mock_row = {
            "id": contract_id,
            "content_hash": content_hash,
            "contract_type": "unknown",
            "purchase_method": None,
            "use_category": None,
            "ocr_confidence": None,
            "australian_state": "NSW",
            "contract_terms": None,
            "raw_text": None,
            "property_address": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        mock_connection.fetchrow.return_value = mock_row

        # Writes use service-role connection
        with patch(
            "app.services.repositories.contracts_repository.get_user_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await contracts_repo.upsert_contract_by_content_hash(
                content_hash=content_hash,
                contract_type="unknown",
                state="NSW",
                updated_by="unit_test",
            )

            assert isinstance(result, Contract)
            assert result.ocr_confidence == {}
            assert result.contract_terms == {}

    @pytest.mark.asyncio
    async def test_upsert_contract_string_json_defaults_to_parsed(
        self, contracts_repo, mock_connection
    ):
        """Ensure string JSON from DB is parsed into dicts in model."""
        content_hash = "test_hash_string_json"
        contract_id = uuid4()

        mock_row = {
            "id": contract_id,
            "content_hash": content_hash,
            "contract_type": "unknown",
            "purchase_method": None,
            "use_category": None,
            "ocr_confidence": '{"purchase_method": 0.5}',
            "australian_state": "NSW",
            "contract_terms": "{}",
            "raw_text": None,
            "property_address": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        mock_connection.fetchrow.return_value = mock_row

        with patch(
            "app.services.repositories.contracts_repository.get_service_role_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await contracts_repo.upsert_contract_by_content_hash(
                content_hash=content_hash,
                contract_type="unknown",
                state="NSW",
                updated_by="unit_test",
            )

            assert isinstance(result, Contract)
            assert result.ocr_confidence == {"purchase_method": 0.5}
            assert result.contract_terms == {}

    @pytest.mark.asyncio
    async def test_upsert_purchase_agreement_without_purchase_method_is_downgraded(
        self, contracts_repo, mock_connection
    ):
        """Ensure repository downgrades to 'unknown' when purchase_method is missing."""
        content_hash = "test_hash_downgrade"
        contract_id = uuid4()

        mock_row = {
            "id": contract_id,
            "content_hash": content_hash,
            "contract_type": "unknown",
            "purchase_method": None,
            "use_category": None,
            "ocr_confidence": {},
            "australian_state": "NSW",
            "contract_terms": {},
            "raw_text": None,
            "property_address": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        mock_connection.fetchrow.return_value = mock_row

        with patch(
            "app.services.repositories.contracts_repository.get_service_role_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await contracts_repo.upsert_contract_by_content_hash(
                content_hash=content_hash,
                contract_type="purchase_agreement",
                state="NSW",
                updated_by="unit_test",
            )

            # Verify SQL was called and contract_type param was downgraded to 'unknown'
            assert mock_connection.fetchrow.called
            _, *params = mock_connection.fetchrow.call_args[0]
            assert params[0] == content_hash
            assert params[1] == "unknown"
            assert result.contract_type == "unknown"

    @pytest.mark.asyncio
    async def test_upsert_contract_with_use_category(
        self, contracts_repo, mock_connection
    ):
        """Test upserting contract with lease category"""
        content_hash = "test_hash_456"
        contract_id = uuid4()

        # Mock database response
        mock_row = {
            "id": contract_id,
            "content_hash": content_hash,
            "contract_type": "lease_agreement",
            "purchase_method": None,
            "use_category": "commercial",
            "ocr_confidence": {"use_category": 0.85},
            "australian_state": "VIC",
            "contract_terms": {},
            "raw_text": None,
            "property_address": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        mock_connection.fetchrow.return_value = mock_row

        with patch(
            "app.services.repositories.contracts_repository.get_service_role_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await contracts_repo.upsert_contract_by_content_hash(
                content_hash=content_hash,
                contract_type="lease_agreement",
                use_category="commercial",
                ocr_confidence={"use_category": 0.85},
                state="VIC",
                updated_by="unit_test",
            )

            # Verify the returned contract
            assert result.contract_type == "lease_agreement"
            assert result.purchase_method is None
            assert result.use_category == "commercial"
            assert result.ocr_confidence == {"use_category": 0.85}

    @pytest.mark.asyncio
    async def test_list_contracts_by_taxonomy(self, contracts_repo, mock_connection):
        """Test querying contracts by taxonomy fields"""
        contract_id1 = uuid4()
        contract_id2 = uuid4()

        # Mock database response
        mock_rows = [
            {
                "id": contract_id1,
                "content_hash": "hash1",
                "contract_type": "purchase_agreement",
                "purchase_method": "auction",
                "use_category": None,
                "ocr_confidence": {"purchase_method": 0.92},
                "australian_state": "NSW",
                "contract_terms": {},
                "raw_text": None,
                "property_address": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
            {
                "id": contract_id2,
                "content_hash": "hash2",
                "contract_type": "purchase_agreement",
                "purchase_method": "auction",
                "use_category": None,
                "ocr_confidence": {"purchase_method": 0.88},
                "australian_state": "NSW",
                "contract_terms": {},
                "raw_text": None,
                "property_address": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        ]

        mock_connection.fetch.return_value = mock_rows

        with patch(
            "app.services.repositories.contracts_repository.get_service_role_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            results = await contracts_repo.list_contracts_by_taxonomy(
                contract_type="purchase_agreement", purchase_method="auction", limit=10
            )

            # Verify the query was built correctly
            mock_connection.fetch.assert_called_once()
            call_args = mock_connection.fetch.call_args
            query = call_args[0][0]
            params = call_args[0][1:]

            assert "contract_type = $1" in query
            assert "purchase_method = $2" in query
            assert params[0] == "purchase_agreement"
            assert params[1] == "auction"
            assert params[2] == 10  # limit
            assert params[3] == 0  # offset

            # Verify the results
            assert len(results) == 2
            assert all(
                contract.contract_type == "purchase_agreement" for contract in results
            )
            assert all(contract.purchase_method == "auction" for contract in results)

    @pytest.mark.asyncio
    async def test_get_contract_stats_with_taxonomy(
        self, contracts_repo, mock_connection
    ):
        """Test contract statistics including taxonomy fields"""
        # Mock database responses
        mock_connection.fetchrow.return_value = {"total": 150}

        mock_connection.fetch.side_effect = [
            # by_type
            [
                {"contract_type": "purchase_agreement", "count": 80},
                {"contract_type": "lease_agreement", "count": 50},
                {"contract_type": "option_to_purchase", "count": 15},
                {"contract_type": "unknown", "count": 5},
            ],
            # by_purchase_method
            [
                {"purchase_method": "auction", "count": 30},
                {"purchase_method": "private_treaty", "count": 25},
                {"purchase_method": "off_plan", "count": 15},
                {"purchase_method": "standard", "count": 10},
            ],
            # by_use_category
            [
                {"use_category": "residential", "count": 30},
                {"use_category": "commercial", "count": 15},
                {"use_category": "retail", "count": 5},
            ],
            # by_state
            [
                {"australian_state": "NSW", "count": 60},
                {"australian_state": "VIC", "count": 40},
                {"australian_state": "QLD", "count": 30},
                {"australian_state": "WA", "count": 20},
            ],
        ]

        with patch(
            "app.services.repositories.contracts_repository.get_service_role_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            stats = await contracts_repo.get_contract_stats()

            # Verify stats structure
            assert stats["total_contracts"] == 150
            assert stats["by_type"]["purchase_agreement"] == 80
            assert stats["by_type"]["lease_agreement"] == 50
            assert stats["by_purchase_method"]["auction"] == 30
            assert stats["by_purchase_method"]["private_treaty"] == 25
            assert stats["by_use_category"]["residential"] == 30
            assert stats["by_use_category"]["commercial"] == 15
            assert stats["by_state"]["NSW"] == 60

    @pytest.mark.asyncio
    async def test_get_contract_with_taxonomy_fields(
        self, contracts_repo, mock_connection
    ):
        """Test retrieving contract with taxonomy fields"""
        contract_id = uuid4()
        content_hash = "test_hash_789"

        # Mock database response
        mock_row = {
            "id": contract_id,
            "content_hash": content_hash,
            "contract_type": "purchase_agreement",
            "purchase_method": "off_plan",
            "use_category": None,
            "ocr_confidence": {
                "purchase_method": 0.89,
                "purchase_method_evidence": ["off-the-plan", "completion certificate"],
            },
            "australian_state": "NSW",
            "contract_terms": {"purchase_price": 750000},
            "raw_text": "Sample contract text...",
            "property_address": "123 Test Street, Sydney NSW",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        mock_connection.fetchrow.return_value = mock_row

        with patch(
            "app.services.repositories.contracts_repository.get_service_role_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await contracts_repo.get_contract_by_content_hash(content_hash)

            # Verify the query includes taxonomy fields
            mock_connection.fetchrow.assert_called_once()
            call_args = mock_connection.fetchrow.call_args
            query = call_args[0][0]

            assert "purchase_method" in query
            assert "use_category" in query
            assert "ocr_confidence" in query

            # Verify the returned contract
            assert result is not None
            assert result.contract_type == "purchase_agreement"
            assert result.purchase_method == "off_plan"
            assert result.use_category is None
            assert result.ocr_confidence["purchase_method"] == 0.89
            assert "purchase_method_evidence" in result.ocr_confidence

    @pytest.mark.asyncio
    async def test_contract_not_found(self, contracts_repo, mock_connection):
        """Test handling when contract is not found"""
        content_hash = "nonexistent_hash"

        mock_connection.fetchrow.return_value = None

        with patch(
            "app.services.repositories.contracts_repository.get_service_role_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await contracts_repo.get_contract_by_content_hash(content_hash)

            assert result is None

    @pytest.mark.asyncio
    async def test_list_contracts_by_taxonomy_no_filters(
        self, contracts_repo, mock_connection
    ):
        """Test listing contracts without taxonomy filters"""
        mock_connection.fetch.return_value = []

        with patch(
            "app.services.repositories.contracts_repository.get_service_role_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            results = await contracts_repo.list_contracts_by_taxonomy()

            # Verify query without WHERE clause
            call_args = mock_connection.fetch.call_args
            query = call_args[0][0]
            params = call_args[0][1:]

            assert "WHERE" not in query
            assert len(params) == 2  # just limit and offset
            assert params[0] == 50  # default limit
            assert params[1] == 0  # default offset

    @pytest.mark.asyncio
    async def test_list_contracts_mixed_taxonomy_filters(
        self, contracts_repo, mock_connection
    ):
        """Test listing contracts with mixed taxonomy filters"""
        mock_connection.fetch.return_value = []

        with patch(
            "app.services.repositories.contracts_repository.get_service_role_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            results = await contracts_repo.list_contracts_by_taxonomy(
                contract_type="lease_agreement",
                use_category="commercial",
                limit=20,
                offset=10,
            )

            # Verify query construction
            call_args = mock_connection.fetch.call_args
            query = call_args[0][0]
            params = call_args[0][1:]

            assert "contract_type = $1" in query
            assert "use_category = $2" in query
            # Ensure purchase_method is not part of WHERE clause
            where_segment = query.split("WHERE", 1)[1]
            assert "purchase_method =" not in where_segment
            assert params[0] == "lease_agreement"
            assert params[1] == "commercial"
            assert params[2] == 20  # limit
            assert params[3] == 10  # offset


class TestContractModelTaxonomy:
    """Test Contract model with taxonomy fields"""

    def test_contract_model_with_purchase_method(self):
        """Test Contract model with purchase method"""
        contract_data = {
            "id": uuid4(),
            "content_hash": "test_hash",
            "contract_type": ContractType.PURCHASE_AGREEMENT,
            "purchase_method": PurchaseMethod.AUCTION,
            "use_category": None,
            "ocr_confidence": {"purchase_method": 0.92},
            "australian_state": AustralianState.NSW,
            "contract_terms": {},
        }

        contract = Contract(**contract_data)

        assert contract.contract_type == ContractType.PURCHASE_AGREEMENT
        assert contract.purchase_method == PurchaseMethod.AUCTION
        assert contract.use_category is None
        assert contract.ocr_confidence == {"purchase_method": 0.92}

    def test_contract_model_with_use_category(self):
        """Test Contract model with lease category"""
        contract_data = {
            "id": uuid4(),
            "content_hash": "test_hash",
            "contract_type": ContractType.LEASE_AGREEMENT,
            "purchase_method": None,
            "use_category": UseCategory.RESIDENTIAL,
            "ocr_confidence": {"use_category": 0.85},
            "australian_state": AustralianState.VIC,
            "contract_terms": {},
        }

        contract = Contract(**contract_data)

        assert contract.contract_type == ContractType.LEASE_AGREEMENT
        assert contract.purchase_method is None
        assert contract.use_category == UseCategory.RESIDENTIAL
        assert contract.ocr_confidence == {"use_category": 0.85}

    def test_contract_model_defaults(self):
        """Test Contract model with default values"""
        contract_data = {
            "id": uuid4(),
            "content_hash": "test_hash",
        }

        contract = Contract(**contract_data)

        assert contract.contract_type == ContractType.UNKNOWN
        assert contract.purchase_method is None
        assert contract.use_category is None
        assert contract.ocr_confidence == {}
        assert contract.australian_state == AustralianState.NSW
