"""
Cache Management Utilities
Command-line tools for cache administration and monitoring
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import argparse

from app.services.cache_service import CacheService
from app.clients.factory import get_supabase_client

logger = logging.getLogger(__name__)


class CacheManager:
    """Command-line cache management utilities."""

    def __init__(self):
        self.cache_service: Optional[CacheService] = None
        self.initialized = False

    async def initialize(self) -> None:
        """Initialize cache manager with database connection."""
        try:
            db_client = await get_supabase_client(use_service_role=True)
            self.cache_service = CacheService(db_client)
            await self.cache_service.initialize()
            self.initialized = True
            logger.info("Cache manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize cache manager: {str(e)}")
            raise

    def _ensure_initialized(self):
        """Ensure cache manager is initialized."""
        if not self.initialized or not self.cache_service:
            raise RuntimeError("Cache manager not initialized. Call initialize() first.")

    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        self._ensure_initialized()
        
        stats = await self.cache_service.get_cache_stats()
        consistency = await self.cache_service.validate_hash_consistency()
        
        return {
            "cache_stats": stats,
            "hash_consistency": consistency,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def cleanup_expired(self) -> Dict[str, int]:
        """Clean up expired cache entries."""
        self._ensure_initialized()
        
        result = await self.cache_service.cleanup_expired_cache()
        logger.info(f"Cache cleanup completed: {result}")
        return result

    async def rebuild_cache(
        self, 
        min_confidence: float = 0.7,
        days_back: int = 30,
        max_entries: int = 1000
    ) -> int:
        """Rebuild contract cache from high-quality analyses."""
        self._ensure_initialized()
        
        try:
            # Call the database function to rebuild cache
            result = await self.cache_service.db_client.rpc(
                "rebuild_contract_cache",
                {
                    "min_confidence": min_confidence,
                    "days_back": days_back,
                    "max_entries": max_entries
                }
            )
            
            if result:
                entries_created = result if isinstance(result, int) else result[0]
                logger.info(f"Cache rebuilt with {entries_created} entries")
                return entries_created
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Error rebuilding cache: {str(e)}")
            raise

    async def validate_integrity(self) -> Dict[str, Any]:
        """Validate cache integrity and consistency."""
        self._ensure_initialized()
        
        try:
            # Get hash consistency validation
            consistency = await self.cache_service.validate_hash_consistency()
            
            # Check for common issues
            issues = []
            warnings = []
            
            for table, data in consistency.items():
                percentage = data.get("consistency_percentage", 0)
                if percentage < 100:
                    if percentage < 90:
                        issues.append(f"Low hash consistency in {table}: {percentage}%")
                    else:
                        warnings.append(f"Minor hash inconsistency in {table}: {percentage}%")
            
            # Check cache sizes
            stats = await self.cache_service.get_cache_stats()
            total_cached = (stats.get("contracts", {}).get("total_cached", 0) + 
                          stats.get("properties", {}).get("total_cached", 0))
            
            if total_cached == 0:
                warnings.append("No active cache entries found")
            
            return {
                "status": "healthy" if not issues else ("warning" if not issues and warnings else "critical"),
                "issues": issues,
                "warnings": warnings,
                "consistency": consistency,
                "stats": stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error validating cache integrity: {str(e)}")
            return {
                "status": "critical",
                "issues": [f"Integrity check failed: {str(e)}"],
                "warnings": [],
                "timestamp": datetime.utcnow().isoformat()
            }

    async def list_popular_content(self, limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
        """List most popular cached content."""
        self._ensure_initialized()
        
        try:
            # Get popular contracts
            popular_contracts = await self.cache_service.db_client.database.select(
                "hot_contracts_cache",
                columns="content_hash, property_address, access_count, created_at, expires_at",
                filters={"expires_at__gte": datetime.utcnow().isoformat()},
                order={"access_count": "desc"},
                limit=limit
            )
            
            # Get popular properties
            popular_properties = await self.cache_service.db_client.database.select(
                "hot_properties_cache", 
                columns="property_hash, property_address, popularity_score, access_count, created_at, expires_at",
                filters={"expires_at__gte": datetime.utcnow().isoformat()},
                order={"popularity_score": "desc"},
                limit=limit
            )
            
            return {
                "popular_contracts": popular_contracts.get("data", []),
                "popular_properties": popular_properties.get("data", [])
            }
            
        except Exception as e:
            logger.error(f"Error listing popular content: {str(e)}")
            return {"popular_contracts": [], "popular_properties": []}

    async def purge_cache(self, cache_type: Optional[str] = None, confirm: bool = False) -> Dict[str, int]:
        """Purge cache entries (use with caution)."""
        self._ensure_initialized()
        
        if not confirm:
            raise ValueError("Cache purge requires explicit confirmation (confirm=True)")
        
        try:
            deleted_counts = {"contracts": 0, "properties": 0}
            
            if cache_type in [None, "contracts"]:
                # Delete all contract cache entries
                await self.cache_service.db_client.database.delete(
                    "hot_contracts_cache", filters={}
                )
                deleted_counts["contracts"] = "all"
            
            if cache_type in [None, "properties"]:
                # Delete all property cache entries
                await self.cache_service.db_client.database.delete(
                    "hot_properties_cache", filters={}
                )
                deleted_counts["properties"] = "all"
            
            logger.info(f"Cache purge completed: {deleted_counts}")
            return deleted_counts
            
        except Exception as e:
            logger.error(f"Error purging cache: {str(e)}")
            raise

    async def monitor_performance(self, duration_minutes: int = 5) -> Dict[str, Any]:
        """Monitor cache performance over time."""
        self._ensure_initialized()
        
        logger.info(f"Starting {duration_minutes}-minute cache performance monitoring...")
        
        # Take initial measurements
        initial_stats = await self.cache_service.get_cache_stats()
        start_time = datetime.utcnow()
        
        # Wait for monitoring period
        await asyncio.sleep(duration_minutes * 60)
        
        # Take final measurements
        final_stats = await self.cache_service.get_cache_stats()
        end_time = datetime.utcnow()
        
        # Calculate performance metrics
        duration = (end_time - start_time).total_seconds()
        
        return {
            "monitoring_period": f"{duration_minutes} minutes",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "initial_stats": initial_stats,
            "final_stats": final_stats,
            "performance_summary": {
                "monitoring_duration_seconds": duration,
                "cache_operations_detected": "N/A (would need request logging)",
                "status": "monitoring_completed"
            }
        }


# CLI Interface
async def main():
    """Main CLI interface for cache management."""
    parser = argparse.ArgumentParser(description="Real2.AI Cache Management Utilities")
    parser.add_argument("command", choices=[
        "stats", "cleanup", "rebuild", "validate", "popular", 
        "purge", "monitor", "health"
    ], help="Command to execute")
    
    # Command-specific arguments
    parser.add_argument("--min-confidence", type=float, default=0.7,
                       help="Minimum confidence for cache rebuild (default: 0.7)")
    parser.add_argument("--days-back", type=int, default=30,
                       help="Days back to look for rebuild data (default: 30)")
    parser.add_argument("--max-entries", type=int, default=1000,
                       help="Maximum cache entries to create (default: 1000)")
    parser.add_argument("--limit", type=int, default=20,
                       help="Limit for list operations (default: 20)")
    parser.add_argument("--cache-type", choices=["contracts", "properties"],
                       help="Cache type for purge operations")
    parser.add_argument("--confirm", action="store_true",
                       help="Confirm destructive operations")
    parser.add_argument("--monitor-duration", type=int, default=5,
                       help="Monitoring duration in minutes (default: 5)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Initialize cache manager
    cache_manager = CacheManager()
    try:
        await cache_manager.initialize()
    except Exception as e:
        print(f"Failed to initialize cache manager: {str(e)}")
        sys.exit(1)

    # Execute command
    try:
        if args.command == "stats":
            result = await cache_manager.get_stats()
            print("=== Cache Statistics ===")
            print(f"Timestamp: {result['timestamp']}")
            print("\nCache Stats:")
            for cache_type, stats in result['cache_stats'].items():
                if cache_type != "last_updated":
                    print(f"  {cache_type.title()}: {stats}")
            
            print("\nHash Consistency:")
            for table, data in result['hash_consistency'].items():
                print(f"  {table}: {data['consistency_percentage']}% ({data['records_with_hashes']}/{data['total_records']})")

        elif args.command == "cleanup":
            result = await cache_manager.cleanup_expired()
            print("=== Cache Cleanup Results ===")
            print(f"Properties deleted: {result['properties_deleted']}")
            print(f"Contracts deleted: {result['contracts_deleted']}")

        elif args.command == "rebuild":
            result = await cache_manager.rebuild_cache(
                args.min_confidence, args.days_back, args.max_entries
            )
            print("=== Cache Rebuild Results ===")
            print(f"Cache entries created: {result}")

        elif args.command == "validate":
            result = await cache_manager.validate_integrity()
            print("=== Cache Validation Results ===")
            print(f"Status: {result['status']}")
            print(f"Timestamp: {result['timestamp']}")
            
            if result['issues']:
                print("\nIssues:")
                for issue in result['issues']:
                    print(f"  ❌ {issue}")
            
            if result['warnings']:
                print("\nWarnings:")
                for warning in result['warnings']:
                    print(f"  ⚠️  {warning}")
            
            if not result['issues'] and not result['warnings']:
                print("\n✅ No issues found")

        elif args.command == "popular":
            result = await cache_manager.list_popular_content(args.limit)
            print("=== Popular Cached Content ===")
            
            print("\nTop Contracts:")
            for contract in result['popular_contracts'][:10]:
                print(f"  {contract.get('property_address', 'Unknown')} - {contract['access_count']} accesses")
            
            print("\nTop Properties:")
            for prop in result['popular_properties'][:10]:
                print(f"  {prop['property_address']} - Score: {prop['popularity_score']}")

        elif args.command == "purge":
            if not args.confirm:
                print("⚠️  Cache purge is destructive and requires --confirm flag")
                sys.exit(1)
            
            result = await cache_manager.purge_cache(args.cache_type, args.confirm)
            print("=== Cache Purge Results ===")
            for cache_type, count in result.items():
                print(f"{cache_type.title()} deleted: {count}")

        elif args.command == "monitor":
            print(f"🔍 Starting {args.monitor_duration}-minute performance monitoring...")
            result = await cache_manager.monitor_performance(args.monitor_duration)
            print("=== Performance Monitoring Results ===")
            print(f"Period: {result['monitoring_period']}")
            print(f"Start: {result['start_time']}")
            print(f"End: {result['end_time']}")
            print(f"Status: {result['performance_summary']['status']}")

        elif args.command == "health":
            result = await cache_manager.validate_integrity()
            status_emoji = {"healthy": "✅", "warning": "⚠️", "critical": "❌"}
            print(f"{status_emoji.get(result['status'], '❓')} Cache Health: {result['status'].upper()}")
            
            if result['issues']:
                print("\nCritical Issues:")
                for issue in result['issues']:
                    print(f"  ❌ {issue}")
            
            if result['warnings']:
                print("\nWarnings:")
                for warning in result['warnings']:
                    print(f"  ⚠️  {warning}")

    except Exception as e:
        print(f"Command failed: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())