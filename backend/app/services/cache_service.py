"""
Cache Service Implementation
Handles document processing cache operations with hash-based lookups
"""

import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.clients.base.interfaces import DatabaseOperations
from app.clients.supabase.client import SupabaseClient
from app.core.auth_context import AuthContext
from app.clients.factory import get_service_supabase_client
from app.models.supabase_models import Document, Contract, ContractAnalysis

logger = logging.getLogger(__name__)


class CacheService:
    """Service for managing document processing cache operations."""

    def __init__(self, db_client: Optional[SupabaseClient] = None):
        self.db_client = db_client
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize cache service with database client."""
        if not self.db_client:
            self.db_client = await get_service_supabase_client()

        if not hasattr(self.db_client, "_client") or self.db_client._client is None:
            await self.db_client.initialize()

        self._initialized = True
        logger.info("Cache service initialized successfully")

    def _ensure_initialized(self) -> None:
        """Ensure service is initialized before operations."""
        if not self._initialized or not self.db_client:
            raise RuntimeError(
                "Cache service not initialized. Call initialize() first."
            )

    @staticmethod
    def generate_content_hash(content: bytes) -> str:
        """Generate SHA-256 hash for content."""
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def normalize_address(address: str) -> str:
        """Normalize address for consistent hashing."""
        import re

        # Remove punctuation and normalize whitespace
        normalized = re.sub(r"[^\w\s]", "", address.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    @staticmethod
    def generate_property_hash(address: str) -> str:
        """Generate hash for property address."""
        normalized = CacheService.normalize_address(address)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    # =====================================================
    # CONTRACT CACHE OPERATIONS
    # =====================================================

    async def check_contract_cache(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """
        Check if contract analysis exists in cache.

        Args:
            content_hash: SHA-256 hash of document content

        Returns:
            Cached analysis result or None if not found
        """
        self._ensure_initialized()

        try:
            # Check hot contracts cache
            cache_result = await self.db_client.database.select(
                "hot_contracts_cache",
                columns="*",
                filters={
                    "content_hash": content_hash,
                    "expires_at__gte": datetime.utcnow().isoformat(),
                },
            )

            if not cache_result.get("data"):
                logger.debug(f"No cache entry found for content_hash: {content_hash}")
                return None

            cache_entry = cache_result["data"][0]

            # Update access count and extend expiration for popular content
            await self._increment_cache_access(content_hash, "contract")

            logger.info(f"Cache hit for content_hash: {content_hash}")
            return cache_entry["contract_analysis"]

        except Exception as e:
            logger.error(f"Error checking contract cache: {str(e)}")
            return None

    async def cache_contract_analysis(
        self,
        content_hash: str,
        analysis_result: Dict[str, Any],
        property_address: Optional[str] = None,
        contract_type: Optional[str] = None,
        ttl_hours: int = 24,
    ) -> bool:
        """
        Cache contract analysis result.

        Args:
            content_hash: SHA-256 hash of document content
            analysis_result: Analysis result to cache
            property_address: Optional property address
            contract_type: Optional contract type
            ttl_hours: Time to live in hours (default: 24)

        Returns:
            True if cached successfully, False otherwise
        """
        self._ensure_initialized()

        try:
            expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)

            cache_data = {
                "content_hash": content_hash,
                "contract_analysis": analysis_result,
                "property_address": property_address,
                "contract_type": contract_type,
                "access_count": 1,
                "expires_at": expires_at.isoformat(),
            }

            # Use upsert to handle duplicate hash entries
            result = await self.db_client.database.upsert(
                "hot_contracts_cache", cache_data, on_conflict="content_hash"
            )

            if result.get("success"):
                logger.info(
                    f"Successfully cached contract analysis for hash: {content_hash}"
                )
                return True
            else:
                logger.error(
                    f"Failed to cache contract analysis: {result.get('error')}"
                )
                return False

        except Exception as e:
            logger.error(f"Error caching contract analysis: {str(e)}")
            return False

    async def create_user_contract_from_cache(
        self,
        user_id: str,
        content_hash: str,
        cached_analysis: Dict[str, Any],
        original_filename: str = "Cached Document",
        file_size: int = 0,
        mime_type: str = "application/pdf",
        property_address: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        """
        Create user document, contract, and analysis records from cache hit.

        Args:
            user_id: User ID
            content_hash: Content hash
            cached_analysis: Cached analysis result
            original_filename: Original filename
            file_size: File size
            mime_type: MIME type
            property_address: Property address

        Returns:
            Tuple of (document_id, contract_id, analysis_id)
        """
        self._ensure_initialized()

        try:
            # Use service role function for elevated privileges
            result = await self.db_client.rpc(
                "process_contract_cache_hit",
                {
                    "p_user_id": user_id,
                    "p_content_hash": content_hash,
                    "p_filename": original_filename,
                    "p_file_size": file_size,
                    "p_mime_type": mime_type,
                    "p_property_address": property_address,
                },
            )

            if result and len(result) > 0:
                record = result[0]
                document_id = record.get("document_id")
                analysis_id = record.get("analysis_id")
                view_id = record.get("view_id")

                # Get contract_id from the document
                contract_result = await self.db_client.database.select(
                    "contracts",
                    columns="id",
                    filters={"document_id": document_id, "user_id": user_id},
                )

                contract_id = (
                    contract_result["data"][0]["id"]
                    if contract_result.get("data")
                    else None
                )

                logger.info(
                    f"Created user records from cache hit: doc={document_id}, contract={contract_id}, analysis={analysis_id}"
                )
                return document_id, contract_id, analysis_id

            else:
                raise ValueError("Failed to create user records from cache")

        except Exception as e:
            logger.error(f"Error creating user records from cache: {str(e)}")
            raise

    # =====================================================
    # PROPERTY CACHE OPERATIONS
    # =====================================================

    async def check_property_cache(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Check if property analysis exists in cache.

        Args:
            address: Property address

        Returns:
            Cached analysis result or None if not found
        """
        self._ensure_initialized()

        try:
            property_hash = self.generate_property_hash(address)

            cache_result = await self.db_client.database.select(
                "hot_properties_cache",
                columns="*",
                filters={
                    "property_hash": property_hash,
                    "expires_at__gte": datetime.utcnow().isoformat(),
                },
            )

            if not cache_result.get("data"):
                logger.debug(f"No cache entry found for property: {address}")
                return None

            cache_entry = cache_result["data"][0]

            # Update popularity and extend expiration
            await self._increment_cache_access(property_hash, "property")

            logger.info(f"Cache hit for property: {address}")
            return cache_entry["analysis_result"]

        except Exception as e:
            logger.error(f"Error checking property cache: {str(e)}")
            return None

    async def cache_property_analysis(
        self, address: str, analysis_result: Dict[str, Any], ttl_hours: int = 48
    ) -> bool:
        """
        Cache property analysis result.

        Args:
            address: Property address
            analysis_result: Analysis result to cache
            ttl_hours: Time to live in hours (default: 48)

        Returns:
            True if cached successfully, False otherwise
        """
        self._ensure_initialized()

        try:
            property_hash = self.generate_property_hash(address)
            normalized_address = self.normalize_address(address)
            expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)

            cache_data = {
                "property_hash": property_hash,
                "property_address": address,
                "normalized_address": normalized_address,
                "analysis_result": analysis_result,
                "popularity_score": 1,
                "access_count": 1,
                "expires_at": expires_at.isoformat(),
            }

            result = await self.db_client.database.upsert(
                "hot_properties_cache", cache_data, on_conflict="property_hash"
            )

            if result.get("success"):
                logger.info(f"Successfully cached property analysis for: {address}")
                return True
            else:
                logger.error(
                    f"Failed to cache property analysis: {result.get('error')}"
                )
                return False

        except Exception as e:
            logger.error(f"Error caching property analysis: {str(e)}")
            return False

    async def log_user_property_view(
        self, user_id: str, address: str, source: str = "search"
    ) -> bool:
        """
        Log user property view for history tracking.

        Args:
            user_id: User ID
            address: Property address
            source: View source (search, bookmark, analysis)

        Returns:
            True if logged successfully, False otherwise
        """
        self._ensure_initialized()

        try:
            property_hash = self.generate_property_hash(address)

            view_data = {
                "user_id": user_id,
                "property_hash": property_hash,
                "property_address": address,
                "source": source,
            }

            # Get user client for RLS
            user_client = await AuthContext.get_authenticated_client()
            result = await user_client.database.insert("user_property_views", view_data)

            if result.get("success"):
                logger.debug(f"Logged property view for user {user_id}: {address}")
                return True
            else:
                logger.error(f"Failed to log property view: {result.get('error')}")
                return False

        except Exception as e:
            logger.error(f"Error logging property view: {str(e)}")
            return False

    # =====================================================
    # USER HISTORY OPERATIONS
    # =====================================================

    async def get_user_contract_history(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get user's contract analysis history.

        Args:
            user_id: User ID
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of contract view records
        """
        self._ensure_initialized()

        try:
            # Use view that combines contract views with analysis data
            user_client = await AuthContext.get_authenticated_client()
            result = await user_client.database.select(
                "user_contract_history",
                columns="*",
                filters={"user_id": user_id},
                order={"viewed_at": "desc"},
                limit=limit,
                offset=offset,
            )

            if result.get("data"):
                logger.debug(
                    f"Retrieved {len(result['data'])} contract history records for user {user_id}"
                )
                return result["data"]
            else:
                return []

        except Exception as e:
            logger.error(f"Error getting user contract history: {str(e)}")
            return []

    async def get_user_property_history(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get user's property search history.

        Args:
            user_id: User ID
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of property view records
        """
        self._ensure_initialized()

        try:
            user_client = await AuthContext.get_authenticated_client()
            result = await user_client.database.select(
                "user_property_history",
                columns="*",
                filters={"user_id": user_id},
                order={"viewed_at": "desc"},
                limit=limit,
                offset=offset,
            )

            if result.get("data"):
                logger.debug(
                    f"Retrieved {len(result['data'])} property history records for user {user_id}"
                )
                return result["data"]
            else:
                return []

        except Exception as e:
            logger.error(f"Error getting user property history: {str(e)}")
            return []

    # =====================================================
    # CACHE MANAGEMENT OPERATIONS
    # =====================================================

    async def _increment_cache_access(self, hash_value: str, cache_type: str) -> None:
        """
        Increment cache access count and extend expiration for popular content.

        Args:
            hash_value: Cache key hash
            cache_type: 'contract' or 'property'
        """
        try:
            await self.db_client.rpc(
                "increment_cache_popularity",
                {"cache_type": cache_type, "hash_value": hash_value},
            )
        except Exception as e:
            logger.error(f"Error incrementing cache access: {str(e)}")

    async def cleanup_expired_cache(self) -> Dict[str, int]:
        """
        Clean up expired cache entries.

        Returns:
            Dictionary with counts of deleted entries
        """
        self._ensure_initialized()

        try:
            result = await self.db_client.rpc("cleanup_expired_cache")

            if result and len(result) > 0:
                cleanup_stats = result[0]
                logger.info(f"Cache cleanup completed: {cleanup_stats}")
                return {
                    "properties_deleted": cleanup_stats.get("properties_deleted", 0),
                    "contracts_deleted": cleanup_stats.get("contracts_deleted", 0),
                }
            else:
                return {"properties_deleted": 0, "contracts_deleted": 0}

        except Exception as e:
            logger.error(f"Error during cache cleanup: {str(e)}")
            return {"properties_deleted": 0, "contracts_deleted": 0}

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        self._ensure_initialized()

        try:
            # Get contract cache stats
            contract_stats = await self.db_client.database.select(
                "hot_contracts_cache",
                columns="COUNT(*) as total, AVG(access_count) as avg_access",
                filters={"expires_at__gte": datetime.utcnow().isoformat()},
            )

            # Get property cache stats
            property_stats = await self.db_client.database.select(
                "hot_properties_cache",
                columns="COUNT(*) as total, AVG(access_count) as avg_access, AVG(popularity_score) as avg_popularity",
                filters={"expires_at__gte": datetime.utcnow().isoformat()},
            )

            return {
                "contracts": {
                    "total_cached": (
                        contract_stats["data"][0]["total"]
                        if contract_stats.get("data")
                        else 0
                    ),
                    "average_access": (
                        contract_stats["data"][0]["avg_access"]
                        if contract_stats.get("data")
                        else 0
                    ),
                },
                "properties": {
                    "total_cached": (
                        property_stats["data"][0]["total"]
                        if property_stats.get("data")
                        else 0
                    ),
                    "average_access": (
                        property_stats["data"][0]["avg_access"]
                        if property_stats.get("data")
                        else 0
                    ),
                    "average_popularity": (
                        property_stats["data"][0]["avg_popularity"]
                        if property_stats.get("data")
                        else 0
                    ),
                },
                "last_updated": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {
                "contracts": {"total_cached": 0, "average_access": 0},
                "properties": {
                    "total_cached": 0,
                    "average_access": 0,
                    "average_popularity": 0,
                },
                "last_updated": datetime.utcnow().isoformat(),
                "error": str(e),
            }

    async def validate_hash_consistency(self) -> Dict[str, Dict[str, Any]]:
        """
        Validate hash consistency across tables.

        Returns:
            Dictionary with consistency validation results
        """
        self._ensure_initialized()

        try:
            result = await self.db_client.rpc("validate_hash_consistency")

            if result:
                consistency_data = {}
                for row in result:
                    consistency_data[row["table_name"]] = {
                        "total_records": row["total_records"],
                        "records_with_hashes": row["records_with_hashes"],
                        "consistency_percentage": row["consistency_percentage"],
                    }

                logger.info(
                    f"Hash consistency validation completed: {consistency_data}"
                )
                return consistency_data
            else:
                return {}

        except Exception as e:
            logger.error(f"Error validating hash consistency: {str(e)}")
            return {"error": str(e)}


# Global cache service instance
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """Get initialized cache service instance."""
    global _cache_service

    if not _cache_service:
        _cache_service = CacheService()
        await _cache_service.initialize()

    return _cache_service
