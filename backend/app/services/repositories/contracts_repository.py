"""
Contracts Repository - Service-role contract operations

This repository handles contract operations using the service-role context.
Prefer the Supabase service client (PostgREST) so RLS/grants are enforced
consistently by the Supabase stack, avoiding direct Postgres permission
discrepancies across environments.
"""

from typing import Dict, List, Optional, Any
import json
from uuid import UUID
from datetime import datetime
import logging

from app.database.connection import get_service_role_connection, get_user_connection
from app.models.supabase_models import Contract

logger = logging.getLogger(__name__)


class ContractsRepository:
    """Repository for contract operations.

    - Writes (upserts/updates/deletes) use service-role connection
    - Reads can be user-scoped (RLS) if a user_id is provided
    """

    def __init__(self, user_id: Optional[UUID] = None):
        self.user_id = user_id

    async def upsert_contract_by_content_hash(
        self,
        content_hash: str,
        contract_type: str,
        *,
        purchase_method: Optional[str] = None,
        use_category: Optional[str] = None,
        ocr_confidence: Optional[Dict[str, float]] = None,
        state: Optional[str] = None,
        contract_terms: Optional[Dict[str, Any]] = None,
        extracted_entity: Optional[Dict[str, Any]] = None,
        raw_text: Optional[str] = None,
        property_address: Optional[str] = None,
        updated_by: str,
    ) -> Contract:
        """
        Upsert contract by content hash.

        Args:
            content_hash: SHA-256 hash of contract content
            contract_type: Type of contract
            purchase_method: Optional OCR-inferred purchase method
            use_category: Optional OCR-inferred property use category
            ocr_confidence: Optional confidence scores for OCR-inferred fields
            australian_state: Optional Australian state
            contract_terms: Optional contract terms

        Returns:
            Contract: Existing or newly created contract
        """
        # Sanitize inputs to satisfy DB taxonomy constraints conservatively
        adjusted_contract_type = contract_type
        adjusted_purchase_method = purchase_method
        adjusted_use_category = use_category

        try:
            if contract_type == "lease_agreement" and purchase_method is not None:
                logger.warning(
                    "Dropping purchase_method for lease_agreement to satisfy constraints",
                    extra={"content_hash": content_hash},
                )
                adjusted_purchase_method = None
            elif contract_type == "option_to_purchase":
                if purchase_method is not None or use_category is not None:
                    logger.warning(
                        "Dropping purchase_method/use_category for option_to_purchase to satisfy constraints",
                        extra={"content_hash": content_hash},
                    )
                adjusted_purchase_method = None
                adjusted_use_category = None
        except Exception:
            # Defensive: never block upsert due to sanitization logging issues
            pass

        async with get_service_role_connection() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO contracts (
                    content_hash, contract_type, purchase_method, use_category,
                    ocr_confidence, state, contract_terms, extracted_entity,
                    raw_text, property_address, updated_by
                ) VALUES (
                    $1, $2, $3, $4,
                    COALESCE($5::jsonb, '{}'::jsonb),
                    $6,
                    COALESCE($7::jsonb, '{}'::jsonb),
                    COALESCE($8::jsonb, '{}'::jsonb),
                    $9,
                    $10,
                    $11
                )
                ON CONFLICT (content_hash) DO UPDATE SET
                    -- Prefer incoming non-null values while keeping existing when incoming is null
                    contract_type = COALESCE(EXCLUDED.contract_type, contracts.contract_type),
                    purchase_method = COALESCE(EXCLUDED.purchase_method, contracts.purchase_method),
                    use_category = COALESCE(EXCLUDED.use_category, contracts.use_category),
                    ocr_confidence = COALESCE(EXCLUDED.ocr_confidence, contracts.ocr_confidence),
                    state = COALESCE(EXCLUDED.state, contracts.state),
                    contract_terms = COALESCE(EXCLUDED.contract_terms, contracts.contract_terms),
                    extracted_entity = COALESCE(EXCLUDED.extracted_entity, contracts.extracted_entity),
                    raw_text = COALESCE(EXCLUDED.raw_text, contracts.raw_text),
                    property_address = COALESCE(EXCLUDED.property_address, contracts.property_address),
                    updated_by = COALESCE(EXCLUDED.updated_by, contracts.updated_by),
                    updated_at = now()
                RETURNING id, content_hash, contract_type, purchase_method, use_category,
                         COALESCE(ocr_confidence, '{}'::jsonb) as ocr_confidence,
                         state,
                         COALESCE(contract_terms, '{}'::jsonb) as contract_terms,
                         COALESCE(extracted_entity, '{}'::jsonb) as extracted_entity,
                         raw_text,
                         property_address,
                         updated_by,
                         created_at, updated_at
                """,
                content_hash,
                adjusted_contract_type,
                adjusted_purchase_method,
                adjusted_use_category,
                json.dumps(ocr_confidence) if ocr_confidence is not None else None,
                state,
                json.dumps(contract_terms) if contract_terms is not None else None,
                json.dumps(extracted_entity) if extracted_entity is not None else None,
                raw_text,
                property_address,
                updated_by,
            )

            # Normalize JSON fields in case the driver returns strings instead of dicts
            def _normalize_json(value: Optional[Any]) -> Dict[str, Any]:
                if value is None:
                    return {}
                if isinstance(value, dict):
                    return value
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        return parsed if isinstance(parsed, dict) else {}
                    except Exception:
                        return {}
                return {}

            return Contract(
                id=row["id"],
                content_hash=row["content_hash"],
                contract_type=row["contract_type"],
                purchase_method=row.get("purchase_method"),
                use_category=row.get("use_category"),
                ocr_confidence=_normalize_json(row.get("ocr_confidence")),
                state=row["state"],
                contract_terms=_normalize_json(row.get("contract_terms")),
                extracted_entity=_normalize_json(row.get("extracted_entity")),
                raw_text=row.get("raw_text"),
                property_address=row.get("property_address"),
                updated_by=row.get("updated_by"),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def get_contract_id_by_content_hash(
        self, content_hash: str
    ) -> Optional[UUID]:
        """
        Get contract ID by content hash.

        Args:
            content_hash: SHA-256 hash of contract content

        Returns:
            Contract ID or None if not found
        """
        # Prefer user-scoped read if user_id was provided (RLS enforced)
        if self.user_id is not None:
            async with get_user_connection(self.user_id) as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id FROM contracts WHERE content_hash = $1
                    """,
                    content_hash,
                )
        else:
            async with get_service_role_connection() as conn:
                row = await conn.fetchrow(
                    "SELECT id FROM contracts WHERE content_hash = $1", content_hash
                )
        return row["id"] if row else None

    async def get_contract_by_content_hash(
        self, content_hash: str
    ) -> Optional[Contract]:
        """
        Get contract by content hash.

        Args:
            content_hash: SHA-256 hash of contract content

        Returns:
            Contract or None if not found
        """
        if self.user_id is not None:
            async with get_user_connection(self.user_id) as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, content_hash, contract_type, purchase_method, use_category,
                           COALESCE(ocr_confidence, '{}'::jsonb) as ocr_confidence,
                           state,
                           COALESCE(contract_terms, '{}'::jsonb) as contract_terms,
                           COALESCE(extracted_entity, '{}'::jsonb) as extracted_entity,
                           raw_text, 
                           property_address, updated_by, created_at, updated_at
                    FROM contracts
                    WHERE content_hash = $1
                    """,
                    content_hash,
                )
        else:
            async with get_service_role_connection() as conn:
                row = await conn.fetchrow(
                    """
                SELECT id, content_hash, contract_type, purchase_method, use_category,
                       COALESCE(ocr_confidence, '{}'::jsonb) as ocr_confidence,
                       state,
                       COALESCE(contract_terms, '{}'::jsonb) as contract_terms,
                       COALESCE(extracted_entity, '{}'::jsonb) as extracted_entity,
                       raw_text, 
                       property_address, updated_by, created_at, updated_at
                FROM contracts
                WHERE content_hash = $1
                """,
                    content_hash,
                )

            if not row:
                return None

            def _normalize_json(value: Optional[Any]) -> Dict[str, Any]:
                if value is None:
                    return {}
                if isinstance(value, dict):
                    return value
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        return parsed if isinstance(parsed, dict) else {}
                    except Exception:
                        return {}
                return {}

            return Contract(
                id=row["id"],
                content_hash=row["content_hash"],
                contract_type=row["contract_type"],
                purchase_method=row.get("purchase_method"),
                use_category=row.get("use_category"),
                ocr_confidence=_normalize_json(row.get("ocr_confidence")),
                state=row["state"],
                contract_terms=_normalize_json(row.get("contract_terms")),
                extracted_entity=_normalize_json(row.get("extracted_entity")),
                raw_text=row.get("raw_text"),
                property_address=row.get("property_address"),
                updated_by=row.get("updated_by"),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def get_contracts_by_content_hash(
        self, content_hash: str, limit: int = 1
    ) -> List[Contract]:
        """
        Backwards-compatible wrapper that returns a list of contracts for a
        given content hash. The underlying schema enforces uniqueness on
        content_hash, so at most one item will be returned.

        Args:
            content_hash: SHA-256 hash of contract content
            limit: Maximum number of contracts to return (kept for API
                   compatibility; effectively 0 or 1 will be returned)

        Returns:
            List containing the matching Contract, or an empty list.
        """
        contract = await self.get_contract_by_content_hash(content_hash)
        return ([contract] if contract else [])[: max(0, limit)]

    async def get_contract_by_id(self, contract_id: UUID) -> Optional[Contract]:
        """
        Get contract by ID.

        Args:
            contract_id: Contract ID

        Returns:
            Contract or None if not found
        """
        async with get_service_role_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, content_hash, contract_type, purchase_method, use_category,
                       ocr_confidence, state, contract_terms, extracted_entity, raw_text,
                       property_address, updated_by, created_at, updated_at
                FROM contracts
                WHERE id = $1
                """,
                contract_id,
            )

            if not row:
                return None

            return Contract(
                id=row["id"],
                content_hash=row["content_hash"],
                contract_type=row["contract_type"],
                purchase_method=row.get("purchase_method"),
                use_category=row.get("use_category"),
                ocr_confidence=row.get("ocr_confidence", {}),
                state=row["state"],
                contract_terms=row.get("contract_terms", {}),
                extracted_entity=row.get("extracted_entity", {}),
                raw_text=row.get("raw_text"),
                property_address=row.get("property_address"),
                updated_by=row.get("updated_by"),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def update_contract_terms(
        self, contract_id: UUID, contract_terms: Dict[str, Any]
    ) -> bool:
        """
        Update contract terms.

        Args:
            contract_id: Contract ID
            contract_terms: New contract terms

        Returns:
            True if update successful, False otherwise
        """
        async with get_service_role_connection() as conn:
            result = await conn.execute(
                """
                UPDATE contracts 
                SET contract_terms = $1::jsonb, updated_at = now()
                WHERE id = $2
                """,
                json.dumps(contract_terms) if contract_terms is not None else None,
                contract_id,
            )
            return result.split()[-1] == "1"

    async def list_contracts_by_type(
        self, contract_type: str, limit: int = 50, offset: int = 0
    ) -> List[Contract]:
        """
        List contracts by type.

        Args:
            contract_type: Contract type to filter by
            limit: Maximum number of contracts to return
            offset: Offset for pagination

        Returns:
            List of Contract objects
        """
        async with get_service_role_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content_hash, contract_type, purchase_method, use_category,
                       COALESCE(ocr_confidence, '{}'::jsonb) as ocr_confidence,
                       state, COALESCE(contract_terms, '{}'::jsonb) as contract_terms,
                       COALESCE(extracted_entity, '{}'::jsonb) as extracted_entity,
                       raw_text,
                       property_address, updated_by, created_at, updated_at
                FROM contracts
                WHERE contract_type = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                contract_type,
                limit,
                offset,
            )

            def _normalize_json(value: Optional[Any]) -> Dict[str, Any]:
                if value is None:
                    return {}
                if isinstance(value, dict):
                    return value
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        return parsed if isinstance(parsed, dict) else {}
                    except Exception:
                        return {}
                return {}

            return [
                Contract(
                    id=row["id"],
                    content_hash=row["content_hash"],
                    contract_type=row["contract_type"],
                    purchase_method=row.get("purchase_method"),
                    use_category=row.get("use_category"),
                    ocr_confidence=_normalize_json(row.get("ocr_confidence")),
                    state=row["state"],
                    contract_terms=_normalize_json(row.get("contract_terms")),
                    extracted_entity=_normalize_json(row.get("extracted_entity")),
                    raw_text=row.get("raw_text"),
                    property_address=row.get("property_address"),
                    updated_by=row.get("updated_by"),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    async def list_contracts_by_state(
        self, state: str, limit: int = 50, offset: int = 0
    ) -> List[Contract]:
        """
        List contracts by Australian state.

        Args:
            australian_state: Australian state to filter by
            limit: Maximum number of contracts to return
            offset: Offset for pagination

        Returns:
            List of Contract objects
        """
        async with get_service_role_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content_hash, contract_type, purchase_method, use_category,
                       COALESCE(ocr_confidence, '{}'::jsonb) as ocr_confidence,
                       state, COALESCE(contract_terms, '{}'::jsonb) as contract_terms,
                       COALESCE(extracted_entity, '{}'::jsonb) as extracted_entity,
                       raw_text,
                       property_address, updated_by, created_at, updated_at
                FROM contracts
                WHERE state = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                state,
                limit,
                offset,
            )

            def _normalize_json(value: Optional[Any]) -> Dict[str, Any]:
                if value is None:
                    return {}
                if isinstance(value, dict):
                    return value
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        return parsed if isinstance(parsed, dict) else {}
                    except Exception:
                        return {}
                return {}

            return [
                Contract(
                    id=row["id"],
                    content_hash=row["content_hash"],
                    contract_type=row["contract_type"],
                    purchase_method=row.get("purchase_method"),
                    use_category=row.get("use_category"),
                    ocr_confidence=_normalize_json(row.get("ocr_confidence")),
                    state=row["state"],
                    contract_terms=_normalize_json(row.get("contract_terms")),
                    extracted_entity=_normalize_json(row.get("extracted_entity")),
                    raw_text=row.get("raw_text"),
                    property_address=row.get("property_address"),
                    updated_by=row.get("updated_by"),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    async def delete_contract(self, contract_id: UUID) -> bool:
        """
        Delete a contract.

        Args:
            contract_id: Contract ID

        Returns:
            True if deletion successful, False otherwise
        """
        async with get_service_role_connection() as conn:
            result = await conn.execute(
                "DELETE FROM contracts WHERE id = $1", contract_id
            )
            return result.split()[-1] == "1"

    async def list_contracts_by_taxonomy(
        self,
        contract_type: Optional[str] = None,
        purchase_method: Optional[str] = None,
        use_category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Contract]:
        """
        List contracts by taxonomy fields.

        Args:
            contract_type: Optional contract type filter
            purchase_method: Optional purchase method filter
            use_category: Optional lease category filter
            limit: Maximum number of contracts to return
            offset: Offset for pagination

        Returns:
            List of Contract objects
        """
        conditions = []
        params = []
        param_count = 0

        if contract_type:
            param_count += 1
            conditions.append(f"contract_type = ${param_count}")
            params.append(contract_type)

        if purchase_method:
            param_count += 1
            conditions.append(f"purchase_method = ${param_count}")
            params.append(purchase_method)

        if use_category:
            param_count += 1
            conditions.append(f"use_category = ${param_count}")
            params.append(use_category)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        param_count += 1
        limit_param = f"${param_count}"
        params.append(limit)

        param_count += 1
        offset_param = f"${param_count}"
        params.append(offset)

        query = f"""
            SELECT id, content_hash, contract_type, purchase_method, use_category,
                   ocr_confidence, state, contract_terms, extracted_entity, raw_text,
                   property_address, updated_by, created_at, updated_at
            FROM contracts
            {where_clause}
            ORDER BY created_at DESC
            LIMIT {limit_param} OFFSET {offset_param}
        """

        async with get_service_role_connection() as conn:
            rows = await conn.fetch(query, *params)

            return [
                Contract(
                    id=row["id"],
                    content_hash=row["content_hash"],
                    contract_type=row["contract_type"],
                    purchase_method=row.get("purchase_method"),
                    use_category=row.get("use_category"),
                    ocr_confidence=row.get("ocr_confidence", {}),
                    state=row["state"],
                    contract_terms=row.get("contract_terms", {}),
                    extracted_entity=row.get("extracted_entity", {}),
                    raw_text=row.get("raw_text"),
                    property_address=row.get("property_address"),
                    updated_by=row.get("updated_by"),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    async def get_contract_stats(self) -> Dict[str, Any]:
        """
        Get contract statistics including new taxonomy fields.

        Returns:
            Dictionary with contract statistics
        """
        async with get_service_role_connection() as conn:
            # Get total count and count by type
            total_row = await conn.fetchrow("SELECT COUNT(*) as total FROM contracts")

            type_rows = await conn.fetch(
                """
                SELECT contract_type, COUNT(*) as count
                FROM contracts
                GROUP BY contract_type
                ORDER BY count DESC
                """
            )

            purchase_method_rows = await conn.fetch(
                """
                SELECT purchase_method, COUNT(*) as count
                FROM contracts
                WHERE purchase_method IS NOT NULL
                GROUP BY purchase_method
                ORDER BY count DESC
                """
            )

            use_category_rows = await conn.fetch(
                """
                SELECT use_category, COUNT(*) as count
                FROM contracts
                WHERE use_category IS NOT NULL
                GROUP BY use_category
                ORDER BY count DESC
                """
            )

            state_rows = await conn.fetch(
                """
                SELECT state, COUNT(*) as count
                FROM contracts
                WHERE state IS NOT NULL
                GROUP BY state
                ORDER BY count DESC
                """
            )

            return {
                "total_contracts": total_row["total"],
                "by_type": {row["contract_type"]: row["count"] for row in type_rows},
                "by_purchase_method": {
                    row["purchase_method"]: row["count"] for row in purchase_method_rows
                },
                "by_use_category": {
                    row["use_category"]: row["count"] for row in use_category_rows
                },
                "by_state": {row["state"]: row["count"] for row in state_rows},
            }
