# CoreLogic API Client for Real2.AI

This module provides a comprehensive CoreLogic API client for Real2.AI's Australian property analysis platform. CoreLogic is a leading provider of professional property valuations, market analytics, and risk assessments in Australia.

## Features

### Core Capabilities
- **Professional Property Valuations**: AVM, Desktop, and Professional valuations
- **Market Analytics**: Suburb-level market trends, forecasting, and demographics
- **Risk Assessment**: Comprehensive property and market risk analysis
- **Investment Analysis**: Yield calculations, ROI metrics, and cash flow analysis
- **Comparable Sales**: Intelligent comparable property analysis
- **Bulk Operations**: Batch processing for multiple properties

### Advanced Features
- **Cost Management**: Budget tracking, alerts, and cost optimization
- **Rate Limiting**: Intelligent rate limiting with hourly and per-second controls
- **Circuit Breaker**: Automatic failure protection and recovery
- **Caching**: Multi-tier caching with cost-aware TTL strategies
- **Data Quality**: Confidence scoring and validation
- **Error Handling**: Comprehensive error recovery and reporting

## Architecture

### Client Hierarchy
```
BaseClient (Abstract)
└── CoreLogicClient (RealEstateAPIOperations)
    ├── Authentication (OAuth2 Client Credentials)
    ├── Rate Limiting (CoreLogicRateLimitManager)
    ├── Caching (CoreLogicCacheManager)
    └── Cost Tracking (Integrated)
```

### Service Tiers
- **Basic**: AVM valuations, basic analytics, comparable sales
- **Professional**: Desktop valuations, market analytics, risk assessment, yield analysis
- **Enterprise**: Professional valuations, bulk operations, custom reports

## Configuration

### Environment Variables
```bash
# Authentication
CORELOGIC_API_KEY=your_api_key
CORELOGIC_CLIENT_ID=your_client_id
CORELOGIC_CLIENT_SECRET=your_client_secret
CORELOGIC_ENVIRONMENT=sandbox  # or production

# Service Configuration
CORELOGIC_SERVICE_TIER=professional
CORELOGIC_DEFAULT_VALUATION_TYPE=avm

# Rate Limiting
CORELOGIC_RATE_LIMIT_RPH=1000
CORELOGIC_REQUESTS_PER_SECOND=0.28
CORELOGIC_CONCURRENT_REQUESTS=5

# Cost Management
CORELOGIC_DAILY_BUDGET=500.0
CORELOGIC_MONTHLY_BUDGET=10000.0
CORELOGIC_AUTO_SUSPEND_ON_BUDGET=true

# Caching
CORELOGIC_ENABLE_CACHING=true
CORELOGIC_CACHE_TTL=86400  # 24 hours
CORELOGIC_MARKET_CACHE_TTL=259200  # 3 days

# Quality Controls
CORELOGIC_MIN_CONFIDENCE_SCORE=0.6
CORELOGIC_REQUIRE_VALUATION_CONFIDENCE=true
```

### Service Configuration
```python
from app.clients.corelogic import CoreLogicClientConfig

config = CoreLogicClientConfig(
    api_key="your_api_key",
    client_id="your_client_id", 
    client_secret="your_client_secret",
    environment="sandbox",
    service_tier="professional",
    
    # Rate limiting
    rate_limit_rph=1000,
    requests_per_second=0.28,
    
    # Cost management
    cost_management={
        "daily_budget_limit": 500.0,
        "monthly_budget_limit": 10000.0,
        "auto_suspend_on_budget_exceeded": True
    }
)
```

## Usage Examples

### Basic Valuation
```python
from app.clients.corelogic import CoreLogicClient, create_corelogic_client_config

async def get_property_valuation():
    config = create_corelogic_client_config()
    
    async with CoreLogicClient(config) as client:
        valuation = await client.get_property_valuation(
            address="123 Collins Street, Melbourne VIC 3000",
            property_details={
                "valuation_type": "avm",
                "property_type": "apartment",
                "bedrooms": 2,
                "bathrooms": 1,
                "building_area": 85
            }
        )
        
        print(f"Valuation: ${valuation['valuation_amount']:,}")
        print(f"Confidence: {valuation['confidence_score']:.2f}")
        return valuation
```

### Market Analytics
```python
async def analyze_market():
    config = create_corelogic_client_config()
    
    async with CoreLogicClient(config) as client:
        market_data = await client.get_market_analytics(
            location={"suburb": "Melbourne", "state": "VIC"},
            property_type="apartment"
        )
        
        metrics = market_data["market_metrics"]
        print(f"Median Price: ${metrics['median_price']:,}")
        print(f"1-Year Growth: {metrics['price_growth_1yr']:.1f}%")
        print(f"Days on Market: {metrics['days_on_market']}")
        
        return market_data
```

### Bulk Valuations
```python
async def bulk_valuations():
    addresses = [
        "123 Smith Street, Collingwood VIC 3066",
        "456 Jones Avenue, Richmond VIC 3121", 
        "789 Brown Road, Hawthorn VIC 3122"
    ]
    
    config = create_corelogic_client_config()
    
    async with CoreLogicClient(config) as client:
        results = await client.bulk_valuation(addresses, "avm")
        
        successful = [r for r in results if r.get("status") == "success"]
        print(f"Successfully valued {len(successful)}/{len(addresses)} properties")
        
        for result in successful:
            print(f"{result['address']}: ${result['valuation_amount']:,}")
        
        return results
```

### Risk Assessment
```python
async def assess_property_risk():
    config = create_corelogic_client_config()
    
    async with CoreLogicClient(config) as client:
        risk_data = await client.get_property_risk_assessment(
            property_id="property_123",
            assessment_type="comprehensive"
        )
        
        print(f"Overall Risk Score: {risk_data['overall_risk_score']:.1f}")
        print(f"Risk Level: {risk_data['risk_level']}")
        
        # Risk factor breakdown
        for factor_type, factor_data in risk_data["risk_factors"].items():
            print(f"{factor_type}: {factor_data.get('score', 'N/A')}")
        
        return risk_data
```

### Investment Analysis
```python
async def analyze_investment():
    config = create_corelogic_client_config()
    
    async with CoreLogicClient(config) as client:
        yield_analysis = await client.calculate_investment_yield(
            property_id="property_123",
            purchase_price=850000,
            rental_income=27040  # $520/week * 52
        )
        
        print(f"Gross Yield: {yield_analysis['gross_yield']:.2f}%")
        print(f"Net Yield: {yield_analysis['net_yield']:.2f}%")
        print(f"Annual Cash Flow: ${yield_analysis['cash_flow']:,}")
        
        return yield_analysis
```

### Cost Management
```python
async def monitor_costs():
    config = create_corelogic_client_config()
    
    async with CoreLogicClient(config) as client:
        # Check current costs
        cost_summary = await client.get_cost_summary()
        
        print(f"Daily Cost: ${cost_summary['daily_cost']:.2f}")
        print(f"Monthly Cost: ${cost_summary['monthly_cost']:.2f}")
        print(f"Budget Utilization: {cost_summary['budget_utilization']['daily_percentage']:.1f}%")
        
        # Check rate limits
        rate_limits = await client.get_rate_limit_status()
        print(f"Hourly Usage: {rate_limits['hourly_requests_used']}/{rate_limits['hourly_requests_limit']}")
        
        return cost_summary
```

## Error Handling

The client provides comprehensive error handling for different failure scenarios:

```python
from app.clients.base.exceptions import (
    PropertyNotFoundError,
    PropertyValuationError, 
    ClientRateLimitError,
    CoreLogicBudgetExceededError
)

async def robust_valuation(address: str):
    try:
        valuation = await client.get_property_valuation(address)
        return valuation
        
    except PropertyNotFoundError as e:
        print(f"Property not found: {e.address}")
        # Handle property not found
        
    except PropertyValuationError as e:
        print(f"Valuation failed: {e.reason}")
        # Handle valuation specific errors
        
    except ClientRateLimitError as e:
        print(f"Rate limited, retry after {e.retry_after}s")
        # Implement backoff strategy
        
    except CoreLogicBudgetExceededError as e:
        print(f"Budget exceeded: {e}")
        # Handle budget limits
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        # Handle other errors
```

## Performance & Optimization

### Caching Strategy
The client implements intelligent caching with cost-aware TTL:

- **Tier 1** (1 hour): Low cost operations (comparable sales, property details)
- **Tier 2** (24 hours): Medium cost operations (AVM valuations, market analytics)
- **Tier 3** (3 days): High cost operations (desktop valuations, risk assessments)
- **Tier 4** (7 days): Very high cost operations (professional valuations, reports)

### Rate Limiting
- **Hourly Limits**: Based on service tier (100-2000 requests/hour)
- **Per-Second Limits**: Conservative throttling (0.28 requests/second default)
- **Circuit Breaker**: Automatic failure protection with exponential backoff

### Cost Optimization
- **Budget Tracking**: Real-time cost monitoring with alerts
- **Operation Costing**: Predictive cost estimation before execution
- **Bulk Discounts**: Automatic batching for bulk operations
- **Cache Utilization**: Aggressive caching of expensive operations

## Integration with Property Profile Service

The CoreLogic client integrates seamlessly with the PropertyProfileService for comprehensive property analysis:

```python
from app.services.property_profile_service import (
    PropertyProfileService,
    PropertyProfileRequest
)

async def comprehensive_analysis():
    service = PropertyProfileService()
    
    request = PropertyProfileRequest(
        address="123 Collins Street, Melbourne VIC 3000",
        valuation_type="desktop",
        include_market_analysis=True,
        include_risk_assessment=True,
        include_investment_metrics=True,
        include_comparable_sales=True
    )
    
    profile = await service.generate_property_profile(request)
    
    return {
        "valuation": profile.valuation_data,
        "market_analysis": profile.market_analysis,
        "risk_assessment": profile.risk_assessment,
        "investment_metrics": profile.investment_metrics,
        "data_quality_score": profile.data_quality_score,
        "total_cost": profile.total_cost
    }
```

## API Reference

### Main Client Methods

#### Property Valuations
- `get_property_valuation(address, property_details)` - Get property valuation
- `bulk_valuation(addresses, valuation_type)` - Bulk property valuations

#### Market Analysis
- `get_market_analytics(location, property_type)` - Market trends and analytics
- `get_suburb_demographics(suburb, state)` - Demographic information

#### Risk & Investment
- `get_property_risk_assessment(property_id, assessment_type)` - Risk analysis
- `calculate_investment_yield(property_id, purchase_price, rental_income)` - Investment metrics

#### Property Data
- `get_property_details(property_id)` - Detailed property information
- `get_comparable_sales(property_id, radius_km)` - Comparable sales analysis
- `get_sales_history(property_id)` - Historical sales data
- `get_rental_history(property_id)` - Historical rental data

#### Utilities
- `check_api_health()` - API status and health check
- `get_rate_limit_status()` - Current rate limiting status
- `get_cost_summary()` - Cost and usage summary

## Testing

### Unit Tests
```bash
pytest app/clients/corelogic/tests/test_client.py -v
```

### Integration Tests
```bash
pytest app/tests/integration/test_property_profile_integration.py -v
```

### Example Usage
```bash
python app/clients/corelogic/example_usage.py
```

## Monitoring & Logging

The client provides comprehensive logging and monitoring:

- **Request/Response Logging**: Detailed API interaction logs
- **Cost Tracking**: Real-time cost monitoring and alerts
- **Performance Metrics**: Response times, success rates, cache hit rates
- **Error Tracking**: Comprehensive error logging with context
- **Circuit Breaker Events**: Automatic failure detection and recovery

## Security Considerations

- **API Key Management**: Secure credential storage and rotation
- **Request Signing**: OAuth2 client credentials flow
- **Data Encryption**: TLS 1.2+ for all API communications
- **Rate Limiting**: Protection against abuse and cost overruns
- **Error Handling**: Secure error messages without sensitive data exposure

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Verify API credentials are correct
   - Check environment configuration
   - Ensure client has proper permissions

2. **Rate Limiting**
   - Monitor rate limit status
   - Implement proper backoff strategies
   - Consider upgrading service tier

3. **Budget Exceeded**
   - Review cost management settings
   - Monitor daily/monthly usage
   - Optimize caching strategies

4. **Low Data Quality**
   - Check confidence score thresholds
   - Verify property address accuracy
   - Review data quality settings

5. **Performance Issues**
   - Enable caching for expensive operations
   - Use bulk operations where possible
   - Monitor connection pool usage

### Debug Mode
```python
import logging
logging.getLogger('app.clients.corelogic').setLevel(logging.DEBUG)
```

## Support

For technical support and API access:
- CoreLogic Developer Portal: https://developer.corelogic.com.au
- Real2.AI Support: support@real2.ai
- Documentation: https://docs.real2.ai/corelogic-integration

## License

This CoreLogic integration is part of the Real2.AI platform and is subject to the terms of service for both Real2.AI and CoreLogic API usage agreements.