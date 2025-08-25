"""
Example usage of the Domain API client for Real2.AI platform.

This file demonstrates common usage patterns and best practices.
Run with a valid Domain API key for testing.
"""

import asyncio
import logging
import os

from .client import DomainClient
from .enhanced_client import EnhancedDomainClient
from .config import DomainClientConfig
from .settings import DomainSettings
from ..base.exceptions import (
    PropertyNotFoundError,
    PropertyValuationError,
)
from ...schema import PropertySearchRequest

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_client_example():
    """Basic Domain client usage example."""
    print("\n" + "=" * 60)
    print("BASIC DOMAIN CLIENT EXAMPLE")
    print("=" * 60)

    # Create configuration
    config = DomainClientConfig(
        api_key=os.getenv("DOMAIN_API_KEY", "test_key"),
        service_tier="standard",
        default_state="NSW",
        enable_caching=False,  # Disable for demo
        enable_request_logging=True,
    )

    # Create and initialize client
    async with DomainClient(config) as client:
        await client.initialize()

        # Check health
        health = await client.health_check()
        print(f"✓ Client Status: {health['status']}")
        print(f"  Service Tier: {health['service_tier']}")

        # Example 1: Property Search
        print(f"\n1. Property Search Example:")
        try:
            search_params = {
                "suburb": "Sydney",
                "state": "NSW",
                "listing_type": "Sale",
                "min_bedrooms": 2,
                "max_bedrooms": 4,
                "page_size": 5,
            }

            results = await client.search_properties(search_params)
            print(f"   Found {results['total_results']} properties")

            # Show first few results
            for i, listing in enumerate(results["listings"][:3], 1):
                address = listing["address"]["full_address"] or "Address not available"
                prop_type = listing["property_details"]["property_type"]
                bedrooms = listing["property_details"]["bedrooms"] or "N/A"
                print(f"   {i}. {address}")
                print(f"      Type: {prop_type}, Bedrooms: {bedrooms}")

        except Exception as e:
            print(f"   ❌ Search failed: {e}")

        # Example 2: Property Valuation
        print(f"\n2. Property Valuation Example:")
        try:
            # Use a well-known Sydney address
            test_address = "1 Macquarie Place, Sydney NSW 2000"
            valuation = await client.get_property_valuation(test_address)

            if valuation.get("valuations", {}).get("domain"):
                domain_val = valuation["valuations"]["domain"]
                estimated_value = domain_val.get("estimated_value", 0)
                confidence = domain_val.get("confidence", 0)

                print(f"   Address: {test_address}")
                print(f"   Estimated Value: ${estimated_value:,.0f}")
                print(f"   Confidence: {confidence:.2f}")
            else:
                print(f"   No valuation data available for {test_address}")

        except PropertyValuationError as e:
            print(f"   ❌ Valuation failed: {e.reason}")
        except Exception as e:
            print(f"   ❌ Valuation error: {e}")

        # Example 3: Rate Limit Status
        print(f"\n3. Rate Limit Status:")
        try:
            rate_status = await client.get_rate_limit_status()
            global_status = rate_status.get("global", {})

            print(
                f"   Requests in window: {global_status.get('requests_in_window', 0)}"
            )
            print(
                f"   Rate limit: {global_status.get('requests_per_minute_limit', 0)} RPM"
            )
            print(f"   Burst tokens: {global_status.get('burst_tokens', 0)}")

        except Exception as e:
            print(f"   ❌ Rate limit check failed: {e}")


async def enhanced_client_example():
    """Enhanced Domain client with caching example."""
    print("\n" + "=" * 60)
    print("ENHANCED DOMAIN CLIENT EXAMPLE")
    print("=" * 60)

    # Create configuration with caching enabled
    config = DomainClientConfig(
        api_key=os.getenv("DOMAIN_API_KEY", "test_key"),
        service_tier="premium",  # Premium for more features
        default_state="NSW",
        enable_caching=True,
        cache_ttl_seconds=3600,
        enable_request_logging=True,
    )

    # Create and initialize enhanced client
    async with EnhancedDomainClient(config) as client:
        await client.initialize()

        # Example 1: Comprehensive Property Profile
        print(f"\n1. Comprehensive Property Profile:")
        try:
            request = PropertySearchRequest(
                address="100 George Street, Sydney NSW 2000",
                include_valuation=True,
                include_market_data=True,
                include_comparables=True,
                include_risk_assessment=True,
                force_refresh=False,  # Use cache if available
            )

            profile_response = await client.get_property_profile(request)
            profile = profile_response.property_profile

            print(f"   Address: {profile.address.full_address}")
            print(f"   Property Type: {profile.property_details.property_type}")
            print(f"   Bedrooms: {profile.property_details.bedrooms}")
            print(f"   Profile Confidence: {profile.profile_confidence:.2f}")
            print(f"   Processing Time: {profile_response.processing_time:.3f}s")
            print(f"   Cached Data: {profile_response.cached_data}")

            # Show risk assessment if available
            if profile.risk_assessment:
                print(f"   Risk Level: {profile.risk_assessment.overall_risk}")
                print(f"   Risk Score: {profile.risk_assessment.risk_score}/100")
                if profile.risk_assessment.risk_factors:
                    print(
                        f"   Risk Factors: {len(profile.risk_assessment.risk_factors)}"
                    )

            # Show valuation if available
            if profile.valuation:
                print(f"   Estimated Value: ${profile.valuation.estimated_value:,.0f}")
                print(f"   Valuation Confidence: {profile.valuation.confidence:.2f}")

        except PropertyNotFoundError as e:
            print(f"   ❌ Property not found: {e.address}")
        except Exception as e:
            print(f"   ❌ Profile generation failed: {e}")

        # Example 2: Cache Statistics
        print(f"\n2. Cache Performance:")
        try:
            stats = await client.get_cache_statistics()
            cache_stats = stats.get("caching", {})
            perf_stats = stats.get("performance", {})

            print(f"   Cache Entries: {cache_stats.get('entries', 0)}")
            print(f"   Cache Size: {cache_stats.get('size_mb', 0):.1f} MB")
            print(f"   Hit Rate: {cache_stats.get('hit_rate', 0):.2%}")
            print(f"   API Requests Made: {perf_stats.get('requests_made', 0)}")
            print(f"   Cache Hits: {perf_stats.get('cache_hits', 0)}")
            print(f"   Cache Misses: {perf_stats.get('cache_misses', 0)}")
            print(
                f"   Average Response Time: {perf_stats.get('average_response_time', 0):.3f}s"
            )

        except Exception as e:
            print(f"   ❌ Cache stats failed: {e}")


async def error_handling_example():
    """Demonstrate error handling patterns."""
    print("\n" + "=" * 60)
    print("ERROR HANDLING EXAMPLES")
    print("=" * 60)

    config = DomainClientConfig(
        api_key="invalid_key",  # Intentionally invalid
        service_tier="standard",
        timeout=5,  # Short timeout for demo
    )

    async with DomainClient(config) as client:
        # Example 1: Authentication Error
        print(f"\n1. Authentication Error:")
        try:
            await client.initialize()
        except Exception as e:
            print(f"   ❌ Expected auth error: {type(e).__name__}")
            print(f"   Message: {str(e)[:100]}...")

        # Example 2: Property Not Found
        print(f"\n2. Property Not Found Error:")
        # Mock a valid client for this demo
        client._initialized = True
        client._session = None  # This will cause an error we can handle

        try:
            await client.get_property_details("999999999")
        except Exception as e:
            print(f"   ❌ Expected error: {type(e).__name__}")
            print(f"   Message: {str(e)[:100]}...")

        # Example 3: Invalid Address
        print(f"\n3. Invalid Address Error:")
        try:
            await client.get_property_valuation("Invalid Address 123")
        except Exception as e:
            print(f"   ❌ Expected error: {type(e).__name__}")
            print(f"   Message: {str(e)[:100]}...")


async def configuration_examples():
    """Show different configuration patterns."""
    print("\n" + "=" * 60)
    print("CONFIGURATION EXAMPLES")
    print("=" * 60)

    # Example 1: Environment-based configuration
    print("\n1. Environment-based Configuration:")
    try:
        # This would load from environment variables
        settings = DomainSettings(
            domain_api_key=os.getenv("DOMAIN_API_KEY", "test_key")
        )
        config = settings.to_client_config()

        print(
            f"   API Key: {'*' * 10 + config.api_key[-4:] if len(config.api_key) > 4 else 'NOT_SET'}"
        )
        print(f"   Service Tier: {config.service_tier}")
        print(f"   Rate Limit: {config.rate_limit_rpm} RPM")
        print(f"   Caching: {'Enabled' if config.enable_caching else 'Disabled'}")
        print(f"   Default State: {config.default_state}")

    except Exception as e:
        print(f"   ❌ Configuration error: {e}")

    # Example 2: Custom configuration
    print("\n2. Custom Configuration:")
    try:
        custom_config = DomainClientConfig(
            api_key="custom_key",
            service_tier="enterprise",
            rate_limit_rpm=5000,
            enable_caching=True,
            cache_ttl_seconds=7200,  # 2 hours
            default_state="VIC",
            connection_pool_size=50,
            timeout=60,
        )

        print(f"   Service Tier: {custom_config.service_tier}")
        print(f"   Rate Limit: {custom_config.rate_limit_rpm} RPM")
        print(f"   Cache TTL: {custom_config.cache_ttl_seconds} seconds")
        print(f"   Connection Pool: {custom_config.connection_pool_size}")
        print(
            f"   Features Available: {custom_config.is_feature_enabled('bulk_operations')}"
        )

    except Exception as e:
        print(f"   ❌ Custom config error: {e}")


async def main():
    """Run all examples."""
    print("DOMAIN API CLIENT EXAMPLES")
    print("=" * 80)
    print("These examples demonstrate the Domain API client functionality.")
    print("Set DOMAIN_API_KEY environment variable for live testing.")
    print("=" * 80)

    # Check if API key is available
    api_key = os.getenv("DOMAIN_API_KEY")
    if not api_key or api_key == "test_key":
        print("\n⚠️  WARNING: No valid DOMAIN_API_KEY found in environment")
        print("   Some examples will fail with authentication errors")
        print("   Set DOMAIN_API_KEY=your_actual_api_key for full testing")

    try:
        # Run configuration examples (these work without API key)
        await configuration_examples()

        # Run error handling examples
        await error_handling_example()

        # Only run API examples if we have a potentially valid key
        if api_key and api_key != "test_key":
            await basic_client_example()
            await enhanced_client_example()
        else:
            print("\n" + "=" * 60)
            print("SKIPPING API EXAMPLES - NO VALID API KEY")
            print("=" * 60)
            print("Set DOMAIN_API_KEY environment variable to run API examples")

    except KeyboardInterrupt:
        print("\n\n⚠️  Examples interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Example execution failed: {e}")
        logger.exception("Example execution failed")

    print("\n" + "=" * 80)
    print("EXAMPLES COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
