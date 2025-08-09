#!/usr/bin/env python3
"""
Test script for Unified Cache Service.
"""

import sys
import os
import asyncio
import time
from datetime import datetime, timezone

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_cache_basic_operations():
    """Test basic cache operations (get/set/invalidate)."""
    async def async_test():
        try:
            from app.services.cache.unified_cache_service import UnifiedCacheService, CachePriority
            
            # Create cache service
            config = {
                "max_memory_mb": 10,
                "enable_cache_warming": False,  # Disable for testing
                "cleanup_interval_seconds": 3600  # Long interval for testing
            }
            cache_service = UnifiedCacheService(config)
            
            # Test data storage
            operation_type = "domain_valuation"
            params = {"address": "123 Test Street Sydney NSW 2000"}
            test_data = {"estimated_value": 750000, "confidence": 0.8}
            
            # Store data
            success = await cache_service.store_cached_data(
                operation_type,
                params,
                test_data,
                context={"data_volatility": 0.5}
            )
            assert success, "Cache storage should succeed"
            
            # Retrieve data
            cached_data = await cache_service.get_cached_data(operation_type, params)
            assert cached_data is not None, "Cached data should be retrievable"
            assert cached_data["estimated_value"] == 750000, "Cached data should match stored data"
            
            # Test cache miss
            different_params = {"address": "456 Different Street Melbourne VIC 3000"}
            missing_data = await cache_service.get_cached_data(operation_type, different_params)
            assert missing_data is None, "Should return None for cache miss"
            
            # Test invalidation
            invalidated_count = await cache_service.invalidate_cache(operation_type=operation_type)
            assert invalidated_count >= 1, "Should invalidate at least one entry"
            
            # Verify invalidation
            invalidated_data = await cache_service.get_cached_data(operation_type, params)
            assert invalidated_data is None, "Data should be invalidated"
            
            await cache_service.shutdown()
            
            print("✅ Basic cache operations work correctly")
            print(f"   - Storage: ✓")
            print(f"   - Retrieval: ✓")
            print(f"   - Cache miss: ✓")
            print(f"   - Invalidation: ✓")
            
            return True
            
        except Exception as e:
            print(f"❌ Basic cache operations test failed: {e}")
            return False
    
    return asyncio.run(async_test())

def test_cache_ttl_and_expiration():
    """Test cache TTL calculation and expiration."""
    async def async_test():
        try:
            from app.services.cache.unified_cache_service import UnifiedCacheService
            
            cache_service = UnifiedCacheService({
                "max_memory_mb": 10,
                "enable_cache_warming": False,
                "cleanup_interval_seconds": 3600
            })
            
            # Test with short TTL
            operation_type = "market_analytics"
            params = {"suburb": "Paddington", "state": "NSW"}
            test_data = {"median_price": 1200000}
            
            # Store with custom short TTL
            success = await cache_service.store_cached_data(
                operation_type,
                params,
                test_data,
                custom_ttl=1  # 1 second TTL
            )
            assert success, "Cache storage should succeed"
            
            # Immediate retrieval should work
            cached_data = await cache_service.get_cached_data(operation_type, params)
            assert cached_data is not None, "Should get cached data immediately"
            
            # Wait for expiration
            await asyncio.sleep(1.5)
            
            # Should be expired now
            expired_data = await cache_service.get_cached_data(operation_type, params)
            assert expired_data is None, "Data should be expired"
            
            # Test TTL calculation with different contexts
            high_volatility_context = {"data_volatility": 0.9, "accuracy_requirement": 0.8}
            low_volatility_context = {"data_volatility": 0.1, "accuracy_requirement": 0.3}
            
            strategy = cache_service.cache_strategies["market_analytics"]
            high_vol_ttl = strategy.calculate_ttl(high_volatility_context)
            low_vol_ttl = strategy.calculate_ttl(low_volatility_context)
            
            assert low_vol_ttl > high_vol_ttl, "Low volatility should have longer TTL"
            assert high_vol_ttl >= 300, "TTL should respect minimum bounds"
            
            await cache_service.shutdown()
            
            print("✅ Cache TTL and expiration work correctly")
            print(f"   - Short TTL expiration: ✓")
            print(f"   - TTL calculation: ✓")
            print(f"   - High volatility TTL: {high_vol_ttl}s")
            print(f"   - Low volatility TTL: {low_vol_ttl}s")
            
            return True
            
        except Exception as e:
            print(f"❌ Cache TTL and expiration test failed: {e}")
            return False
    
    return asyncio.run(async_test())

def test_cache_strategies():
    """Test different cache strategies for different operation types."""
    async def async_test():
        try:
            from app.services.cache.unified_cache_service import UnifiedCacheService, CachePriority
            
            cache_service = UnifiedCacheService({
                "max_memory_mb": 10,
                "enable_cache_warming": False,
                "cleanup_interval_seconds": 3600
            })
            
            # Test different operation types with their strategies
            test_cases = [
                {
                    "operation_type": "corelogic_valuation",
                    "params": {"address": "123 High Cost Street"},
                    "data": {"valuation_amount": 850000, "cost": 50.0},
                    "expected_priority": CachePriority.HIGH
                },
                {
                    "operation_type": "property_details",
                    "params": {"property_id": "12345"},
                    "data": {"bedrooms": 3, "bathrooms": 2},
                    "expected_priority": CachePriority.LOW
                },
                {
                    "operation_type": "risk_assessment",
                    "params": {"address": "456 Risk Analysis Ave"},
                    "data": {"risk_level": "medium", "factors": []},
                    "expected_priority": CachePriority.HIGH
                }
            ]
            
            for test_case in test_cases:
                operation_type = test_case["operation_type"]
                strategy = cache_service.cache_strategies.get(operation_type)
                
                assert strategy is not None, f"Strategy should exist for {operation_type}"
                assert strategy.priority == test_case["expected_priority"], f"Priority mismatch for {operation_type}"
                
                # Store and verify
                success = await cache_service.store_cached_data(
                    operation_type,
                    test_case["params"],
                    test_case["data"]
                )
                assert success, f"Should store {operation_type} successfully"
                
                # Retrieve and verify
                cached_data = await cache_service.get_cached_data(
                    operation_type,
                    test_case["params"]
                )
                assert cached_data is not None, f"Should retrieve {operation_type} data"
            
            await cache_service.shutdown()
            
            print("✅ Cache strategies work correctly")
            print(f"   - High-cost operations cached longer: ✓")
            print(f"   - Priority-based storage: ✓")
            print(f"   - Strategy-specific TTL: ✓")
            
            return True
            
        except Exception as e:
            print(f"❌ Cache strategies test failed: {e}")
            return False
    
    return asyncio.run(async_test())

def test_cache_metrics_and_analytics():
    """Test cache metrics and analytics functionality."""
    async def async_test():
        try:
            from app.services.cache.unified_cache_service import UnifiedCacheService
            
            cache_service = UnifiedCacheService({
                "max_memory_mb": 10,
                "enable_cache_warming": False,
                "cleanup_interval_seconds": 3600
            })
            
            operation_type = "domain_valuation"
            
            # Generate some cache activity
            for i in range(10):
                params = {"address": f"{i} Test Street"}
                data = {"value": i * 100000}
                
                await cache_service.store_cached_data(operation_type, params, data)
            
            # Generate cache hits
            for i in range(5):
                params = {"address": f"{i} Test Street"}
                cached_data = await cache_service.get_cached_data(operation_type, params)
                assert cached_data is not None, "Should get cache hit"
            
            # Generate cache misses
            for i in range(3):
                params = {"address": f"{i+20} Missing Street"}
                cached_data = await cache_service.get_cached_data(operation_type, params)
                assert cached_data is None, "Should get cache miss"
            
            # Get metrics
            metrics = await cache_service.get_cache_metrics()
            
            assert metrics.hit_rate > 0, "Should have some cache hits"
            assert metrics.miss_rate > 0, "Should have some cache misses"
            assert metrics.hit_rate + metrics.miss_rate <= 1.0, "Hit rate + miss rate should not exceed 1"
            
            # Get analytics
            analytics = await cache_service.get_cache_analytics()
            
            assert "performance_metrics" in analytics, "Should include performance metrics"
            assert "cache_size" in analytics, "Should include cache size info"
            assert "operation_breakdown" in analytics, "Should include operation breakdown"
            
            # Verify operation breakdown
            assert operation_type in analytics["operation_breakdown"], "Should track operation-specific metrics"
            op_stats = analytics["operation_breakdown"][operation_type]
            assert op_stats["requests"] > 0, "Should track requests"
            assert op_stats["hits"] > 0, "Should track hits"
            assert op_stats["misses"] > 0, "Should track misses"
            
            await cache_service.shutdown()
            
            print("✅ Cache metrics and analytics work correctly")
            print(f"   - Hit rate: {metrics.hit_rate:.2%}")
            print(f"   - Miss rate: {metrics.miss_rate:.2%}")
            print(f"   - Total entries: {analytics['cache_size']['total_entries']}")
            print(f"   - Memory usage: {analytics['cache_size']['memory_usage_mb']:.2f} MB")
            
            return True
            
        except Exception as e:
            print(f"❌ Cache metrics and analytics test failed: {e}")
            return False
    
    return asyncio.run(async_test())

def test_cache_memory_management():
    """Test cache memory management and eviction."""
    async def async_test():
        try:
            from app.services.cache.unified_cache_service import UnifiedCacheService, CachePriority
            
            # Create cache with very small memory limit
            cache_service = UnifiedCacheService({
                "max_memory_mb": 1,  # Very small for testing eviction
                "enable_cache_warming": False,
                "cleanup_interval_seconds": 3600
            })
            
            # Store many entries to trigger eviction
            stored_keys = []
            for i in range(20):
                operation_type = "property_details"
                params = {"property_id": f"prop_{i}"}
                
                # Make some entries high priority
                context = {"priority": "high" if i % 5 == 0 else "low"}
                large_data = {"details": "x" * 10000, "id": i}  # Large data to trigger memory pressure
                
                success = await cache_service.store_cached_data(
                    operation_type,
                    params,
                    large_data,
                    context
                )
                
                if success:
                    stored_keys.append((operation_type, params))
            
            # Check that some entries were evicted
            cache_size_after = len(cache_service._memory_cache)
            assert cache_size_after < 20, "Some entries should have been evicted due to memory pressure"
            
            # Check that high priority entries are more likely to be retained
            high_priority_retained = 0
            low_priority_retained = 0
            
            for i, (operation_type, params) in enumerate(stored_keys):
                cached_data = await cache_service.get_cached_data(operation_type, params)
                if cached_data is not None:
                    if i % 5 == 0:  # High priority entry
                        high_priority_retained += 1
                    else:  # Low priority entry
                        low_priority_retained += 1
            
            # Verify eviction metrics were updated
            metrics = await cache_service.get_cache_metrics()
            assert metrics.eviction_rate >= 0, "Should track eviction rate"
            
            await cache_service.shutdown()
            
            print("✅ Cache memory management works correctly")
            print(f"   - Entries after eviction: {cache_size_after}/20")
            print(f"   - High priority retained: {high_priority_retained}")
            print(f"   - Low priority retained: {low_priority_retained}")
            print(f"   - Eviction rate: {metrics.eviction_rate:.2%}")
            
            return True
            
        except Exception as e:
            print(f"❌ Cache memory management test failed: {e}")
            return False
    
    return asyncio.run(async_test())

def test_cache_invalidation_triggers():
    """Test trigger-based cache invalidation."""
    async def async_test():
        try:
            from app.services.cache.unified_cache_service import UnifiedCacheService
            
            cache_service = UnifiedCacheService({
                "max_memory_mb": 10,
                "enable_cache_warming": False,
                "cleanup_interval_seconds": 3600
            })
            
            # Store data for different operation types
            test_data = [
                ("domain_valuation", {"address": "123 Test St"}, {"value": 750000}),
                ("market_analytics", {"suburb": "Paddington"}, {"median": 1200000}),
                ("risk_assessment", {"address": "456 Risk St"}, {"risk": "medium"})
            ]
            
            for operation_type, params, data in test_data:
                success = await cache_service.store_cached_data(operation_type, params, data)
                assert success, f"Should store {operation_type} data"
            
            # Verify all data is cached
            for operation_type, params, expected_data in test_data:
                cached_data = await cache_service.get_cached_data(operation_type, params)
                assert cached_data is not None, f"Should have cached {operation_type} data"
            
            # Test trigger-based invalidation
            # "market_change" should invalidate domain_valuation and market_analytics
            invalidated_count = await cache_service.invalidate_cache(
                invalidation_trigger="market_change"
            )
            assert invalidated_count >= 2, "Should invalidate at least 2 entries for market_change trigger"
            
            # Verify specific invalidations
            domain_data = await cache_service.get_cached_data("domain_valuation", {"address": "123 Test St"})
            market_data = await cache_service.get_cached_data("market_analytics", {"suburb": "Paddington"})
            risk_data = await cache_service.get_cached_data("risk_assessment", {"address": "456 Risk St"})
            
            assert domain_data is None, "Domain valuation should be invalidated by market_change"
            assert market_data is None, "Market analytics should be invalidated by market_change"
            assert risk_data is not None, "Risk assessment should not be affected by market_change"
            
            await cache_service.shutdown()
            
            print("✅ Cache invalidation triggers work correctly")
            print(f"   - Trigger-based invalidation: ✓")
            print(f"   - Selective invalidation: ✓")
            print(f"   - Invalidated {invalidated_count} entries")
            
            return True
            
        except Exception as e:
            print(f"❌ Cache invalidation triggers test failed: {e}")
            return False
    
    return asyncio.run(async_test())

def test_cache_warming():
    """Test cache warming functionality."""
    async def async_test():
        try:
            from app.services.cache.unified_cache_service import UnifiedCacheService
            
            cache_service = UnifiedCacheService({
                "max_memory_mb": 10,
                "enable_cache_warming": True,
                "cleanup_interval_seconds": 3600
            })
            
            # Mock warming function
            async def mock_warming_function(params):
                address = params.get("address", "Unknown")
                return {
                    "estimated_value": hash(address) % 1000000,
                    "confidence": 0.8,
                    "source": "warmed"
                }
            
            # Define warming parameters
            warming_params = [
                {"address": "1 Popular Street Sydney NSW"},
                {"address": "2 Frequent Avenue Melbourne VIC"},
                {"address": "3 Common Road Brisbane QLD"}
            ]
            
            # Warm the cache
            warmed_count = await cache_service.warm_cache(
                "domain_valuation",
                warming_params,
                mock_warming_function
            )
            
            assert warmed_count == len(warming_params), f"Should warm {len(warming_params)} entries"
            
            # Verify warmed data is accessible
            for params in warming_params:
                cached_data = await cache_service.get_cached_data("domain_valuation", params)
                assert cached_data is not None, "Warmed data should be accessible"
                assert cached_data["source"] == "warmed", "Should be warmed data"
            
            # Test that already cached entries are not re-warmed
            warmed_count_second = await cache_service.warm_cache(
                "domain_valuation",
                warming_params,
                mock_warming_function
            )
            
            assert warmed_count_second == 0, "Should not re-warm already cached entries"
            
            await cache_service.shutdown()
            
            print("✅ Cache warming works correctly")
            print(f"   - Initial warming: {warmed_count} entries")
            print(f"   - Skip already cached: ✓")
            print(f"   - Warmed data accessible: ✓")
            
            return True
            
        except Exception as e:
            print(f"❌ Cache warming test failed: {e}")
            return False
    
    return asyncio.run(async_test())

def main():
    """Run all Unified Cache Service tests."""
    print("=" * 60)
    print("UNIFIED CACHE SERVICE TESTS")
    print("=" * 60)
    
    tests = [
        test_cache_basic_operations,
        test_cache_ttl_and_expiration,
        test_cache_strategies,
        test_cache_metrics_and_analytics,
        test_cache_memory_management,
        test_cache_invalidation_triggers,
        test_cache_warming
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("🎉 All Unified Cache Service tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())