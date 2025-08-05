# Domain API Client

A comprehensive Python client for integrating with Domain.com.au's property API, specifically designed for the Real2.AI platform's Australian contract analysis needs.

## Features

- **Comprehensive Property Data**: Search properties, get detailed information, valuations, and market analytics
- **Rate Limiting**: Built-in adaptive rate limiting with exponential backoff
- **Caching**: Intelligent caching system with configurable TTL for different data types  
- **Error Handling**: Robust error handling with custom exceptions and retry logic
- **Circuit Breaker**: Resilience patterns to handle API failures gracefully
- **Australian Focus**: Specialized for Australian property market with state-specific configurations
- **Performance Monitoring**: Built-in metrics and performance tracking
- **Multiple Service Tiers**: Support for standard, premium, and enterprise API tiers

## Quick Start

### Basic Usage

```python
from app.clients.domain import DomainClient, DomainClientConfig

# Configure the client
config = DomainClientConfig(
    api_key="your_domain_api_key",
    service_tier="standard",
    default_state="NSW"
)

# Create and initialize client
client = DomainClient(config)
await client.initialize()

# Search for properties
search_params = {
    "suburb": "Sydney",
    "state": "NSW", 
    "listing_type": "Sale",
    "min_bedrooms": 2,
    "max_price": 1000000
}

results = await client.search_properties(search_params)
print(f"Found {results['total_results']} properties")

# Get property valuation
valuation = await client.get_property_valuation("123 George Street, Sydney NSW 2000")
print(f"Estimated value: ${valuation['valuations']['domain']['estimated_value']:,.0f}")
```

### Using Environment Variables

Set up your environment variables:

```bash
export DOMAIN_API_KEY="your_api_key_here"
export DOMAIN_SERVICE_TIER="premium"
export DOMAIN_DEFAULT_STATE="NSW"
export DOMAIN_ENABLE_CACHING="true"
```

```python
from app.clients.factory import get_domain_client

# Get configured client from factory
client = await get_domain_client()

# Client is automatically initialized and ready to use
health = await client.health_check()
print(f"Client status: {health['status']}")
```

### Enhanced Client with Caching

```python
from app.clients.domain.enhanced_client import EnhancedDomainClient
from app.api.models import PropertySearchRequest

# Enhanced client with caching and additional features
enhanced_client = EnhancedDomainClient(config)
await enhanced_client.initialize()

# Get comprehensive property profile
request = PropertySearchRequest(
    address="123 Collins Street, Melbourne VIC 3000",
    include_valuation=True,
    include_market_data=True,
    include_comparables=True,
    include_risk_assessment=True
)

profile = await enhanced_client.get_property_profile(request)
print(f"Property confidence: {profile.property_profile.profile_confidence:.2f}")
print(f"Risk assessment: {profile.property_profile.risk_assessment.overall_risk}")
```

## Configuration

### Service Tiers

| Tier | Rate Limit | Features |
|------|------------|----------|
| **Standard** | 500 RPM | Property search, details, sales history |
| **Premium** | 1,500 RPM | + Market analytics, comparables, demographics |
| **Enterprise** | 5,000 RPM | + Bulk operations, real-time updates |

### Configuration Options

```python
config = DomainClientConfig(
    # Required
    api_key="your_api_key",
    
    # Service Configuration  
    service_tier="premium",
    timeout=30,
    max_retries=3,
    
    # Rate Limiting
    rate_limit_rpm=1500,
    requests_per_second=10.0,
    
    # Caching
    enable_caching=True,
    cache_ttl_seconds=3600,  # 1 hour
    market_data_cache_ttl=86400,  # 24 hours
    
    # Australian Settings
    default_state="NSW",
    
    # Performance
    connection_pool_size=20,
    circuit_breaker_enabled=True,
    
    # Data Quality
    validate_responses=True,
    strict_address_validation=True
)
```

### Environment Variables

All configuration options can be set via environment variables with the `DOMAIN_` prefix:

```bash
DOMAIN_API_KEY=your_api_key
DOMAIN_SERVICE_TIER=premium
DOMAIN_TIMEOUT=30
DOMAIN_RATE_LIMIT_RPM=1500
DOMAIN_ENABLE_CACHING=true
DOMAIN_DEFAULT_STATE=NSW
DOMAIN_CONNECTION_POOL_SIZE=20
```

## API Operations

### Property Search

```python
# Basic search
search_params = {
    "suburb": "Bondi",
    "state": "NSW",
    "listing_type": "Sale",
    "page_size": 20
}
results = await client.search_properties(search_params)

# Advanced search with filters
search_params = {
    "locations": [
        {"suburb": "Toorak", "state": "VIC"},
        {"suburb": "South Yarra", "state": "VIC"}
    ],
    "min_price": 800000,
    "max_price": 2000000,
    "min_bedrooms": 3,
    "property_types": ["House", "Townhouse"]
}
results = await client.search_properties(search_params)
```

### Property Details

```python
# Get detailed property information
property_id = "123456"
details = await client.get_property_details(property_id)

print(f"Property Type: {details['property_details']['property_type']}")
print(f"Bedrooms: {details['property_details']['bedrooms']}")
print(f"Address: {details['address']['full_address']}")
```

### Valuation

```python
# Get property valuation
address = "456 Chapel Street, South Yarra VIC 3141"
valuation = await client.get_property_valuation(address)

domain_val = valuation['valuations']['domain']
print(f"Estimated Value: ${domain_val['estimated_value']:,.0f}")
print(f"Range: ${domain_val['valuation_range_lower']:,.0f} - ${domain_val['valuation_range_upper']:,.0f}")
print(f"Confidence: {domain_val['confidence']:.2f}")
```

### Market Analytics

```python
# Get market analytics for a location
location = {"suburb": "Paddington", "state": "NSW"}
analytics = await client.get_market_analytics(location, property_type="House")

print(f"Median Price: ${analytics['median_price']:,.0f}")
print(f"12-month Growth: {analytics['price_growth_12_month']:.1f}%")
print(f"Sales Volume: {analytics['sales_volume_12_month']} properties")
```

### Comparable Sales

```python
# Get comparable sales
property_id = "789012"
radius_km = 2.0
comparables = await client.get_comparable_sales(property_id, radius_km)

for comp in comparables['comparable_sales'][:5]:
    print(f"{comp['address']}: ${comp['sale_price']:,.0f} ({comp['sale_date']})")
```

## Error Handling

The client includes comprehensive error handling with custom exceptions:

```python
from app.clients.base.exceptions import (
    PropertyNotFoundError,
    PropertyValuationError, 
    ClientRateLimitError,
    DomainAPIError
)

try:
    valuation = await client.get_property_valuation("Invalid Address")
except PropertyNotFoundError as e:
    print(f"Property not found: {e.address}")
except PropertyValuationError as e:
    print(f"Valuation failed: {e.reason}")
except ClientRateLimitError as e:
    print(f"Rate limited, retry after: {e.retry_after} seconds")
except DomainAPIError as e:
    print(f"Domain API error: {e.message}")
```

## Rate Limiting

The client includes adaptive rate limiting:

```python
# Check rate limit status
status = await client.get_rate_limit_status()
print(f"Requests in window: {status['global']['requests_in_window']}")
print(f"Burst tokens: {status['global']['burst_tokens']}")

# The client automatically handles rate limits with exponential backoff
# No manual intervention required
```

## Caching

Intelligent caching with different TTL values for different data types:

```python
# Cache statistics
stats = await enhanced_client.get_cache_statistics()
print(f"Cache hit rate: {stats['caching']['hit_rate']:.2f}")
print(f"Cache size: {stats['caching']['size_mb']:.1f} MB")

# Warm cache for high-traffic areas
warm_result = await enhanced_client.warm_cache_for_suburb("Sydney", "NSW")
print(f"Cache warming: {warm_result['success']}")

# Invalidate property cache
await enhanced_client.invalidate_property_cache("123 Test Street, Sydney NSW")
```

## Health Monitoring

```python
# Check client health
health = await client.health_check()
print(f"Status: {health['status']}")
print(f"Response time: {health.get('response_time_seconds', 0):.3f}s")

# Check API health
api_health = await client.check_api_health()
print(f"API Status: {api_health['api_status']}")
print(f"Available features: {api_health['features_available']}")
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest app/clients/domain/tests/

# Run specific test file
pytest app/clients/domain/tests/test_client.py -v

# Run with coverage
pytest app/clients/domain/tests/ --cov=app.clients.domain
```

## Performance Tips

1. **Use caching**: Enable caching for production environments to reduce API calls
2. **Batch operations**: Group related requests when possible
3. **Service tier**: Use higher tiers for better rate limits and additional features
4. **Connection pooling**: Configure appropriate pool size for concurrent usage
5. **Cache warming**: Pre-populate cache for high-traffic areas

## Limitations

- Domain API has rate limits that vary by service tier
- Some features (market analytics, demographics) require premium/enterprise tiers
- Historical data availability varies by location and property type
- Address geocoding accuracy depends on data quality

## Support

For issues related to the Domain API client:

1. Check the logs for detailed error messages
2. Verify API key and service tier configuration
3. Review rate limiting and caching settings
4. Consult Domain API documentation for endpoint-specific requirements

## License

This client is part of the Real2.AI platform and follows the same licensing terms.