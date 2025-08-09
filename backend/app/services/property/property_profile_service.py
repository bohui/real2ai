"""
Property Profile Service for Real2.AI platform.

This service orchestrates between Domain and CoreLogic clients to provide
comprehensive property analysis and valuation services.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from dataclasses import dataclass

from app.clients.factory import get_domain_client, get_corelogic_client
from app.clients.base.exceptions import (
    PropertyNotFoundError, PropertyValuationError, ClientError,
    PropertyDataIncompleteError
)

logger = logging.getLogger(__name__)


@dataclass
class PropertyProfileRequest:
    """Request structure for property profile generation."""
    address: str
    property_type: Optional[str] = None
    valuation_type: str = "avm"  # avm, desktop, professional
    include_market_analysis: bool = True
    include_risk_assessment: bool = True
    include_investment_metrics: bool = True
    include_comparable_sales: bool = True
    radius_km: float = 2.0


@dataclass
class PropertyProfileResponse:
    """Response structure for comprehensive property profile."""
    request_id: str
    address: str
    generated_at: datetime
    data_sources: List[str]
    property_details: Dict[str, Any]
    valuation_data: Dict[str, Any]
    market_analysis: Optional[Dict[str, Any]] = None
    risk_assessment: Optional[Dict[str, Any]] = None
    investment_metrics: Optional[Dict[str, Any]] = None
    comparable_sales: Optional[Dict[str, Any]] = None
    data_quality_score: float = 0.0
    total_cost: float = 0.0
    processing_time_seconds: float = 0.0


class PropertyProfileService:
    """
    Orchestrated property profile service combining Domain and CoreLogic data.
    
    This service provides:
    - Comprehensive property profiles
    - Cross-validation between data sources
    - Intelligent data source selection
    - Cost optimization
    - Quality scoring
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._request_counter = 0
    
    async def generate_property_profile(self, request: PropertyProfileRequest) -> PropertyProfileResponse:
        """
        Generate a comprehensive property profile using multiple data sources.
        
        Args:
            request: Property profile request with analysis parameters
            
        Returns:
            PropertyProfileResponse: Comprehensive property analysis
        """
        start_time = datetime.now(timezone.utc)
        request_id = f"profile_{int(start_time.timestamp())}_{self._request_counter}"
        self._request_counter += 1
        
        self.logger.info(f"Generating property profile {request_id} for {request.address}")
        
        # Initialize response
        response = PropertyProfileResponse(
            request_id=request_id,
            address=request.address,
            generated_at=start_time,
            data_sources=[],
            property_details={},
            valuation_data={}
        )
        
        try:
            # Get clients
            domain_client = await get_domain_client()
            corelogic_client = await get_corelogic_client()
            
            # 1. Get basic property data from Domain (lower cost, good coverage)
            property_data = await self._get_domain_property_data(
                domain_client, request.address
            )
            response.data_sources.append("domain")
            response.property_details = property_data
            
            # 2. Get CoreLogic valuation (higher cost, professional grade)
            valuation_data = await self._get_corelogic_valuation(
                corelogic_client, request.address, property_data, request.valuation_type
            )
            response.data_sources.append("corelogic")
            response.valuation_data = valuation_data
            
            # 3. Optional analysis based on request
            analysis_tasks = []
            
            if request.include_market_analysis:
                analysis_tasks.append(
                    self._get_market_analysis(corelogic_client, property_data)
                )
            
            if request.include_risk_assessment:
                analysis_tasks.append(
                    self._get_risk_assessment(corelogic_client, property_data)
                )
            
            if request.include_investment_metrics:
                analysis_tasks.append(
                    self._get_investment_metrics(corelogic_client, property_data, valuation_data)
                )
            
            if request.include_comparable_sales:
                analysis_tasks.append(
                    self._get_comparable_sales(
                        corelogic_client, property_data, request.radius_km
                    )
                )
            
            # Execute analysis tasks in parallel
            if analysis_tasks:
                analysis_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
                
                # Process results
                task_index = 0
                if request.include_market_analysis:
                    if not isinstance(analysis_results[task_index], Exception):
                        response.market_analysis = analysis_results[task_index]
                    task_index += 1
                
                if request.include_risk_assessment:
                    if not isinstance(analysis_results[task_index], Exception):
                        response.risk_assessment = analysis_results[task_index]
                    task_index += 1
                
                if request.include_investment_metrics:
                    if not isinstance(analysis_results[task_index], Exception):
                        response.investment_metrics = analysis_results[task_index]
                    task_index += 1
                
                if request.include_comparable_sales:
                    if not isinstance(analysis_results[task_index], Exception):
                        response.comparable_sales = analysis_results[task_index]
                    task_index += 1
            
            # 4. Calculate data quality score
            response.data_quality_score = self._calculate_data_quality_score(response)
            
            # 5. Calculate total cost and processing time
            response.total_cost = await self._calculate_total_cost(
                corelogic_client, request
            )
            
            end_time = datetime.now(timezone.utc)
            response.processing_time_seconds = (end_time - start_time).total_seconds()
            
            self.logger.info(
                f"Property profile {request_id} completed in "
                f"{response.processing_time_seconds:.2f}s (Cost: ${response.total_cost:.2f})"
            )
            
            return response
        
        except Exception as e:
            self.logger.error(f"Property profile generation failed for {request_id}: {e}")
            raise PropertyValuationError(
                request.address,
                f"Profile generation failed: {str(e)}"
            )
    
    async def _get_domain_property_data(self, client, address: str) -> Dict[str, Any]:
        """Get basic property data from Domain."""
        try:
            # Search for property on Domain
            search_results = await client.search_properties({
                "address": address,
                "limit": 1
            })
            
            if not search_results.get("results"):
                raise PropertyNotFoundError(address)
            
            property_listing = search_results["results"][0]
            property_id = property_listing.get("id")
            
            if property_id:
                # Get detailed property information
                property_details = await client.get_property_details(property_id)
            else:
                property_details = property_listing
            
            # Get sales history if available
            sales_history = []
            try:
                if property_id:
                    sales_history = await client.get_sales_history(property_id)
            except Exception as e:
                self.logger.warning(f"Could not get sales history from Domain: {e}")
            
            return {
                "source": "domain",
                "property_id": property_id,
                "address": property_details.get("address", address),
                "property_type": property_details.get("property_type"),
                "bedrooms": property_details.get("bedrooms"),
                "bathrooms": property_details.get("bathrooms"),
                "parking_spaces": property_details.get("parking_spaces"),
                "land_area": property_details.get("land_area"),
                "building_area": property_details.get("building_area"),
                "features": property_details.get("features", []),
                "location": property_details.get("location", {}),
                "sales_history": sales_history,
                "listing_date": property_details.get("listing_date"),
                "agent_details": property_details.get("agent_details", {})
            }
        
        except PropertyNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to get Domain property data: {e}")
            raise PropertyDataIncompleteError(
                address, 
                ["domain_property_details"],
                original_error=e
            )
    
    async def _get_corelogic_valuation(self, client, address: str, 
                                     property_data: Dict[str, Any], 
                                     valuation_type: str) -> Dict[str, Any]:
        """Get professional valuation from CoreLogic."""
        try:
            # Prepare property details for CoreLogic
            property_details = {
                "valuation_type": valuation_type,
                "property_type": property_data.get("property_type", "house"),
                "bedrooms": property_data.get("bedrooms"),
                "bathrooms": property_data.get("bathrooms"),
                "land_area": property_data.get("land_area"),
                "building_area": property_data.get("building_area"),
                "features": property_data.get("features", [])
            }
            
            valuation = await client.get_property_valuation(address, property_details)
            
            return {
                "source": "corelogic",
                "valuation_amount": valuation["valuation_amount"],
                "valuation_type": valuation["valuation_type"],
                "confidence_score": valuation["confidence_score"],
                "valuation_date": valuation["valuation_date"],
                "methodology": valuation.get("methodology"),
                "comparables_used": valuation.get("comparables_used", 0),
                "value_range": valuation.get("value_range", {}),
                "market_conditions": valuation.get("market_conditions"),
                "risk_factors": valuation.get("risk_factors", []),
                "provider_metadata": valuation.get("provider_metadata", {})
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get CoreLogic valuation: {e}")
            raise PropertyValuationError(
                address,
                f"CoreLogic valuation failed: {str(e)}"
            )
    
    async def _get_market_analysis(self, client, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get market analysis from CoreLogic."""
        try:
            location = property_data.get("location", {})
            suburb = location.get("suburb")
            state = location.get("state")
            
            if not suburb or not state:
                raise ValueError("Missing location data for market analysis")
            
            market_data = await client.get_market_analytics(
                {"suburb": suburb, "state": state},
                property_data.get("property_type")
            )
            
            return market_data
        
        except Exception as e:
            self.logger.warning(f"Market analysis failed: {e}")
            return {"error": str(e), "source": "corelogic"}
    
    async def _get_risk_assessment(self, client, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get risk assessment from CoreLogic."""
        try:
            property_id = property_data.get("property_id")
            if not property_id:
                raise ValueError("Property ID required for risk assessment")
            
            risk_data = await client.get_property_risk_assessment(
                property_id, "comprehensive"
            )
            
            return risk_data
        
        except Exception as e:
            self.logger.warning(f"Risk assessment failed: {e}")
            return {"error": str(e), "source": "corelogic"}
    
    async def _get_investment_metrics(self, client, property_data: Dict[str, Any], 
                                    valuation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate investment metrics using CoreLogic."""
        try:
            property_id = property_data.get("property_id")
            purchase_price = valuation_data.get("valuation_amount")
            
            if not property_id or not purchase_price:
                raise ValueError("Missing data for investment analysis")
            
            # Estimate rental income (this could be enhanced with rental data)
            estimated_weekly_rent = purchase_price * 0.0004  # Rough estimate
            annual_rental = estimated_weekly_rent * 52
            
            yield_analysis = await client.calculate_investment_yield(
                property_id, purchase_price, annual_rental
            )
            
            return {
                **yield_analysis,
                "estimated_weekly_rent": estimated_weekly_rent,
                "purchase_price": purchase_price
            }
        
        except Exception as e:
            self.logger.warning(f"Investment metrics calculation failed: {e}")
            return {"error": str(e), "source": "corelogic"}
    
    async def _get_comparable_sales(self, client, property_data: Dict[str, Any], 
                                  radius_km: float) -> Dict[str, Any]:
        """Get comparable sales from CoreLogic."""
        try:
            property_id = property_data.get("property_id")
            if not property_id:
                raise ValueError("Property ID required for comparable sales")
            
            comparables = await client.get_comparable_sales(property_id, radius_km)
            
            return comparables
        
        except Exception as e:
            self.logger.warning(f"Comparable sales analysis failed: {e}")
            return {"error": str(e), "source": "corelogic"}
    
    def _calculate_data_quality_score(self, response: PropertyProfileResponse) -> float:
        """Calculate overall data quality score (0.0 to 1.0)."""
        score = 0.0
        max_score = 0.0
        
        # Base property data (30%)
        if response.property_details:
            max_score += 30
            completeness = self._calculate_completeness(response.property_details)
            score += completeness * 30
        
        # Valuation data (40%)
        if response.valuation_data:
            max_score += 40
            valuation_score = response.valuation_data.get("confidence_score", 0.0)
            score += valuation_score * 40
        
        # Market analysis (10%)
        if response.market_analysis and not response.market_analysis.get("error"):
            max_score += 10
            market_confidence = response.market_analysis.get("data_quality", {}).get("confidence", 0.8)
            score += market_confidence * 10
        
        # Risk assessment (10%)
        if response.risk_assessment and not response.risk_assessment.get("error"):
            max_score += 10
            score += 8  # Assume good quality if available
        
        # Investment metrics (5%)
        if response.investment_metrics and not response.investment_metrics.get("error"):
            max_score += 5
            score += 4  # Assume good quality if available
        
        # Comparable sales (5%)
        if response.comparable_sales and not response.comparable_sales.get("error"):
            max_score += 5
            comparable_count = response.comparable_sales.get("comparable_count", 0)
            if comparable_count >= 5:
                score += 5
            elif comparable_count >= 3:
                score += 3
            elif comparable_count >= 1:
                score += 1
        
        return score / max_score if max_score > 0 else 0.0
    
    def _calculate_completeness(self, data: Dict[str, Any]) -> float:
        """Calculate data completeness score."""
        required_fields = [
            "address", "property_type", "bedrooms", "bathrooms"
        ]
        optional_fields = [
            "land_area", "building_area", "parking_spaces", "features"
        ]
        
        score = 0.0
        
        # Required fields (70%)
        for field in required_fields:
            if data.get(field):
                score += 0.175  # 70% / 4 fields
        
        # Optional fields (30%)  
        for field in optional_fields:
            if data.get(field):
                score += 0.075  # 30% / 4 fields
        
        return min(score, 1.0)
    
    async def _calculate_total_cost(self, corelogic_client, 
                                  request: PropertyProfileRequest) -> float:
        """Calculate estimated total cost for the profile generation."""
        try:
            cost_summary = await corelogic_client.get_cost_summary()
            
            # Estimate based on operations performed
            base_valuation_cost = 5.0  # Typical AVM cost
            
            if request.valuation_type == "desktop":
                base_valuation_cost = 10.0
            elif request.valuation_type == "professional":
                base_valuation_cost = 17.5
            
            additional_costs = 0.0
            if request.include_market_analysis:
                additional_costs += 2.5
            if request.include_risk_assessment:
                additional_costs += 7.5
            if request.include_investment_metrics:
                additional_costs += 4.0
            if request.include_comparable_sales:
                additional_costs += 1.5
            
            return base_valuation_cost + additional_costs
        
        except Exception:
            # Fallback estimate
            return 15.0
    
    async def compare_properties(self, addresses: List[str], 
                               comparison_criteria: List[str] = None) -> Dict[str, Any]:
        """
        Compare multiple properties side by side.
        
        Args:
            addresses: List of property addresses to compare
            comparison_criteria: Specific criteria to focus on
            
        Returns:
            Comprehensive property comparison
        """
        if not comparison_criteria:
            comparison_criteria = [
                "valuation", "market_performance", "risk_assessment", "investment_potential"
            ]
        
        self.logger.info(f"Comparing {len(addresses)} properties")
        
        # Generate profiles for all properties
        profile_requests = [
            PropertyProfileRequest(
                address=address,
                valuation_type="avm",
                include_market_analysis=True,
                include_risk_assessment=True,
                include_investment_metrics=True
            )
            for address in addresses
        ]
        
        # Execute in parallel
        profiles = await asyncio.gather(
            *[self.generate_property_profile(req) for req in profile_requests],
            return_exceptions=True
        )
        
        # Process successful profiles
        successful_profiles = [
            profile for profile in profiles 
            if not isinstance(profile, Exception)
        ]
        
        if not successful_profiles:
            raise PropertyDataIncompleteError(
                "multiple_properties",
                ["All property profiles failed"]
            )
        
        # Create comparison matrix
        comparison = {
            "comparison_date": datetime.now(timezone.utc).isoformat(),
            "properties_compared": len(successful_profiles),
            "criteria": comparison_criteria,
            "properties": [],
            "rankings": {},
            "summary_statistics": {}
        }
        
        # Process each profile
        for profile in successful_profiles:
            property_comparison = {
                "address": profile.address,
                "valuation_amount": profile.valuation_data.get("valuation_amount", 0),
                "confidence_score": profile.valuation_data.get("confidence_score", 0),
                "data_quality_score": profile.data_quality_score,
                "processing_cost": profile.total_cost
            }
            
            # Add market performance
            if profile.market_analysis:
                market_metrics = profile.market_analysis.get("market_metrics", {})
                property_comparison["market_performance"] = {
                    "growth_1yr": market_metrics.get("price_growth_1yr", 0),
                    "days_on_market": market_metrics.get("days_on_market", 0),
                    "sales_volume": market_metrics.get("sales_volume", 0)
                }
            
            # Add risk assessment
            if profile.risk_assessment:
                property_comparison["risk_profile"] = {
                    "overall_risk_score": profile.risk_assessment.get("overall_risk_score", 0),
                    "risk_level": profile.risk_assessment.get("risk_level", "unknown")
                }
            
            # Add investment metrics
            if profile.investment_metrics:
                property_comparison["investment_potential"] = {
                    "gross_yield": profile.investment_metrics.get("gross_yield", 0),
                    "net_yield": profile.investment_metrics.get("net_yield", 0),
                    "cash_flow": profile.investment_metrics.get("cash_flow", 0)
                }
            
            comparison["properties"].append(property_comparison)
        
        # Generate rankings
        if len(successful_profiles) > 1:
            comparison["rankings"] = self._generate_property_rankings(
                comparison["properties"], comparison_criteria
            )
        
        # Calculate summary statistics
        comparison["summary_statistics"] = self._calculate_comparison_statistics(
            comparison["properties"]
        )
        
        return comparison
    
    def _generate_property_rankings(self, properties: List[Dict[str, Any]], 
                                  criteria: List[str]) -> Dict[str, List[str]]:
        """Generate property rankings based on specified criteria."""
        rankings = {}
        
        if "valuation" in criteria:
            rankings["highest_valuation"] = sorted(
                properties, 
                key=lambda p: p.get("valuation_amount", 0), 
                reverse=True
            )[0]["address"]
        
        if "market_performance" in criteria and any(p.get("market_performance") for p in properties):
            rankings["best_growth"] = sorted(
                [p for p in properties if p.get("market_performance")],
                key=lambda p: p["market_performance"].get("growth_1yr", 0),
                reverse=True
            )[0]["address"]
        
        if "risk_assessment" in criteria and any(p.get("risk_profile") for p in properties):
            rankings["lowest_risk"] = sorted(
                [p for p in properties if p.get("risk_profile")],
                key=lambda p: p["risk_profile"].get("overall_risk_score", 10),
                reverse=False
            )[0]["address"]
        
        if "investment_potential" in criteria and any(p.get("investment_potential") for p in properties):
            rankings["best_yield"] = sorted(
                [p for p in properties if p.get("investment_potential")],
                key=lambda p: p["investment_potential"].get("gross_yield", 0),
                reverse=True
            )[0]["address"]
        
        return rankings
    
    def _calculate_comparison_statistics(self, properties: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics for property comparison."""
        valuations = [p.get("valuation_amount", 0) for p in properties if p.get("valuation_amount")]
        
        stats = {
            "property_count": len(properties),
            "valuation_statistics": {}
        }
        
        if valuations:
            stats["valuation_statistics"] = {
                "min_valuation": min(valuations),
                "max_valuation": max(valuations),
                "average_valuation": sum(valuations) / len(valuations),
                "valuation_spread": max(valuations) - min(valuations)
            }
        
        # Data quality statistics
        quality_scores = [p.get("data_quality_score", 0) for p in properties]
        if quality_scores:
            stats["data_quality"] = {
                "average_quality_score": sum(quality_scores) / len(quality_scores),
                "min_quality_score": min(quality_scores),
                "max_quality_score": max(quality_scores)
            }
        
        return stats


# Global service instance
_property_profile_service: Optional[PropertyProfileService] = None


def get_property_profile_service() -> PropertyProfileService:
    """Get the global property profile service instance."""
    global _property_profile_service
    if _property_profile_service is None:
        _property_profile_service = PropertyProfileService()
    return _property_profile_service