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
from dataclasses import dataclass
from datetime import datetime
import logging

from app.database.connection import get_service_role_connection, get_user_connection

logger = logging.getLogger(__name__)


@dataclass
class Contract:
    """Contract model"""

    id: UUID
    content_hash: str
    contract_type: str
    australian_state: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


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
        australian_state: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Contract:
        """
        Upsert contract by content hash.

        Args:
            content_hash: SHA-256 hash of contract content
            contract_type: Type of contract
            australian_state: Optional Australian state
            metadata: Optional additional metadata

        Returns:
            Contract: Existing or newly created contract
        """
        async with get_service_role_connection() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO contracts (
                    content_hash, contract_type, australian_state, metadata
                ) VALUES ($1, $2, $3, $4::jsonb)
                ON CONFLICT (content_hash) DO UPDATE SET
                    contract_type = COALESCE(contracts.contract_type, EXCLUDED.contract_type),
                    australian_state = COALESCE(contracts.australian_state, EXCLUDED.australian_state),
                    metadata = COALESCE(contracts.metadata, EXCLUDED.metadata),
                    updated_at = now()
                RETURNING id, content_hash, contract_type, australian_state, 
                         metadata, created_at, updated_at
                """,
                content_hash,
                contract_type,
                australian_state,
                json.dumps(metadata) if metadata is not None else None,
            )

            return Contract(
                id=row["id"],
                content_hash=row["content_hash"],
                contract_type=row["contract_type"],
                australian_state=row["australian_state"],
                metadata=row["metadata"],
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
                    SELECT id, content_hash, contract_type, australian_state, 
                           metadata, created_at, updated_at
                    FROM contracts
                    WHERE content_hash = $1
                    """,
                    content_hash,
                )
        else:
            async with get_service_role_connection() as conn:
                row = await conn.fetchrow(
                    """
                SELECT id, content_hash, contract_type, australian_state, 
                       metadata, created_at, updated_at
                FROM contracts
                WHERE content_hash = $1
                """,
                    content_hash,
                )

            if not row:
                return None

            return Contract(
                id=row["id"],
                content_hash=row["content_hash"],
                contract_type=row["contract_type"],
                australian_state=row["australian_state"],
                metadata=row["metadata"],
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
                SELECT id, content_hash, contract_type, australian_state, 
                       metadata, created_at, updated_at
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
                australian_state=row["australian_state"],
                metadata=row["metadata"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def update_contract_metadata(
        self, contract_id: UUID, metadata: Dict[str, Any]
    ) -> bool:
        """
        Update contract metadata.

        Args:
            contract_id: Contract ID
            metadata: New metadata

        Returns:
            True if update successful, False otherwise
        """
        async with get_service_role_connection() as conn:
            result = await conn.execute(
                """
                UPDATE contracts 
                SET metadata = $1::jsonb, updated_at = now()
                WHERE id = $2
                """,
                json.dumps(metadata) if metadata is not None else None,
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
                SELECT id, content_hash, contract_type, australian_state, 
                       metadata, created_at, updated_at
                FROM contracts
                WHERE contract_type = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                contract_type,
                limit,
                offset,
            )

            return [
                Contract(
                    id=row["id"],
                    content_hash=row["content_hash"],
                    contract_type=row["contract_type"],
                    australian_state=row["australian_state"],
                    metadata=row["metadata"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    async def list_contracts_by_state(
        self, australian_state: str, limit: int = 50, offset: int = 0
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
                SELECT id, content_hash, contract_type, australian_state, 
                       metadata, created_at, updated_at
                FROM contracts
                WHERE australian_state = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                australian_state,
                limit,
                offset,
            )

            return [
                Contract(
                    id=row["id"],
                    content_hash=row["content_hash"],
                    contract_type=row["contract_type"],
                    australian_state=row["australian_state"],
                    metadata=row["metadata"],
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

    async def get_contract_stats(self) -> Dict[str, Any]:
        """
        Get contract statistics.

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

            state_rows = await conn.fetch(
                """
                SELECT australian_state, COUNT(*) as count
                FROM contracts
                WHERE australian_state IS NOT NULL
                GROUP BY australian_state
                ORDER BY count DESC
                """
            )

            return {
                "total_contracts": total_row["total"],
                "by_type": {row["contract_type"]: row["count"] for row in type_rows},
                "by_state": {
                    row["australian_state"]: row["count"] for row in state_rows
                },
            }
