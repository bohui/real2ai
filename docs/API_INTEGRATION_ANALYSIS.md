# Australian Property API Integration Analysis
## Domain API & CoreLogic API Technical Documentation

### Executive Summary

This document provides comprehensive technical analysis for integrating Domain API and CoreLogic API into the Real2.AI platform's property profile service. Both APIs offer complementary data sources for Australian real estate, enabling comprehensive property analysis to enhance contract validation and risk assessment.

## 1. Domain API Technical Specification

### 1.1 Core Capabilities
- **Property Search**: Comprehensive property listings across Australia
- **Property Details**: Detailed property information including history, features, and market data
- **Sales History**: Historical transaction data and price trends
- **Suburb Insights**: Market analytics and demographic information
- **Agent Information**: Real estate agent details and performance metrics

### 1.2 API Endpoints

#### Property Search Endpoint
```
GET /v1/listings/residential/_search
```

**Request Schema:**
```json
{
  "listingType": "Sale|Rent",
  "propertyTypes": ["House", "Unit", "Townhouse", "Villa", "Land"],
  "minBedrooms": 1,
  "maxBedrooms": 10,
  "minBathrooms": 1,
  "maxBathrooms": 10,
  "minCarspaces": 0,
  "maxCarspaces": 10,
  "minPrice": 100000,
  "maxPrice": 5000000,
  "locations": [
    {
      "state": "NSW|VIC|QLD|WA|SA|TAS|ACT|NT",
      "region": "string",
      "area": "string",
      "suburb": "string",
      "postcode": "string"
    }
  ],
  "surroundingSuburbs": true,
  "searchMode": "ForSale|ForRent|Sold",
  "pageNumber": 1,
  "pageSize": 20,
  "sortBy": "DateUpdated|Price|Bedrooms"
}
```

**Response Schema:**
```json
{
  "totalResultsCount": 150,
  "resultsReturned": 20,
  "listings": [
    {
      "id": 123456789,
      "advertiserId": 12345,
      "priceDetails": {
        "displayPrice": "$850,000",
        "price": 850000,
        "priceFrom": 800000,
        "priceTo": 900000
      },
      "media": [
        {
          "category": "Image",
          "url": "https://bucket-api.domain.com.au/v1/image.jpg"
        }
      ],
      "propertyDetails": {
        "state": "NSW",
        "features": ["AirConditioning", "BuiltInWardrobes", "Dishwasher"],
        "propertyType": "House",
        "allPropertyTypes": ["House"],
        "bedrooms": 3,
        "bathrooms": 2,
        "carspaces": 2,
        "unitNumber": "",
        "streetNumber": "123",
        "street": "Main Street",
        "area": "Sydney",
        "region": "Sydney Region",
        "suburb": "Parramatta",
        "postcode": "2150",
        "displayableAddress": "123 Main Street, Parramatta NSW 2150",
        "latitude": -33.8688,
        "longitude": 151.2093,
        "mapCertainty": 9,
        "landArea": 650,
        "buildingArea": 180
      },
      "headline": "Stunning Family Home in Prime Location",
      "summaryDescription": "Beautiful 3 bedroom home...",
      "hasFloorplan": true,
      "hasVideo": false,
      "labels": ["New"],
      "auctionSchedule": {
        "time": "2024-08-15T14:00:00.000Z",
        "auctioneerName": "John Smith Auctions"
      },
      "dateListed": "2024-07-15T09:00:00.000Z",
      "dateUpdated": "2024-08-01T10:30:00.000Z"
    }
  ]
}
```

#### Property Details Endpoint
```
GET /v1/properties/{propertyId}
```

**Response Schema:**
```json
{
  "id": 123456789,
  "propertyDetails": {
    "displayableAddress": "123 Main Street, Parramatta NSW 2150",
    "propertyType": "House",
    "bedrooms": 3,
    "bathrooms": 2,
    "carspaces": 2,
    "landArea": 650,
    "buildingArea": 180,
    "yearBuilt": 1995,
    "features": ["AirConditioning", "BuiltInWardrobes", "Dishwasher"]
  },
  "salesHistory": [
    {
      "date": "2024-03-15",
      "price": 850000,
      "type": "Sold"
    },
    {
      "date": "2019-05-20",
      "price": 720000,
      "type": "Sold"
    }
  ],
  "rentalHistory": [
    {
      "date": "2023-01-01",
      "price": 650,
      "type": "Leased"
    }
  ],
  "demographics": {
    "medianHousePrice": 945000,
    "medianUnitPrice": 675000,
    "medianRentHouse": 680,
    "medianRentUnit": 520
  }
}
```

### 1.3 Authentication & Rate Limits

**Authentication:**
```http
Authorization: Bearer {API_KEY}
X-API-Call-Source: {APPLICATION_NAME}
```

**Rate Limits:**
- Standard Tier: 500 requests/hour
- Premium Tier: 2000 requests/hour
- Enterprise Tier: 10000 requests/hour

**Error Handling:**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "API rate limit exceeded",
    "details": {
      "limit": 500,
      "remaining": 0,
      "resetTime": "2024-08-05T15:00:00.000Z"
    }
  }
}
```

## 2. CoreLogic API Technical Specification

### 2.1 Core Capabilities
- **Property Valuations**: Automated Valuation Models (AVM) and professional valuations
- **Market Analytics**: Comprehensive market trends and forecasting
- **Risk Assessment**: Property investment risk analysis
- **Comparable Sales**: Detailed comparative market analysis
- **Property Reports**: Comprehensive property investment reports

### 2.2 API Endpoints

#### Property Valuation Endpoint
```
POST /v1/property/valuation
```

**Request Schema:**
```json
{
  "address": {
    "unitNumber": "12",
    "streetNumber": "123",
    "streetName": "Main Street",
    "streetType": "Street",
    "suburb": "Parramatta",
    "state": "NSW",
    "postcode": "2150"
  },
  "propertyType": "House|Unit|Townhouse|Villa|Land",
  "bedrooms": 3,
  "bathrooms": 2,
  "carspaces": 2,
  "landArea": 650,
  "yearBuilt": 1995,
  "valuationType": "AVM|Professional|Comparative"
}
```

**Response Schema:**
```json
{
  "propertyId": "CL123456789",
  "valuation": {
    "estimatedValue": 875000,
    "valuationRange": {
      "lower": 825000,
      "upper": 925000
    },
    "confidence": 85,
    "valuationDate": "2024-08-05T00:00:00.000Z",
    "valuationType": "AVM",
    "methodology": "Automated Valuation Model using recent sales data"
  },
  "marketMetrics": {
    "medianPrice": 890000,
    "priceGrowth12Month": 5.2,
    "priceGrowth3Year": 15.8,
    "daysOnMarket": 32,
    "saleVolume12Month": 145
  },
  "riskAssessment": {
    "overallRisk": "Low",
    "liquidityRisk": "Low",
    "marketRisk": "Medium",
    "structuralRisk": "Low",
    "riskFactors": [
      "Stable market conditions",
      "High demand area",
      "Good transport links"
    ]
  }
}
```

#### Market Analytics Endpoint
```
GET /v1/market/analytics
```

**Request Parameters:**
```
suburb=Parramatta&state=NSW&propertyType=House&period=12months
```

**Response Schema:**
```json
{
  "location": {
    "suburb": "Parramatta",
    "state": "NSW",
    "postcode": "2150"
  },
  "marketTrends": {
    "medianPrice": 890000,
    "priceChange": {
      "quarterly": 2.1,
      "annually": 5.2,
      "3year": 15.8
    },
    "salesVolume": {
      "quarterly": 42,
      "annually": 145,
      "previousYear": 138
    },
    "daysOnMarket": {
      "current": 32,
      "previousQuarter": 28,
      "previousYear": 35
    }
  },
  "forecast": {
    "priceGrowthNext12Months": 3.5,
    "confidenceLevel": 78,
    "marketOutlook": "Stable Growth"
  },
  "demographics": {
    "populationGrowth": 1.8,
    "medianAge": 34,
    "medianHouseholdIncome": 95000,
    "unemploymentRate": 4.2
  }
}
```

#### Comparable Sales Endpoint
```
GET /v1/property/comparables/{propertyId}
```

**Response Schema:**
```json
{
  "subjectProperty": {
    "address": "123 Main Street, Parramatta NSW 2150",
    "propertyType": "House",
    "bedrooms": 3,
    "bathrooms": 2,
    "landArea": 650
  },
  "comparables": [
    {
      "address": "125 Main Street, Parramatta NSW 2150",
      "saleDate": "2024-06-15",
      "salePrice": 860000,
      "bedrooms": 3,
      "bathrooms": 2,
      "landArea": 630,
      "similarity": 92,
      "adjustments": {
        "landSizeAdjustment": -5000,
        "conditionAdjustment": 10000,
        "adjustedPrice": 865000
      }
    }
  ],
  "analysis": {
    "averageComparablePrice": 865000,
    "pricePerSqm": 4806,
    "recommendedValueRange": {
      "lower": 845000,
      "upper": 885000
    }
  }
}
```

### 2.3 Authentication & Rate Limits

**Authentication:**
```http
Authorization: Bearer {API_KEY}
X-Client-ID: {CLIENT_ID}
Content-Type: application/json
```

**Rate Limits:**
- Standard Tier: 100 requests/hour
- Professional Tier: 500 requests/hour
- Enterprise Tier: 2000 requests/hour

## 3. Integration Architecture Design

### 3.1 Recommended Service Architecture

```python
# /backend/app/services/property_profile_service.py

class PropertyProfileService:
    """
    Unified property profile service integrating Domain API and CoreLogic API
    """
    
    def __init__(self):
        self.domain_client = DomainAPIClient()
        self.corelogic_client = CoreLogicAPIClient()
        self.cache_service = PropertyCacheService()
    
    async def get_comprehensive_property_profile(
        self, 
        address: str, 
        property_details: Optional[Dict] = None
    ) -> PropertyProfile:
        """
        Generate comprehensive property profile using both APIs
        """
        # Search property in Domain API
        domain_data = await self.domain_client.search_property(address)
        
        # Get valuation from CoreLogic
        corelogic_data = await self.corelogic_client.get_valuation(
            address, property_details
        )
        
        # Merge and validate data
        return self._merge_property_data(domain_data, corelogic_data)
```

### 3.2 Data Models for Integration

```python
# Add to /backend/app/api/models.py

class PropertyAddress(BaseModel):
    """Australian property address"""
    unit_number: Optional[str] = None
    street_number: str
    street_name: str
    street_type: str
    suburb: str
    state: AustralianState
    postcode: str
    full_address: Optional[str] = None

class PropertyDetails(BaseModel):
    """Property physical details"""
    property_type: str  # House, Unit, Townhouse, Villa, Land
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    carspaces: Optional[int] = None
    land_area: Optional[float] = None
    building_area: Optional[float] = None
    year_built: Optional[int] = None
    features: List[str] = []

class PropertyValuation(BaseModel):
    """Property valuation data"""
    estimated_value: float
    valuation_range_lower: float
    valuation_range_upper: float
    confidence: float
    valuation_date: datetime
    valuation_source: str  # domain, corelogic
    methodology: str

class PropertyMarketData(BaseModel):
    """Property market analytics"""
    median_price: float
    price_growth_12_month: float
    price_growth_3_year: float
    days_on_market: int
    sales_volume_12_month: int
    market_outlook: str

class PropertyRiskAssessment(BaseModel):
    """Property investment risk assessment"""
    overall_risk: RiskLevel
    liquidity_risk: RiskLevel
    market_risk: RiskLevel
    structural_risk: RiskLevel
    risk_factors: List[str]
    confidence: float

class ComparableSale(BaseModel):
    """Comparable property sale"""
    address: str
    sale_date: datetime
    sale_price: float
    property_details: PropertyDetails
    similarity_score: float
    adjusted_price: Optional[float] = None

class PropertyProfile(BaseModel):
    """Comprehensive property profile"""
    address: PropertyAddress
    property_details: PropertyDetails
    valuation: PropertyValuation
    market_data: PropertyMarketData
    risk_assessment: PropertyRiskAssessment
    comparable_sales: List[ComparableSale]
    sales_history: List[Dict[str, Any]]
    rental_history: List[Dict[str, Any]]
    data_sources: List[str]
    profile_created_at: datetime
    profile_confidence: float

class PropertySearchRequest(BaseModel):
    """Property search request"""
    address: Optional[str] = None
    property_details: Optional[PropertyDetails] = None
    include_valuation: bool = True
    include_market_data: bool = True
    include_risk_assessment: bool = True
    include_comparables: bool = True
    force_refresh: bool = False

class PropertyProfileResponse(BaseModel):
    """Property profile API response"""
    property_profile: PropertyProfile
    processing_time: float
    data_freshness: Dict[str, datetime]
    api_usage: Dict[str, int]
```

### 3.3 API Client Implementation

```python
# /backend/app/clients/domain_api_client.py

class DomainAPIClient:
    """Domain API client with rate limiting and caching"""
    
    def __init__(self):
        self.api_key = settings.DOMAIN_API_KEY
        self.base_url = "https://api.domain.com.au"
        self.rate_limiter = RateLimiter(500, 3600)  # 500 requests per hour
        self.session = aiohttp.ClientSession()
    
    async def search_property(self, address: str) -> Dict[str, Any]:
        """Search for property by address"""
        await self.rate_limiter.acquire()
        
        search_params = {
            "locations": [{"area": self._extract_area(address)}],
            "pageSize": 1,
            "searchMode": "ForSale"
        }
        
        async with self.session.post(
            f"{self.base_url}/v1/listings/residential/_search",
            json=search_params,
            headers=self._get_headers()
        ) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 429:
                raise RateLimitExceededError("Domain API rate limit exceeded")
            else:
                raise DomainAPIError(f"API error: {response.status}")
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Call-Source": "Real2AI-Platform",
            "Content-Type": "application/json"
        }

# /backend/app/clients/corelogic_api_client.py

class CoreLogicAPIClient:
    """CoreLogic API client with enterprise features"""
    
    def __init__(self):
        self.api_key = settings.CORELOGIC_API_KEY
        self.base_url = "https://api.corelogic.com.au"
        self.rate_limiter = RateLimiter(100, 3600)  # 100 requests per hour
        self.session = aiohttp.ClientSession()
    
    async def get_valuation(
        self, 
        address: str, 
        property_details: PropertyDetails
    ) -> Dict[str, Any]:
        """Get property valuation"""
        await self.rate_limiter.acquire()
        
        valuation_request = {
            "address": self._format_address(address),
            "propertyType": property_details.property_type,
            "bedrooms": property_details.bedrooms,
            "bathrooms": property_details.bathrooms,
            "carspaces": property_details.carspaces,
            "landArea": property_details.land_area,
            "valuationType": "AVM"
        }
        
        async with self.session.post(
            f"{self.base_url}/v1/property/valuation",
            json=valuation_request,
            headers=self._get_headers()
        ) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 429:
                raise RateLimitExceededError("CoreLogic API rate limit exceeded")
            else:
                raise CoreLogicAPIError(f"API error: {response.status}")
```

## 4. Complementary Data Analysis

### 4.1 Unique Data Sources

**Domain API Strengths:**
- Real-time listing data and market activity
- Agent information and contact details  
- Property photos and marketing materials
- Auction schedules and results
- Rental listings and vacancy rates

**CoreLogic API Strengths:**
- Professional property valuations (AVM & expert)
- Comprehensive risk assessment models
- Market forecasting and trend analysis  
- Investment yield calculations
- Detailed comparable sales analysis

### 4.2 Data Validation Strategy

```python
class PropertyDataValidator:
    """Validate and cross-reference data from multiple sources"""
    
    def validate_property_profile(
        self, 
        domain_data: Dict, 
        corelogic_data: Dict
    ) -> ValidationResult:
        """Cross-validate property data from both sources"""
        
        validations = []
        
        # Price validation
        domain_price = domain_data.get('priceDetails', {}).get('price')
        corelogic_value = corelogic_data.get('valuation', {}).get('estimatedValue')
        
        if domain_price and corelogic_value:
            price_variance = abs(domain_price - corelogic_value) / domain_price
            if price_variance > 0.2:  # 20% variance threshold
                validations.append({
                    'type': 'price_variance',
                    'severity': 'warning',
                    'message': f'Price variance {price_variance:.1%} between sources'
                })
        
        # Address validation
        domain_address = self._normalize_address(domain_data.get('propertyDetails', {}).get('displayableAddress'))
        corelogic_address = self._normalize_address(corelogic_data.get('address'))
        
        if domain_address and corelogic_address:
            if domain_address != corelogic_address:
                validations.append({
                    'type': 'address_mismatch',
                    'severity': 'error',
                    'message': 'Address mismatch between data sources'
                })
        
        return ValidationResult(validations=validations)
```

## 5. Error Handling & Recovery

### 5.1 Resilience Patterns

```python
class PropertyAPIOrchestrator:
    """Orchestrate API calls with fallback strategies"""
    
    async def get_property_data_with_fallback(
        self, 
        address: str
    ) -> PropertyProfile:
        """Get property data with intelligent fallback"""
        
        errors = []
        
        try:
            # Primary: Try both APIs in parallel
            domain_task = asyncio.create_task(
                self.domain_client.search_property(address)
            )
            corelogic_task = asyncio.create_task(
                self.corelogic_client.get_valuation(address, {})
            )
            
            domain_data, corelogic_data = await asyncio.gather(
                domain_task, corelogic_task, return_exceptions=True
            )
            
            # Handle partial failures
            if isinstance(domain_data, Exception):
                errors.append(f"Domain API error: {domain_data}")
                domain_data = None
            
            if isinstance(corelogic_data, Exception):
                errors.append(f"CoreLogic API error: {corelogic_data}")
                corelogic_data = None
            
            # Return partial data if at least one source succeeded
            if domain_data or corelogic_data:
                return self._merge_partial_data(domain_data, corelogic_data, errors)
            
            # Fallback to cached data
            cached_data = await self.cache_service.get_cached_property(address)
            if cached_data:
                return cached_data.with_warnings(['Using cached data due to API failures'] + errors)
            
            raise PropertyDataUnavailableError("All data sources failed", errors)
            
        except Exception as e:
            logger.error(f"Property data retrieval failed: {e}", extra={'address': address})
            raise
```

### 5.2 Rate Limiting Strategy

```python
class AdaptiveRateLimiter:
    """Adaptive rate limiter with priority queuing"""
    
    def __init__(self, requests_per_hour: int):
        self.requests_per_hour = requests_per_hour
        self.request_queue = asyncio.Queue()
        self.request_times = deque()
        self.priority_queue = asyncio.PriorityQueue()
    
    async def acquire(self, priority: int = 5) -> None:
        """Acquire rate limit token with priority"""
        
        # High priority requests (1-3) bypass normal queue
        if priority <= 3:
            await self.priority_queue.put((priority, asyncio.create_task(self._wait_for_slot())))
            _, task = await self.priority_queue.get()
            await task
        else:
            await self._wait_for_slot()
    
    async def _wait_for_slot(self) -> None:
        """Wait for available rate limit slot"""
        now = time.time()
        
        # Remove requests older than 1 hour
        while self.request_times and now - self.request_times[0] > 3600:
            self.request_times.popleft()
        
        # Wait if we're at the limit
        if len(self.request_times) >= self.requests_per_hour:
            sleep_time = 3600 - (now - self.request_times[0])
            await asyncio.sleep(max(0, sleep_time))
        
        self.request_times.append(now)
```

## 6. Caching & Performance Optimization

### 6.1 Multi-Level Caching Strategy

```python
class PropertyCacheService:
    """Multi-level caching for property data"""
    
    def __init__(self):
        self.redis_client = redis.asyncio.from_url(settings.REDIS_URL)
        self.memory_cache = TTLCache(maxsize=1000, ttl=300)  # 5 min memory cache
    
    async def get_cached_property(self, address: str) -> Optional[PropertyProfile]:
        """Get cached property data with fallback layers"""
        
        cache_key = f"property:{self._normalize_address(address)}"
        
        # Level 1: Memory cache (fastest)
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]
        
        # Level 2: Redis cache
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            property_profile = PropertyProfile.parse_raw(cached_data)
            # Populate memory cache
            self.memory_cache[cache_key] = property_profile
            return property_profile
        
        return None
    
    async def cache_property(
        self, 
        address: str, 
        property_profile: PropertyProfile,
        ttl: int = 3600  # 1 hour default
    ) -> None:
        """Cache property data with appropriate TTL"""
        
        cache_key = f"property:{self._normalize_address(address)}"
        
        # Cache in both levels
        self.memory_cache[cache_key] = property_profile
        await self.redis_client.setex(
            cache_key, 
            ttl, 
            property_profile.json()
        )
```

## 7. Integration Endpoints

### 7.1 REST API Endpoints

```python
# /backend/app/api/routes/property.py

@router.post("/property/profile", response_model=PropertyProfileResponse)
async def get_property_profile(
    request: PropertySearchRequest,
    current_user: User = Depends(get_current_user)
) -> PropertyProfileResponse:
    """Get comprehensive property profile"""
    
    start_time = time.time()
    
    try:
        property_service = PropertyProfileService()
        
        property_profile = await property_service.get_comprehensive_property_profile(
            address=request.address,
            property_details=request.property_details,
            options={
                'include_valuation': request.include_valuation,
                'include_market_data': request.include_market_data,
                'include_risk_assessment': request.include_risk_assessment,
                'include_comparables': request.include_comparables,
                'force_refresh': request.force_refresh
            }
        )
        
        processing_time = time.time() - start_time
        
        # Track usage
        await track_api_usage(current_user.id, "property_profile", processing_time)
        
        return PropertyProfileResponse(
            property_profile=property_profile,
            processing_time=processing_time,
            data_freshness=property_profile.get_data_freshness(),
            api_usage=property_profile.get_api_usage_stats()
        )
        
    except PropertyDataUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Property data temporarily unavailable",
                "details": str(e),
                "retry_after": 300
            }
        )
    except RateLimitExceededError as e:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "API rate limit exceeded",
                "details": str(e),
                "retry_after": 3600
            }
        )

@router.get("/property/valuation/{address}")
async def get_property_valuation(
    address: str,
    source: Optional[str] = Query(None, enum=["domain", "corelogic", "both"]),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get property valuation from specified source(s)"""
    
    valuation_service = PropertyValuationService()
    
    if source == "domain":
        return await valuation_service.get_domain_valuation(address)
    elif source == "corelogic":
        return await valuation_service.get_corelogic_valuation(address)
    else:  # both or None
        return await valuation_service.get_combined_valuation(address)
```

## 8. Monitoring & Analytics

### 8.1 API Performance Monitoring

```python
class PropertyAPIMonitor:
    """Monitor API performance and costs"""
    
    def __init__(self):
        self.metrics_client = MetricsClient()
    
    async def track_api_call(
        self, 
        api_name: str, 
        endpoint: str, 
        response_time: float,
        status_code: int,
        cost: Optional[float] = None
    ) -> None:
        """Track API call metrics"""
        
        await self.metrics_client.increment_counter(
            f"property_api.{api_name}.calls_total",
            tags={
                'endpoint': endpoint,
                'status': str(status_code)
            }
        )
        
        await self.metrics_client.record_histogram(
            f"property_api.{api_name}.response_time",
            response_time,
            tags={'endpoint': endpoint}
        )
        
        if cost:
            await self.metrics_client.record_histogram(
                f"property_api.{api_name}.cost_usd",
                cost,
                tags={'endpoint': endpoint}
            )
    
    async def get_api_health_status(self) -> Dict[str, Any]:
        """Get API health and performance status"""
        
        return {
            'domain_api': {
                'status': await self._check_api_health('domain'),
                'avg_response_time': await self._get_avg_response_time('domain'),
                'success_rate': await self._get_success_rate('domain'),
                'rate_limit_remaining': await self._get_rate_limit_remaining('domain')
            },
            'corelogic_api': {
                'status': await self._check_api_health('corelogic'),
                'avg_response_time': await self._get_avg_response_time('corelogic'),
                'success_rate': await self._get_success_rate('corelogic'),
                'rate_limit_remaining': await self._get_rate_limit_remaining('corelogic')
            }
        }
```

## 9. Cost Optimization Recommendations

### 9.1 Smart Caching Strategy
- Cache property profiles for 1 hour (pricing data)
- Cache market analytics for 24 hours (less volatile)
- Cache demographics data for 7 days (rarely changes)
- Implement cache warming for high-traffic areas

### 9.2 Request Optimization
- Batch property lookups when possible
- Use property IDs instead of addresses for subsequent calls
- Implement request deduplication for concurrent requests
- Prioritize critical data (valuations) over nice-to-have (demographics)

### 9.3 Fallback Strategies
- Use cached data when APIs are unavailable
- Implement graceful degradation (show partial data)
- Provide confidence indicators for data freshness
- Allow manual refresh for critical decisions

## 10. Security Considerations

### 10.1 API Key Management
```python
# Secure API key rotation
class APIKeyManager:
    """Manage API keys with rotation and encryption"""
    
    def __init__(self):
        self.key_rotation_interval = 2592000  # 30 days
        self.encryption_key = Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
    
    async def get_active_api_key(self, service: str) -> str:
        """Get currently active API key for service"""
        encrypted_key = await self.redis_client.get(f"api_key:{service}:active")
        return self.cipher.decrypt(encrypted_key).decode()
    
    async def rotate_api_key(self, service: str, new_key: str) -> None:
        """Rotate API key with zero downtime"""
        encrypted_key = self.cipher.encrypt(new_key.encode())
        
        # Store new key as pending
        await self.redis_client.setex(
            f"api_key:{service}:pending", 
            300, 
            encrypted_key
        )
        
        # Test new key
        if await self._test_api_key(service, new_key):
            # Promote to active
            await self.redis_client.rename(
                f"api_key:{service}:pending",
                f"api_key:{service}:active"
            )
            logger.info(f"API key rotated successfully for {service}")
        else:
            await self.redis_client.delete(f"api_key:{service}:pending")
            raise APIKeyRotationError(f"New API key failed validation for {service}")
```

### 10.2 Data Privacy
- Encrypt property addresses in logs
- Implement data retention policies (delete after 90 days)
- Anonymize user queries for analytics
- Comply with Australian Privacy Principles (APPs)

## 11. Testing Strategy

### 11.1 API Integration Tests
```python
# /backend/tests/integration/test_property_apis.py

class TestPropertyAPIIntegration:
    """Integration tests for property APIs"""
    
    @pytest.mark.asyncio
    async def test_domain_api_property_search(self):
        """Test Domain API property search functionality"""
        client = DomainAPIClient()
        
        result = await client.search_property("123 Main Street, Parramatta NSW 2150")
        
        assert result is not None
        assert 'listings' in result
        assert len(result['listings']) > 0
    
    @pytest.mark.asyncio
    async def test_corelogic_valuation(self):
        """Test CoreLogic valuation API"""
        client = CoreLogicAPIClient()
        
        property_details = PropertyDetails(
            property_type="House",
            bedrooms=3,
            bathrooms=2,
            land_area=650
        )
        
        result = await client.get_valuation(
            "123 Main Street, Parramatta NSW 2150",
            property_details
        )
        
        assert result is not None
        assert 'valuation' in result
        assert result['valuation']['estimatedValue'] > 0
    
    @pytest.mark.asyncio
    async def test_property_profile_integration(self):
        """Test complete property profile generation"""
        service = PropertyProfileService()
        
        profile = await service.get_comprehensive_property_profile(
            "123 Main Street, Parramatta NSW 2150"
        )
        
        assert profile.valuation.estimated_value > 0
        assert profile.market_data.median_price > 0
        assert profile.risk_assessment.overall_risk in ['Low', 'Medium', 'High']
        assert len(profile.comparable_sales) > 0
```

## Conclusion

This integration strategy provides a robust foundation for incorporating Australian property data into the Real2.AI platform. The combined Domain API and CoreLogic API integration offers:

1. **Comprehensive Data Coverage**: Real-time listings + professional valuations
2. **Risk Mitigation**: Cross-validation and fallback strategies
3. **Performance Optimization**: Multi-level caching and rate limiting
4. **Cost Management**: Smart caching and request optimization
5. **Scalability**: Async architecture with monitoring

The implementation follows the existing Real2.AI patterns and integrates seamlessly with the current contract analysis workflow, enhancing the platform's ability to provide comprehensive property risk assessment for Australian real estate contracts.