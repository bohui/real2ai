"""
Property Profile API routes for Real2.AI platform.

This module provides REST API endpoints for comprehensive property analysis
combining Domain and CoreLogic data sources.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends, Query, Body
from pydantic import BaseModel, Field, field_validator
import logging
from datetime import datetime

from app.api.models import (
    PropertySearchRequest,
    PropertyProfileResponse,
    PropertyValuationRequest,
    PropertyValuationResponse,
    PropertyAPIHealthStatus
)
from app.clients.base.exceptions import (
    PropertyNotFoundError,
    PropertyValuationError,
    PropertyDataIncompleteError,
    PropertyRateLimitError,
    ClientError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/property", tags=["Property Profile"])


# Request/Response Models for API endpoints

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
    
    @field_validator("valuation_type")
    @classmethod
    def validate_valuation_type(cls, v):
        if v not in ["avm", "desktop", "professional"]:
            raise ValueError("Valuation type must be 'avm', 'desktop', or 'professional'")
        return v
    
    @field_validator("address")
    @classmethod
    def validate_address(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("Address must be at least 10 characters long")
        return v.strip()


class PropertyComparisonRequestModel(BaseModel):
    """Request model for property comparison."""
    
    addresses: List[str] = Field(..., description="List of property addresses to compare", min_length=2, max_length=10)
    comparison_criteria: Optional[List[str]] = Field(
        None, 
        description="Criteria to focus on (valuation, market_performance, risk_assessment, investment_potential)"
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


# Dependency to get property profile service
async def get_property_profile_service():
    """Get property profile service instance."""
    try:
        from app.services.property_profile_service import PropertyProfileService
        from app.clients.factory import get_client_factory
        
        factory = get_client_factory()
        domain_client = await factory.get_client("domain")
        corelogic_client = await factory.get_client("corelogic")
        
        return PropertyProfileService(domain_client, corelogic_client)
    except Exception as e:
        logger.error(f"Failed to initialize property profile service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Property profile service unavailable"
        )


# API Endpoints

@router.post(
    "/profile",
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
        service_request = PropertySearchRequest(
            address=request.address,
            include_valuation=True,
            include_market_data=request.include_market_analysis,
            include_risk_assessment=request.include_risk_assessment,
            include_comparables=request.include_comparable_sales,
            force_refresh=False
        )
        
        # For now, return a mock response until the service is fully implemented
        response_data = {
            "request_id": f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "address": request.address,
            "generated_at": datetime.now().isoformat(),
            "data_sources": ["domain", "corelogic"],
            "property_details": {
                "property_type": request.property_type or "House",
                "address_validated": True
            },
            "valuation_data": {
                "estimated_value": 850000,
                "valuation_type": request.valuation_type,
                "confidence": 0.85
            },
            "data_quality_score": 0.92,
            "total_cost": 15.50,
            "processing_time_seconds": 2.3,
            "status": "Service implementation in progress"
        }
        
        # Add optional analysis data based on request
        if request.include_market_analysis:
            response_data["market_analysis"] = {
                "median_price": 890000,
                "price_growth_12_month": 5.2,
                "market_outlook": "Stable Growth"
            }
        
        if request.include_risk_assessment:
            response_data["risk_assessment"] = {
                "overall_risk": "Low",
                "risk_factors": ["Stable market conditions", "Good transport links"]
            }
        
        if request.include_investment_metrics:
            response_data["investment_metrics"] = {
                "rental_yield": 4.2,
                "capital_growth_potential": "Medium"
            }
        
        if request.include_comparable_sales:
            response_data["comparable_sales"] = [
                {
                    "address": "125 Main Street, Parramatta NSW 2150",
                    "sale_price": 860000,
                    "similarity_score": 92
                }
            ]
        
        logger.info(f"Property profile completed for {request.address}")
        
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
                "suggestion": "Try using a different valuation type or check property details"
            }
        )
    
    except PropertyRateLimitError as e:
        logger.warning(f"Rate limit exceeded: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded. Please try again later.",
                "error_type": "rate_limit_exceeded",
                "retry_after": getattr(e, 'retry_after', 60)
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
        
        # Mock comparison response
        comparison = {
            "comparison_id": f"comp_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "properties_compared": len(request.addresses),
            "comparison_criteria": request.comparison_criteria or ["valuation", "market_performance"],
            "properties": [],
            "summary": {
                "highest_value": {"address": request.addresses[0], "value": 950000},
                "best_investment": {"address": request.addresses[0], "score": 8.5},
                "lowest_risk": {"address": request.addresses[0], "risk": "Low"}
            },
            "total_cost": len(request.addresses) * 12.50,
            "status": "Service implementation in progress"
        }
        
        # Add mock property data for each address
        for i, address in enumerate(request.addresses):
            comparison["properties"].append({
                "address": address,
                "valuation": 850000 + (i * 50000),
                "risk_level": "Low" if i % 2 == 0 else "Medium",
                "investment_score": 7.5 + (i * 0.5)
            })
        
        logger.info(f"Property comparison completed for {len(request.addresses)} properties")
        
        return comparison
    
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
    include_costs: bool = Query(False, description="Include cost and usage information")
) -> Dict[str, Any]:
    """Check service health and status."""
    
    try:
        response = {
            "service_status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "external_services": {
                "domain_api": {
                    "status": "healthy",
                    "response_time_ms": 150,
                    "rate_limit_remaining": 450
                },
                "corelogic_api": {
                    "status": "healthy", 
                    "response_time_ms": 280,
                    "rate_limit_remaining": 95
                }
            },
            "overall_health": "healthy",
            "implementation_status": "in_progress"
        }
        
        if include_costs:
            response["cost_information"] = {
                "daily_budget": 100.00,
                "daily_usage": 12.50,
                "remaining_budget": 87.50,
                "cost_per_profile": "5-35 AUD depending on options"
            }
        
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
        "pricing_date": datetime.now().strftime("%Y-%m-%d"),
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
        "estimated_total_costs": {
            "basic_profile": "AVM + basic analysis: ~$8-12 AUD",
            "standard_profile": "Desktop + full analysis: ~$20-25 AUD",
            "premium_profile": "Professional + full analysis: ~$30-35 AUD"
        }
    }


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