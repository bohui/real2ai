"""
User Property Views Repository - User property search/view history operations

This repository handles user property view tracking with RLS enforcement
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
class UserPropertyView:
    """User Property View model"""
    id: UUID
    user_id: UUID
    property_hash: str
    property_address: str
    source: str
    viewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class UserPropertyViewsRepository:
    """Repository for user property view tracking operations"""

    def __init__(self, user_id: Optional[UUID] = None):
        """
        Initialize user property views repository.
        
        Args:
            user_id: Optional user ID for user-scoped operations
        """
        self.user_id = user_id

    async def create_property_view(
        self,
        user_id: str,
        property_hash: str,
        property_address: str,
        source: str = "search"
    ) -> bool:
        """
        Create a new property view record.

        Args:
            user_id: User ID as string
            property_hash: Property hash identifier
            property_address: Property address
            source: View source (search, bookmark, analysis)

        Returns:
            True if created successfully, False otherwise
        """
        try:
            query = """
                INSERT INTO user_property_views (
                    user_id, property_hash, property_address, source
                ) VALUES ($1, $2, $3, $4)
                RETURNING id
            """
            
            async with get_user_connection(UUID(user_id) if isinstance(user_id, str) else user_id) as conn:
                result = await conn.fetchrow(
                    query, 
                    UUID(user_id) if isinstance(user_id, str) else user_id,
                    property_hash,
                    property_address,
                    source
                )
                
                return result is not None
                
        except Exception as e:
            logger.error(f"Failed to create property view: {e}")
            return False

    async def get_user_property_views(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get user's property view history.

        Args:
            user_id: User ID as string
            limit: Maximum number of views to return
            offset: Offset for pagination

        Returns:
            List of property view records
        """
        query = """
            SELECT id, user_id, property_hash, property_address, source, 
                   viewed_at, created_at
            FROM user_property_views
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
                "property_hash": row['property_hash'],
                "property_address": row['property_address'],
                "source": row['source'],
                "viewed_at": row['viewed_at'],
                "created_at": row['created_at']
            }
            for row in rows
        ]

    async def get_property_view_by_hash(
        self,
        user_id: str,
        property_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get specific property view by hash for user.

        Args:
            user_id: User ID as string
            property_hash: Property hash identifier

        Returns:
            Property view record or None if not found
        """
        query = """
            SELECT id, user_id, property_hash, property_address, source, 
                   viewed_at, created_at
            FROM user_property_views
            WHERE user_id = $1 AND property_hash = $2
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        async with get_user_connection(UUID(user_id) if isinstance(user_id, str) else user_id) as conn:
            row = await conn.fetchrow(
                query, 
                UUID(user_id) if isinstance(user_id, str) else user_id,
                property_hash
            )

        if not row:
            return None

        return {
            "id": str(row['id']),
            "user_id": str(row['user_id']),
            "property_hash": row['property_hash'],
            "property_address": row['property_address'],
            "source": row['source'],
            "viewed_at": row['viewed_at'],
            "created_at": row['created_at']
        }

    async def delete_property_view(self, view_id: UUID) -> bool:
        """
        Delete a property view record.

        Args:
            view_id: Property view ID

        Returns:
            True if deleted successfully, False otherwise
        """
        query = "DELETE FROM user_property_views WHERE id = $1"

        async with get_user_connection(self.user_id) as conn:
            result = await conn.execute(query, view_id)
        
        return result.split()[-1] == '1'

    async def get_property_view_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get property view statistics for user.

        Args:
            user_id: User ID as string

        Returns:
            Dictionary with view statistics
        """
        total_query = "SELECT COUNT(*) as total FROM user_property_views WHERE user_id = $1"
        source_query = """
            SELECT source, COUNT(*) as count
            FROM user_property_views
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