"""
Property Profile API endpoints for Real2.AI platform.

This module provides REST API endpoints for comprehensive property analysis
combining Domain and CoreLogic data sources.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends, Query, Body
from pydantic import BaseModel, Field, validator
import logging

from ....services.property_profile_service import (
    get_property_profile_service,
    PropertyProfileRequest,
    PropertyProfileResponse
)
from ....clients.base.exceptions import (
    PropertyNotFoundError,
    PropertyValuationError,
    PropertyDataIncompleteError,
    ClientError,
    ClientRateLimitError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/property-profile", tags=["Property Profile"])


# Request/Response Models

class PropertyProfileRequestModel(BaseModel):
    """Request model for property profile generation."""
    
    address: str = Field(..., description="Property address", min_length=10, max_length=200)
    property_type: Optional[str] = Field(None, description="Property type (house, apartment, townhouse, etc.)")
    valuation_type: str = Field("avm", description="Valuation type (avm, desktop, professional)")
    include_market_analysis: bool = Field(True, description="Include market analysis data")
    include_risk_assessment: bool = Field(True, description="Include risk assessment")
    include_investment_metrics: bool = Field(True, description="Include investment analysis")
    include_comparable_sales: bool = Field(True, description="Include comparable sales data")
    radius_km: float = Field(2.0, description="Radius for comparable sales search (km)", ge=0.5, le=10.0)
    
    @validator("valuation_type")
    def validate_valuation_type(cls, v):
        if v not in ["avm", "desktop", "professional"]:
            raise ValueError("Valuation type must be 'avm', 'desktop', or 'professional'")
        return v
    
    @validator("address")
    def validate_address(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("Address must be at least 10 characters long")
        return v.strip()


class PropertyComparisonRequestModel(BaseModel):
    """Request model for property comparison."""
    
    addresses: List[str] = Field(..., description="List of property addresses to compare", min_items=2, max_items=10)
    comparison_criteria: Optional[List[str]] = Field(
        None, 
        description="Criteria to focus on (valuation, market_performance, risk_assessment, investment_potential)"
    )
    
    @validator("addresses")
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
    
    @validator("comparison_criteria")
    def validate_criteria(cls, v):
        if v is None:
            return v
        
        valid_criteria = ["valuation", "market_performance", "risk_assessment", "investment_potential"]
        for criterion in v:
            if criterion not in valid_criteria:
                raise ValueError(f"Invalid criterion: {criterion}. Must be one of {valid_criteria}")
        
        return v


class PropertyProfileSummaryModel(BaseModel):
    """Summary model for property profile."""
    
    request_id: str
    address: str
    generated_at: str
    data_sources: List[str]
    valuation_amount: Optional[float] = None
    confidence_score: Optional[float] = None
    data_quality_score: float
    total_cost: float
    processing_time_seconds: float


class ErrorResponseModel(BaseModel):
    """Error response model."""
    
    error: str
    error_type: str
    address: Optional[str] = None
    suggestion: Optional[str] = None


# API Endpoints

@router.post(
    "/generate",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Generate comprehensive property profile",
    description="""
    Generate a comprehensive property profile combining data from Domain and CoreLogic.
    
    This endpoint provides:
    - Property valuation using professional-grade CoreLogic data
    - Market analysis and trends
    - Risk assessment and factors
    - Investment metrics and yield analysis
    - Comparable sales analysis
    - Cross-validated data from multiple sources
    
    **Cost Information:**
    - AVM valuations: ~$5 AUD
    - Desktop valuations: ~$10 AUD  
    - Professional valuations: ~$18 AUD
    - Additional analysis adds $2-8 AUD depending on components selected
    """
)
async def generate_property_profile(
    request: PropertyProfileRequestModel,
    service=Depends(get_property_profile_service)
) -> Dict[str, Any]:
    """Generate comprehensive property profile."""
    
    try:
        logger.info(f"Property profile request for: {request.address}")
        
        # Convert to service request
        service_request = PropertyProfileRequest(
            address=request.address,
            property_type=request.property_type,
            valuation_type=request.valuation_type,
            include_market_analysis=request.include_market_analysis,
            include_risk_assessment=request.include_risk_assessment,
            include_investment_metrics=request.include_investment_metrics,
            include_comparable_sales=request.include_comparable_sales,
            radius_km=request.radius_km
        )
        
        # Generate profile
        profile = await service.generate_property_profile(service_request)
        
        # Convert to response format
        response_data = {
            "request_id": profile.request_id,
            "address": profile.address,
            "generated_at": profile.generated_at.isoformat(),
            "data_sources": profile.data_sources,
            "property_details": profile.property_details,
            "valuation_data": profile.valuation_data,
            "data_quality_score": profile.data_quality_score,
            "total_cost": profile.total_cost,
            "processing_time_seconds": profile.processing_time_seconds
        }
        
        # Add optional analysis data
        if profile.market_analysis:
            response_data["market_analysis"] = profile.market_analysis
        
        if profile.risk_assessment:
            response_data["risk_assessment"] = profile.risk_assessment
        
        if profile.investment_metrics:
            response_data["investment_metrics"] = profile.investment_metrics
        
        if profile.comparable_sales:
            response_data["comparable_sales"] = profile.comparable_sales
        
        logger.info(
            f"Property profile completed for {request.address} "
            f"(Quality: {profile.data_quality_score:.2f}, Cost: ${profile.total_cost:.2f})"
        )
        
        return response_data
    
    except PropertyNotFoundError as e:
        logger.warning(f"Property not found: {e.address}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": f"Property not found: {e.address}",
                "error_type": "property_not_found",
                "address": e.address,
                "suggestion": "Please verify the address and try again with a more complete address"
            }
        )
    
    except PropertyValuationError as e:
        logger.error(f"Valuation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": str(e),
                "error_type": "valuation_error",
                "address": e.address,
                "suggestion": "Try using a different valuation type or check property details"
            }
        )
    
    except PropertyDataIncompleteError as e:
        logger.warning(f"Incomplete property data: {e}")
        raise HTTPException(
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            detail={
                "error": str(e),
                "error_type": "incomplete_data",
                "address": e.address,
                "missing_fields": e.missing_fields,
                "suggestion": "Some data may be missing. Profile generated with available data."
            }
        )
    
    except ClientRateLimitError as e:
        logger.warning(f"Rate limit exceeded: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded. Please try again later.",
                "error_type": "rate_limit_exceeded",
                "retry_after": getattr(e, 'retry_after', 60)
            }
        )
    
    except ClientError as e:
        logger.error(f"Client error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "External service temporarily unavailable",
                "error_type": "service_unavailable",
                "suggestion": "Please try again in a few minutes"
            }
        )
    
    except Exception as e:
        logger.error(f"Unexpected error generating property profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error occurred",
                "error_type": "internal_error",
                "suggestion": "Please contact support if this error persists"
            }
        )


@router.post(
    "/compare",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Compare multiple properties",
    description="""
    Compare multiple properties side by side with comprehensive analysis.
    
    This endpoint provides:
    - Side-by-side property comparison
    - Rankings based on different criteria
    - Summary statistics and analysis
    - Investment potential comparison
    - Risk assessment comparison
    
    **Limitations:**
    - Maximum 10 properties per comparison
    - Minimum 2 properties required
    - Cost scales with number of properties and analysis depth
    """
)
async def compare_properties(
    request: PropertyComparisonRequestModel,
    service=Depends(get_property_profile_service)
) -> Dict[str, Any]:
    """Compare multiple properties."""
    
    try:
        logger.info(f"Property comparison request for {len(request.addresses)} properties")
        
        # Generate comparison
        comparison = await service.compare_properties(
            request.addresses,
            request.comparison_criteria
        )
        
        logger.info(
            f"Property comparison completed for {len(request.addresses)} properties "
            f"({comparison.get('properties_compared', 0)} successful)"
        )
        
        return comparison
    
    except PropertyDataIncompleteError as e:
        logger.warning(f"Property comparison failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            detail={
                "error": str(e),
                "error_type": "incomplete_comparison",
                "missing_fields": e.missing_fields,
                "suggestion": "Some properties could not be analyzed. Comparison generated with available data."
            }
        )
    
    except ClientRateLimitError as e:
        logger.warning(f"Rate limit exceeded during comparison: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded during property comparison",
                "error_type": "rate_limit_exceeded",
                "retry_after": getattr(e, 'retry_after', 120),
                "suggestion": "Try comparing fewer properties or wait before retrying"
            }
        )
    
    except Exception as e:
        logger.error(f"Property comparison failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Property comparison failed",
                "error_type": "comparison_error",
                "suggestion": "Please check property addresses and try again"
            }
        )


@router.get(
    "/health",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Check property profile service health",
    description="Check the health and status of property profile services including external APIs."
)
async def check_service_health(
    include_costs: bool = Query(False, description="Include cost and usage information"),
    service=Depends(get_property_profile_service)
) -> Dict[str, Any]:
    """Check service health and status."""
    
    try:
        from ....clients.factory import get_client_factory
        
        factory = get_client_factory()
        health_status = await factory.health_check_all()
        
        response = {
            "service_status": "healthy",
            "timestamp": "2024-08-05T10:00:00Z",  # This would be datetime.now().isoformat()
            "external_services": health_status.get("clients", {}),
            "overall_health": health_status.get("overall_status", "unknown")
        }
        
        if include_costs:
            try:
                # Get cost information from CoreLogic client
                corelogic_client = await get_client_factory().get_client("corelogic")
                if corelogic_client.is_initialized:
                    cost_summary = await corelogic_client.get_cost_summary()
                    response["cost_information"] = cost_summary
            except Exception as e:
                logger.warning(f"Could not retrieve cost information: {e}")
                response["cost_information"] = {"error": "Cost information unavailable"}
        
        return response
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Service health check failed",
                "error_type": "health_check_error"
            }
        )


@router.get(
    "/pricing",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get pricing information",
    description="Get current pricing information for different valuation types and analysis components."
)
async def get_pricing_information() -> Dict[str, Any]:
    """Get pricing information for property profile services."""
    
    return {
        "currency": "AUD",
        "pricing_date": "2024-08-05",
        "valuation_types": {
            "avm": {
                "cost": 5.00,
                "description": "Automated Valuation Model - Fast, cost-effective estimate",
                "accuracy": "±10-15%",
                "turnaround": "< 30 seconds"
            },
            "desktop": {
                "cost": 10.00,
                "description": "Desktop valuation with analyst review",
                "accuracy": "±5-10%",
                "turnaround": "< 2 minutes"
            },
            "professional": {
                "cost": 17.50,
                "description": "Full professional valuation report",
                "accuracy": "±3-5%",
                "turnaround": "< 5 minutes"
            }
        },
        "analysis_components": {
            "market_analysis": {
                "cost": 2.50,
                "description": "Suburb market trends and analytics"
            },
            "risk_assessment": {
                "cost": 7.50,
                "description": "Comprehensive property risk evaluation"
            },
            "investment_metrics": {
                "cost": 4.00,
                "description": "Investment yield and return calculations"
            },
            "comparable_sales": {
                "cost": 1.50,
                "description": "Recent comparable sales analysis"
            }
        },
        "bulk_discounts": {
            "5_10_properties": "5% discount",
            "11_50_properties": "10% discount",
            "51_plus_properties": "15% discount"
        },
        "estimated_total_costs": {
            "basic_profile": "AVM + basic analysis: ~$8-12 AUD",
            "standard_profile": "Desktop + full analysis: ~$20-25 AUD",
            "premium_profile": "Professional + full analysis: ~$30-35 AUD"
        }
    }


# Additional utility endpoints

@router.get(
    "/supported-locations",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get supported locations",
    description="Get information about supported locations and coverage areas."
)
async def get_supported_locations() -> Dict[str, Any]:
    """Get supported locations and coverage information."""
    
    return {
        "coverage": {
            "australia": {
                "states": ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"],
                "major_cities": [
                    "Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", 
                    "Canberra", "Darwin", "Hobart"
                ],
                "coverage_percentage": 95,
                "property_types": [
                    "house", "apartment", "townhouse", "villa", "unit", 
                    "duplex", "terrace", "studio"
                ]
            }
        },
        "data_sources": {
            "domain": {
                "coverage": "Comprehensive Australian coverage",
                "specialties": ["listings", "sales_history", "basic_property_data"]
            },
            "corelogic": {
                "coverage": "Professional Australian property data",
                "specialties": ["valuations", "market_analytics", "risk_assessment", "investment_analysis"]
            }
        },
        "limitations": [
            "Rural and remote properties may have limited data availability",
            "Very new developments may not have sufficient comparable sales",
            "Commercial properties require different valuation approaches"
        ]
    }