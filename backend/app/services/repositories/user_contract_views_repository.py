"""
User Contract Views Repository - User contract analysis history operations

This repository handles user contract view tracking with RLS enforcement
for privacy and access control.
"""

from typing import Dict, List, Optional, Any
from uuid import UUID
from dataclasses import dataclass
from datetime import datetime
import logging

from app.database.connection import get_user_connection

logger = logging.getLogger(__name__)


@dataclass
class UserContractView:
    """User Contract View model"""
    id: UUID
    user_id: UUID
    content_hash: str
    property_address: Optional[str] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserContractViewsRepository:
    """Repository for user contract view tracking operations"""

    def __init__(self, user_id: Optional[UUID] = None):
        """
        Initialize user contract views repository.
        
        Args:
            user_id: Optional user ID for user-scoped operations
        """
        self.user_id = user_id

    async def create_contract_view(
        self,
        user_id: str,
        content_hash: str,
        property_address: Optional[str] = None,
        source: str = "upload"
    ) -> bool:
        """
        Create a new contract view record.

        Args:
            user_id: User ID as string
            content_hash: Content hash identifier
            property_address: Optional property address
            source: View source (upload, analysis, search)

        Returns:
            True if created successfully, False otherwise
        """
        try:
            query = """
                INSERT INTO user_contract_views (
                    user_id, content_hash, property_address, source
                ) VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, content_hash) DO UPDATE SET
                    updated_at = now()
                RETURNING id
            """
            
            async with get_user_connection(UUID(user_id) if isinstance(user_id, str) else user_id) as conn:
                result = await conn.fetchrow(
                    query, 
                    UUID(user_id) if isinstance(user_id, str) else user_id,
                    content_hash,
                    property_address,
                    source
                )
                
                return result is not None
                
        except Exception as e:
            logger.error(f"Failed to create contract view: {e}")
            return False

    async def get_user_contract_views(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get user's contract view history.

        Args:
            user_id: User ID as string
            limit: Maximum number of views to return
            offset: Offset for pagination

        Returns:
            List of contract view records
        """
        query = """
            SELECT id, user_id, content_hash, property_address, source, 
                   created_at, updated_at
            FROM user_contract_views
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """
        
        async with get_user_connection(UUID(user_id) if isinstance(user_id, str) else user_id) as conn:
            rows = await conn.fetch(query, UUID(user_id) if isinstance(user_id, str) else user_id, limit, offset)

        return [
            {
                "id": str(row['id']),
                "user_id": str(row['user_id']),
                "content_hash": row['content_hash'],
                "property_address": row['property_address'],
                "source": row['source'],
                "created_at": row['created_at'],
                "updated_at": row['updated_at']
            }
            for row in rows
        ]

    async def get_contract_view_by_hash(
        self,
        user_id: str,
        content_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get specific contract view by content hash for user.

        Args:
            user_id: User ID as string
            content_hash: Content hash identifier

        Returns:
            Contract view record or None if not found
        """
        query = """
            SELECT id, user_id, content_hash, property_address, source, 
                   created_at, updated_at
            FROM user_contract_views
            WHERE user_id = $1 AND content_hash = $2
            LIMIT 1
        """
        
        async with get_user_connection(UUID(user_id) if isinstance(user_id, str) else user_id) as conn:
            row = await conn.fetchrow(
                query, 
                UUID(user_id) if isinstance(user_id, str) else user_id,
                content_hash
            )

        if not row:
            return None

        return {
            "id": str(row['id']),
            "user_id": str(row['user_id']),
            "content_hash": row['content_hash'],
            "property_address": row['property_address'],
            "source": row['source'],
            "created_at": row['created_at'],
            "updated_at": row['updated_at']
        }

    async def update_contract_view(
        self,
        user_id: str,
        content_hash: str,
        property_address: Optional[str] = None,
        source: Optional[str] = None
    ) -> bool:
        """
        Update an existing contract view record.

        Args:
            user_id: User ID as string
            content_hash: Content hash identifier
            property_address: Optional property address to update
            source: Optional source to update

        Returns:
            True if updated successfully, False otherwise
        """
        # Build dynamic update query
        set_clauses = ["updated_at = now()"]
        params = []
        param_count = 0

        if property_address is not None:
            param_count += 1
            set_clauses.append(f"property_address = ${param_count}")
            params.append(property_address)

        if source is not None:
            param_count += 1
            set_clauses.append(f"source = ${param_count}")
            params.append(source)

        # Add WHERE clause parameters
        param_count += 1
        params.append(UUID(user_id) if isinstance(user_id, str) else user_id)
        param_count += 1
        params.append(content_hash)

        query = f"""
            UPDATE user_contract_views 
            SET {', '.join(set_clauses)}
            WHERE user_id = ${param_count - 1} AND content_hash = ${param_count}
        """

        try:
            async with get_user_connection(UUID(user_id) if isinstance(user_id, str) else user_id) as conn:
                result = await conn.execute(query, *params)
                return result.split()[-1] == '1'
        except Exception as e:
            logger.error(f"Failed to update contract view: {e}")
            return False

    async def delete_contract_view(self, view_id: UUID) -> bool:
        """
        Delete a contract view record.

        Args:
            view_id: Contract view ID

        Returns:
            True if deleted successfully, False otherwise
        """
        query = "DELETE FROM user_contract_views WHERE id = $1"

        async with get_user_connection(self.user_id) as conn:
            result = await conn.execute(query, view_id)
        
        return result.split()[-1] == '1'

    async def get_contract_view_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get contract view statistics for user.

        Args:
            user_id: User ID as string

        Returns:
            Dictionary with view statistics
        """
        total_query = "SELECT COUNT(*) as total FROM user_contract_views WHERE user_id = $1"
        source_query = """
            SELECT source, COUNT(*) as count
            FROM user_contract_views
            WHERE user_id = $1
            GROUP BY source
            ORDER BY count DESC
        """

        async with get_user_connection(UUID(user_id) if isinstance(user_id, str) else user_id) as conn:
            total_row = await conn.fetchrow(total_query, UUID(user_id) if isinstance(user_id, str) else user_id)
            source_rows = await conn.fetch(source_query, UUID(user_id) if isinstance(user_id, str) else user_id)

        return {
            'total_views': total_row['total'],
            'by_source': {row['source']: row['count'] for row in source_rows}
        }

    async def check_user_has_access(self, user_id: str, content_hash: str) -> bool:
        """
        Check if user has access to a specific content hash.

        Args:
            user_id: User ID as string
            content_hash: Content hash identifier

        Returns:
            True if user has access, False otherwise
        """
        query = """
            SELECT EXISTS(
                SELECT 1 FROM user_contract_views 
                WHERE user_id = $1 AND content_hash = $2
            )
        """
        
        async with get_user_connection(UUID(user_id) if isinstance(user_id, str) else user_id) as conn:
            result = await conn.fetchval(
                query, 
                UUID(user_id) if isinstance(user_id, str) else user_id,
                content_hash
            )
            
        return result