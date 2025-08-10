"""
Property-related schema models for Real2.AI platform.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

from app.schema.enums import AustralianState, RiskLevel


class PropertyProfileRequestModel(BaseModel):
    """Request model for property profile generation."""

    address: str = Field(
        ..., description="Property address", min_length=10, max_length=200
    )
    property_type: Optional[str] = Field(
        None, description="Property type (house, apartment, townhouse, etc.)"
    )
    valuation_type: str = Field(
        "avm", description="Valuation type (avm, desktop, professional)"
    )
    include_market_analysis: bool = Field(
        True, description="Include market analysis data"
    )
    include_risk_assessment: bool = Field(True, description="Include risk assessment")
    include_investment_metrics: bool = Field(
        True, description="Include investment analysis"
    )
    include_comparable_sales: bool = Field(
        True, description="Include comparable sales data"
    )
    radius_km: float = Field(
        2.0, description="Radius for comparable sales search (km)", ge=0.5, le=10.0
    )

    @field_validator("valuation_type")
    @classmethod
    def validate_valuation_type(cls, v):
        if v not in ["avm", "desktop", "professional"]:
            raise ValueError(
                "Valuation type must be 'avm', 'desktop', or 'professional'"
            )
        return v

    @field_validator("address")
    @classmethod
    def validate_address(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("Address must be at least 10 characters long")
        return v.strip()


class PropertyComparisonRequestModel(BaseModel):
    """Request model for property comparison."""

    addresses: List[str] = Field(
        ...,
        description="List of property addresses to compare",
        min_length=2,
        max_length=10,
    )
    comparison_criteria: Optional[List[str]] = Field(
        None,
        description="Criteria to focus on (valuation, market_performance, risk_assessment, investment_potential)",
    )

    @field_validator("addresses")
    @classmethod
    def validate_addresses(cls, v):
        if len(v) < 2:
            raise ValueError("At least 2 addresses are required for comparison")
        if len(v) > 10:
            raise ValueError("Maximum 10 addresses allowed for comparison")

        # Validate each address
        for address in v:
            if not address or len(address.strip()) < 10:
                raise ValueError(f"Invalid address: {address}")

        return [addr.strip() for addr in v]

    @field_validator("comparison_criteria")
    @classmethod
    def validate_criteria(cls, v):
        if v is None:
            return v

        valid_criteria = [
            "valuation",
            "market_performance",
            "risk_assessment",
            "investment_potential",
        ]
        for criterion in v:
            if criterion not in valid_criteria:
                raise ValueError(
                    f"Invalid criterion: {criterion}. Must be one of {valid_criteria}"
                )

        return v


class PropertySearchFilters(BaseModel):
    """Advanced property search filters"""

    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_bedrooms: Optional[int] = None
    max_bedrooms: Optional[int] = None
    min_bathrooms: Optional[int] = None
    max_bathrooms: Optional[int] = None
    min_carspaces: Optional[int] = None
    property_types: List[str] = []
    suburbs: List[str] = []
    states: List[AustralianState] = []
    min_land_area: Optional[float] = None
    max_land_area: Optional[float] = None
    features_required: List[str] = []

    @field_validator("property_types")
    @classmethod
    def validate_property_types(cls, v):
        valid_types = ["House", "Unit", "Apartment", "Townhouse", "Villa", "Land"]
        for prop_type in v:
            if prop_type not in valid_types:
                raise ValueError(f"Invalid property type: {prop_type}")
        return v


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
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    map_certainty: Optional[int] = None

    @field_validator("postcode")
    @classmethod
    def validate_postcode(cls, v):
        if not v.isdigit() or len(v) != 4:
            raise ValueError("Postcode must be 4 digits")
        return v


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

    @field_validator("property_type")
    @classmethod
    def validate_property_type(cls, v):
        valid_types = ["House", "Unit", "Townhouse", "Villa", "Land", "Apartment"]
        if v not in valid_types:
            raise ValueError(f"Property type must be one of: {', '.join(valid_types)}")
        return v


class PropertyValuation(BaseModel):
    """Property valuation data"""

    estimated_value: float
    valuation_range_lower: float
    valuation_range_upper: float
    confidence: float
    valuation_date: datetime
    valuation_source: str  # domain, corelogic, combined
    methodology: str
    currency: str = "AUD"


class PropertyMarketData(BaseModel):
    """Property market analytics"""

    median_price: float
    price_growth_12_month: float
    price_growth_3_year: float
    days_on_market: int
    sales_volume_12_month: int
    market_outlook: str
    median_rent: Optional[float] = None
    rental_yield: Optional[float] = None
    vacancy_rate: Optional[float] = None


class PropertyRiskAssessment(BaseModel):
    """Property investment risk assessment"""

    overall_risk: RiskLevel
    liquidity_risk: RiskLevel
    market_risk: RiskLevel
    structural_risk: RiskLevel
    risk_factors: List[str]
    confidence: float
    risk_score: Optional[float] = None  # 0-100 scale


class ComparableSale(BaseModel):
    """Comparable property sale"""

    address: str
    sale_date: datetime
    sale_price: float
    property_details: PropertyDetails
    similarity_score: float
    adjusted_price: Optional[float] = None
    adjustments: Optional[Dict[str, float]] = None


class PropertySalesHistory(BaseModel):
    """Property sales history record"""

    date: datetime
    price: float
    sale_type: str  # Sold, Auction, Private Sale, etc.
    days_on_market: Optional[int] = None


class PropertyRentalHistory(BaseModel):
    """Property rental history record"""

    date: datetime
    weekly_rent: float
    lease_type: str  # Leased, Relisted, etc.
    lease_duration: Optional[str] = None


class PropertyProfile(BaseModel):
    """Comprehensive property profile"""

    address: PropertyAddress
    property_details: PropertyDetails
    valuation: PropertyValuation
    market_data: PropertyMarketData
    risk_assessment: PropertyRiskAssessment
    comparable_sales: List[ComparableSale]
    sales_history: List[PropertySalesHistory]
    rental_history: List[PropertyRentalHistory]
    data_sources: List[str]
    profile_created_at: datetime
    profile_confidence: float
    cache_expires_at: Optional[datetime] = None


class PropertySearchRequest(BaseModel):
    """Property search request"""

    address: Optional[str] = None
    property_details: Optional[PropertyDetails] = None
    include_valuation: bool = True
    include_market_data: bool = True
    include_risk_assessment: bool = True
    include_comparables: bool = True
    include_sales_history: bool = True
    include_rental_history: bool = False
    force_refresh: bool = False
    max_comparables: int = 10

    @field_validator("max_comparables")
    @classmethod
    def validate_max_comparables(cls, v):
        if v < 1 or v > 20:
            raise ValueError("max_comparables must be between 1 and 20")
        return v


class PropertyProfileResponse(BaseModel):
    """Property profile API response"""

    property_profile: PropertyProfile
    processing_time: float
    data_freshness: Dict[str, datetime]
    api_usage: Dict[str, int]
    cached_data: bool = False
    warnings: List[str] = []


class PropertyValuationRequest(BaseModel):
    """Property valuation request"""

    address: str
    property_details: Optional[PropertyDetails] = None
    valuation_source: str = "both"  # domain, corelogic, both

    @field_validator("valuation_source")
    @classmethod
    def validate_valuation_source(cls, v):
        if v not in ["domain", "corelogic", "both"]:
            raise ValueError(
                "valuation_source must be 'domain', 'corelogic', or 'both'"
            )
        return v


class PropertyValuationResponse(BaseModel):
    """Property valuation response"""

    address: str
    valuations: Dict[str, PropertyValuation]  # keyed by source
    processing_time: float
    data_sources_used: List[str]
    confidence_score: float
    warnings: List[str] = []


class PropertyAPIHealthStatus(BaseModel):
    """Property API health status"""

    domain_api: Dict[str, Any]
    corelogic_api: Dict[str, Any]
    overall_status: str
    last_checked: datetime
    rate_limits: Dict[str, Dict[str, Any]]


class PropertyAnalysisDepth(BaseModel):
    """Property analysis depth configuration"""

    include_detailed_financials: bool = False
    include_neighborhood_analysis: bool = False
    include_investment_projections: bool = False
    include_market_comparisons: bool = True
    analysis_radius_km: float = Field(2.0, ge=0.5, le=10.0)


class MarketInsightRequest(BaseModel):
    """Market insight request model"""

    location: str = Field(..., description="Suburb, postcode, or address")
    insight_type: str = Field("comprehensive", description="Type of insight requested")
    time_horizon: str = Field("12_months", description="Time horizon for analysis")

    @field_validator("insight_type")
    @classmethod
    def validate_insight_type(cls, v):
        valid_types = [
            "market_trends",
            "price_forecast",
            "investment_opportunity",
            "comprehensive",
        ]
        if v not in valid_types:
            raise ValueError(f"Insight type must be one of: {valid_types}")
        return v

    @field_validator("time_horizon")
    @classmethod
    def validate_time_horizon(cls, v):
        valid_horizons = ["3_months", "6_months", "12_months", "24_months", "5_years"]
        if v not in valid_horizons:
            raise ValueError(f"Time horizon must be one of: {valid_horizons}")
        return v


class PropertySearchFilter(BaseModel):
    """Property search filter for API requests"""

    listing_type: Optional[str] = None  # Sale, Rent, Sold
    property_types: List[str] = []
    min_bedrooms: Optional[int] = None
    max_bedrooms: Optional[int] = None
    min_bathrooms: Optional[int] = None
    max_bathrooms: Optional[int] = None
    min_carspaces: Optional[int] = None
    max_carspaces: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    locations: List[Dict[str, str]] = []
    surrounding_suburbs: bool = False
    search_mode: Optional[str] = None  # ForSale, ForRent, Sold
    sort_by: Optional[str] = None  # DateUpdated, Price, Bedrooms


class PropertyListing(BaseModel):
    """Property listing information"""

    id: str
    address: PropertyAddress
    property_details: PropertyDetails
    price_details: Dict[str, Any] = {}
    listing_date: Optional[datetime] = None
    agent_info: Optional[Dict[str, Any]] = None
    media_urls: List[str] = []
    description: Optional[str] = None
    auction_date: Optional[datetime] = None
    status: Optional[str] = None
    listing_type: Optional[str] = None


class PropertySearchResponse(BaseModel):
    """Property search response"""

    search_id: str
    query: Optional[str] = None
    total_results: int
    results_returned: int
    search_time_ms: int
    properties: List[PropertyListing]
    facets: Optional[Dict[str, Any]] = None
    market_summary: Optional[Dict[str, Any]] = None
    processing_time: float = 0.0
    page_number: int = 1
    page_size: int = 20


class PropertyInvestmentAnalysis(BaseModel):
    """Property investment analysis data"""

    rental_yield: float = Field(..., description="Annual rental yield percentage")
    capital_growth_forecast_1_year: float = Field(..., description="1-year capital growth forecast percentage")
    capital_growth_forecast_3_year: float = Field(..., description="3-year capital growth forecast percentage")
    capital_growth_forecast_5_year: float = Field(..., description="5-year capital growth forecast percentage")
    cash_flow_monthly: float = Field(..., description="Monthly cash flow (AUD)")
    roi_percentage: float = Field(..., description="Return on investment percentage")
    payback_period_years: float = Field(..., description="Investment payback period in years")
    investment_score: float = Field(..., description="Investment score (0-100)")
    investment_grade: str = Field(..., description="Investment grade (A, B, C, D, F)")
    comparable_roi: float = Field(..., description="Comparable market ROI percentage")


class PropertyMarketTrends(BaseModel):
    """Property market trends data"""

    location: str = Field(..., description="Location (suburb, state)")
    property_type: Optional[str] = Field(None, description="Property type filter")
    time_period: str = Field(..., description="Time period for trends")
    median_price_trend: float = Field(..., description="Median price trend percentage")
    sales_volume_trend: float = Field(..., description="Sales volume trend percentage")
    days_on_market_trend: float = Field(..., description="Days on market trend")
    price_per_sqm_trend: Optional[float] = Field(None, description="Price per square meter trend")
    rental_yield_trend: Optional[float] = Field(None, description="Rental yield trend")
    market_momentum: str = Field(..., description="Market momentum (strong_growth, moderate_growth, stable, declining)")
    forecast_confidence: float = Field(..., description="Forecast confidence score (0-1)")
    data_points: int = Field(..., description="Number of data points used")
    trend_start_date: datetime = Field(..., description="Start date for trend analysis")
    trend_end_date: datetime = Field(..., description="End date for trend analysis")


class PropertyMarketInsight(BaseModel):
    """Property market intelligence insights"""

    insight_type: str = Field(..., description="Type of insight (trend, forecast, opportunity)")
    title: str = Field(..., description="Insight title")
    description: str = Field(..., description="Detailed insight description")
    location: str = Field(..., description="Location for the insight")
    property_type: Optional[str] = Field(None, description="Property type (if applicable)")
    impact_score: float = Field(..., description="Impact score (0-100)")
    confidence_level: float = Field(..., description="Confidence level (0-1)")
    time_horizon: str = Field(..., description="Time horizon for the insight")
    supporting_data: Dict[str, Any] = Field(default_factory=dict, description="Supporting data points")
    actionable_recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")
    created_at: datetime = Field(default_factory=datetime.now, description="When the insight was generated")
    expires_at: Optional[datetime] = Field(None, description="When the insight expires")


class PropertyDataValidationResult(BaseModel):
    """Property data validation result"""

    is_valid: bool
    validation_errors: List[str] = []
    validation_warnings: List[str] = []
    data_quality_score: float = 0.0
    missing_fields: List[str] = []
    confidence_score: float = 0.0
    validation_timestamp: datetime = Field(default_factory=datetime.now)
