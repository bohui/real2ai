"""
Integration tests for contract taxonomy database migration.

Tests the database schema changes and constraints for the contract type taxonomy:
- Database enum types and constraints
- Cross-field validation constraints
- Taxonomy validation function
"""

import pytest
import asyncpg
from typing import Dict, Any
from unittest.mock import patch

from app.database.connection import get_service_role_connection


@pytest.mark.integration
class TestContractTaxonomyMigration:
    """Test database migration for contract taxonomy"""

    @pytest.mark.asyncio
    async def test_contract_type_enum_values(self):
        """Test that new contract type enum values are available"""
        async with get_service_role_connection() as conn:
            # Test enum values
            result = await conn.fetch("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = 'contract_type'::regtype 
                ORDER BY enumlabel
            """)
            
            enum_values = [row['enumlabel'] for row in result]
            expected_values = ['lease_agreement', 'option_to_purchase', 'purchase_agreement', 'unknown']
            
            assert set(enum_values) == set(expected_values)

    @pytest.mark.asyncio
    async def test_purchase_method_enum_exists(self):
        """Test that purchase_method enum type exists"""
        async with get_service_role_connection() as conn:
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'purchase_method'
                )
            """)
            
            assert result is True
            
            # Test enum values
            enum_result = await conn.fetch("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = 'purchase_method'::regtype 
                ORDER BY enumlabel
            """)
            
            enum_values = [row['enumlabel'] for row in enum_result]
            expected_values = [
                'auction', 'expression_of_interest', 'off_plan', 
                'private_treaty', 'standard', 'tender'
            ]
            
            assert set(enum_values) == set(expected_values)

    @pytest.mark.asyncio
    async def test_use_category_enum_exists(self):
        """Test that use_category enum type exists"""
        async with get_service_role_connection() as conn:
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'use_category'
                )
            """)
            
            assert result is True
            
            # Test enum values
            enum_result = await conn.fetch("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = 'use_category'::regtype 
                ORDER BY enumlabel
            """)
            
            enum_values = [row['enumlabel'] for row in enum_result]
            expected_values = ['commercial', 'industrial', 'residential', 'retail']
            
            assert set(enum_values) == set(expected_values)

    @pytest.mark.asyncio
    async def test_contracts_table_new_columns(self):
        """Test that contracts table has new taxonomy columns"""
        async with get_service_role_connection() as conn:
            # Check column existence
            result = await conn.fetch("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'contracts' 
                AND column_name IN ('purchase_method', 'use_category', 'ocr_confidence')
                ORDER BY column_name
            """)
            
            columns = {row['column_name']: row for row in result}
            
            # purchase_method column
            assert 'purchase_method' in columns
            assert columns['purchase_method']['data_type'] == 'character varying'
            assert columns['purchase_method']['is_nullable'] == 'YES'
            
            # use_category column
            assert 'use_category' in columns
            assert columns['use_category']['data_type'] == 'character varying'
            assert columns['use_category']['is_nullable'] == 'YES'
            
            # ocr_confidence column
            assert 'ocr_confidence' in columns
            assert columns['ocr_confidence']['data_type'] == 'jsonb'
            assert columns['ocr_confidence']['is_nullable'] == 'YES'

    @pytest.mark.asyncio
    async def test_contract_constraints(self):
        """Test that contract validation constraints exist"""
        async with get_service_role_connection() as conn:
            # Check constraint existence
            result = await conn.fetch("""
                SELECT constraint_name, check_clause
                FROM information_schema.check_constraints 
                WHERE constraint_name LIKE '%contract%'
                ORDER BY constraint_name
            """)
            
            constraint_names = [row['constraint_name'] for row in result]
            
            expected_constraints = [
                'contracts_contract_type_check',
                'contracts_purchase_method_check',
                'contracts_use_category_check',
                'contracts_purchase_method_dependency_check',
                'contracts_use_category_dependency_check'
            ]
            
            for constraint in expected_constraints:
                assert constraint in constraint_names

    @pytest.mark.asyncio
    async def test_taxonomy_validation_function(self):
        """Test the validate_contract_taxonomy function"""
        async with get_service_role_connection() as conn:
            # Test valid purchase agreement
            result = await conn.fetchval("""
                SELECT validate_contract_taxonomy('purchase_agreement', 'auction', NULL)
            """)
            assert result is True
            
            # Test valid lease agreement
            result = await conn.fetchval("""
                SELECT validate_contract_taxonomy('lease_agreement', NULL, 'commercial')
            """)
            assert result is True
            
            # Test valid option to purchase
            result = await conn.fetchval("""
                SELECT validate_contract_taxonomy('option_to_purchase', NULL, NULL)
            """)
            assert result is True
            
            # Test invalid - purchase agreement without purchase_method
            result = await conn.fetchval("""
                SELECT validate_contract_taxonomy('purchase_agreement', NULL, NULL)
            """)
            assert result is False
            
            # Test invalid - lease agreement without use_category
            result = await conn.fetchval("""
                SELECT validate_contract_taxonomy('lease_agreement', NULL, NULL)
            """)
            assert result is False
            
            # Test invalid - cross-field contamination
            result = await conn.fetchval("""
                SELECT validate_contract_taxonomy('purchase_agreement', 'auction', 'commercial')
            """)
            assert result is False

    @pytest.mark.asyncio
    async def test_insert_valid_purchase_agreement(self):
        """Test inserting valid purchase agreement"""
        async with get_service_role_connection() as conn:
            # Insert valid purchase agreement
            result = await conn.fetchrow("""
                INSERT INTO contracts (
                    content_hash, contract_type, purchase_method, australian_state
                ) VALUES (
                    'test_hash_purchase', 'purchase_agreement', 'auction', 'NSW'
                ) RETURNING id, contract_type, purchase_method, use_category
            """)
            
            assert result['contract_type'] == 'purchase_agreement'
            assert result['purchase_method'] == 'auction'
            assert result['use_category'] is None
            
            # Cleanup
            await conn.execute("DELETE FROM contracts WHERE content_hash = 'test_hash_purchase'")

    @pytest.mark.asyncio
    async def test_insert_valid_lease_agreement(self):
        """Test inserting valid lease agreement"""
        async with get_service_role_connection() as conn:
            # Insert valid lease agreement
            result = await conn.fetchrow("""
                INSERT INTO contracts (
                    content_hash, contract_type, use_category, australian_state
                ) VALUES (
                    'test_hash_lease', 'lease_agreement', 'residential', 'VIC'
                ) RETURNING id, contract_type, purchase_method, use_category
            """)
            
            assert result['contract_type'] == 'lease_agreement'
            assert result['purchase_method'] is None
            assert result['use_category'] == 'residential'
            
            # Cleanup
            await conn.execute("DELETE FROM contracts WHERE content_hash = 'test_hash_lease'")

    @pytest.mark.asyncio
    async def test_insert_invalid_purchase_agreement(self):
        """Test that invalid purchase agreements are rejected"""
        async with get_service_role_connection() as conn:
            # Try to insert purchase agreement without purchase_method
            with pytest.raises(asyncpg.CheckViolationError):
                await conn.execute("""
                    INSERT INTO contracts (
                        content_hash, contract_type, australian_state
                    ) VALUES (
                        'test_hash_invalid_purchase', 'purchase_agreement', 'NSW'
                    )
                """)

    @pytest.mark.asyncio
    async def test_insert_invalid_lease_agreement(self):
        """Test that invalid lease agreements are rejected"""
        async with get_service_role_connection() as conn:
            # Try to insert lease agreement without use_category
            with pytest.raises(asyncpg.CheckViolationError):
                await conn.execute("""
                    INSERT INTO contracts (
                        content_hash, contract_type, australian_state
                    ) VALUES (
                        'test_hash_invalid_lease', 'lease_agreement', 'NSW'
                    )
                """)

    @pytest.mark.asyncio
    async def test_insert_cross_field_contamination(self):
        """Test that cross-field contamination is rejected"""
        async with get_service_role_connection() as conn:
            # Try to insert purchase agreement with use_category
            with pytest.raises(asyncpg.CheckViolationError):
                await conn.execute("""
                    INSERT INTO contracts (
                        content_hash, contract_type, purchase_method, use_category, australian_state
                    ) VALUES (
                        'test_hash_contamination', 'purchase_agreement', 'auction', 'commercial', 'NSW'
                    )
                """)

    @pytest.mark.asyncio
    async def test_ocr_confidence_jsonb_storage(self):
        """Test that OCR confidence is stored as JSONB"""
        async with get_service_role_connection() as conn:
            # Insert contract with OCR confidence
            confidence_data = {
                "purchase_method": 0.92,
                "purchase_method_evidence": ["auction", "highest bidder"],
                "extraction_timestamp": "2024-01-20T10:30:00Z"
            }
            
            result = await conn.fetchrow("""
                INSERT INTO contracts (
                    content_hash, contract_type, purchase_method, 
                    ocr_confidence, australian_state
                ) VALUES (
                    'test_hash_confidence', 'purchase_agreement', 'auction',
                    $1::jsonb, 'NSW'
                ) RETURNING ocr_confidence
            """, confidence_data)
            
            assert result['ocr_confidence'] == confidence_data
            assert result['ocr_confidence']['purchase_method'] == 0.92
            
            # Test JSONB querying
            confidence_value = await conn.fetchval("""
                SELECT ocr_confidence->>'purchase_method' 
                FROM contracts 
                WHERE content_hash = 'test_hash_confidence'
            """)
            
            assert float(confidence_value) == 0.92
            
            # Cleanup
            await conn.execute("DELETE FROM contracts WHERE content_hash = 'test_hash_confidence'")

    @pytest.mark.asyncio
    async def test_contract_indexes(self):
        """Test that proper indexes exist for taxonomy fields"""
        async with get_service_role_connection() as conn:
            # Check for taxonomy indexes
            result = await conn.fetch("""
                SELECT indexname, indexdef
                FROM pg_indexes 
                WHERE tablename = 'contracts' 
                AND (indexname LIKE '%taxonomy%' OR 
                     indexname LIKE '%purchase_method%' OR 
                     indexname LIKE '%use_category%')
                ORDER BY indexname
            """)
            
            index_names = [row['indexname'] for row in result]
            
            expected_indexes = [
                'idx_contracts_purchase_method',
                'idx_contracts_use_category', 
                'idx_contracts_taxonomy'
            ]
            
            for index in expected_indexes:
                assert index in index_names

    @pytest.mark.asyncio
    async def test_unknown_contract_type_flexibility(self):
        """Test that unknown contract type allows any field combination"""
        async with get_service_role_connection() as conn:
            # Test unknown with no additional fields
            result1 = await conn.fetchrow("""
                INSERT INTO contracts (
                    content_hash, contract_type, australian_state
                ) VALUES (
                    'test_hash_unknown1', 'unknown', 'NSW'
                ) RETURNING contract_type, purchase_method, use_category
            """)
            
            assert result1['contract_type'] == 'unknown'
            assert result1['purchase_method'] is None
            assert result1['use_category'] is None
            
            # Test unknown with purchase_method
            result2 = await conn.fetchrow("""
                INSERT INTO contracts (
                    content_hash, contract_type, purchase_method, australian_state
                ) VALUES (
                    'test_hash_unknown2', 'unknown', 'auction', 'NSW'
                ) RETURNING contract_type, purchase_method, use_category
            """)
            
            assert result2['contract_type'] == 'unknown'
            assert result2['purchase_method'] == 'auction'
            assert result2['use_category'] is None
            
            # Test unknown with use_category
            result3 = await conn.fetchrow("""
                INSERT INTO contracts (
                    content_hash, contract_type, use_category, australian_state
                ) VALUES (
                    'test_hash_unknown3', 'unknown', 'commercial', 'NSW'
                ) RETURNING contract_type, purchase_method, use_category
            """)
            
            assert result3['contract_type'] == 'unknown'
            assert result3['purchase_method'] is None
            assert result3['use_category'] == 'commercial'
            
            # Cleanup
            await conn.execute("DELETE FROM contracts WHERE content_hash LIKE 'test_hash_unknown%'")