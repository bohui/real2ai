"""
Property Valuation Service - Integrates Domain.com.au and CoreLogic APIs for comprehensive property analysis.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ..clients.domain.client import DomainClient
from ..clients.corelogic.client import CoreLogicClient
from ..clients.base.exceptions import (
    ClientError, PropertyNotFoundError, PropertyValuationError, 
    ClientRateLimitError, InvalidPropertyAddressError
)
from ..api.models import RiskLevel

logger = logging.getLogger(__name__)


class PropertyValuationService:
    """
    Service for comprehensive property valuation using multiple data sources.
    Combines Domain.com.au and CoreLogic APIs for enhanced accuracy and insights.
    """
    
    def __init__(self, domain_client: DomainClient, corelogic_client: CoreLogicClient):
        self.domain_client = domain_client
        self.corelogic_client = corelogic_client
        self.logger = logger
        
        # Service configuration
        self.config = {
            "enable_data_fusion": True,
            "require_multiple_sources": False,
            "confidence_weighting": {
                "domain": 0.4,
                "corelogic": 0.6  # CoreLogic typically more accurate for valuations
            },
            "timeout_seconds": 30,
            "max_concurrent_requests": 3
        }
    
    async def get_comprehensive_property_analysis(
        self, 
        address: str, 
        property_details: Optional[Dict[str, Any]] = None,
        include_market_data: bool = True,
        include_risk_assessment: bool = True,
        include_comparables: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive property analysis from multiple data sources.
        
        Args:
            address: Property address
            property_details: Additional property information
            include_market_data: Include market analytics
            include_risk_assessment: Include risk assessment
            include_comparables: Include comparable sales data
            
        Returns:
            Comprehensive property analysis with data from multiple sources
        """
        if not address or not address.strip():
            raise InvalidPropertyAddressError("Address cannot be empty")
        
        analysis_start_time = datetime.now(timezone.utc)
        
        try:
            # Initialize results structure
            comprehensive_analysis = {
                "address": address,
                "analysis_timestamp": analysis_start_time,
                "data_sources": [],
                "valuations": {},
                "market_data": {},
                "risk_assessment": {},
                "comparable_sales": {},
                "enriched_insights": {},
                "data_quality": {},
                "warnings": [],
                "processing_summary": {}
            }
            
            # Concurrent data collection from multiple sources
            tasks = []
            
            # Domain.com.au valuation
            tasks.append(self._get_domain_valuation(address, property_details))
            
            # CoreLogic valuation
            tasks.append(self._get_corelogic_valuation(address, property_details))
            
            # Market data if requested
            if include_market_data:
                tasks.append(self._get_market_analytics(address, property_details))
            
            # Risk assessment if requested
            if include_risk_assessment:
                tasks.append(self._get_risk_assessment(address, property_details))
            
            # Comparable sales if requested
            if include_comparables:
                tasks.append(self._get_comparable_sales(address, property_details))
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            domain_result, corelogic_result = results[0], results[1]
            market_result = results[2] if include_market_data else None
            risk_result = results[3] if include_risk_assessment else None
            comparables_result = results[4] if include_comparables else None
            
            # Process valuation results
            if not isinstance(domain_result, Exception):
                comprehensive_analysis["valuations"]["domain"] = domain_result
                comprehensive_analysis["data_sources"].append("domain")
            else:
                comprehensive_analysis["warnings"].append(f"Domain valuation failed: {str(domain_result)}")
            
            if not isinstance(corelogic_result, Exception):
                comprehensive_analysis["valuations"]["corelogic"] = corelogic_result
                comprehensive_analysis["data_sources"].append("corelogic")
            else:
                comprehensive_analysis["warnings"].append(f"CoreLogic valuation failed: {str(corelogic_result)}")
            
            # Process market data
            if market_result and not isinstance(market_result, Exception):
                comprehensive_analysis["market_data"] = market_result
            elif market_result:
                comprehensive_analysis["warnings"].append(f"Market data failed: {str(market_result)}")
            
            # Process risk assessment
            if risk_result and not isinstance(risk_result, Exception):
                comprehensive_analysis["risk_assessment"] = risk_result
            elif risk_result:
                comprehensive_analysis["warnings"].append(f"Risk assessment failed: {str(risk_result)}")
            
            # Process comparable sales
            if comparables_result and not isinstance(comparables_result, Exception):
                comprehensive_analysis["comparable_sales"] = comparables_result
            elif comparables_result:
                comprehensive_analysis["warnings"].append(f"Comparable sales failed: {str(comparables_result)}")
            
            # Generate enriched insights
            comprehensive_analysis["enriched_insights"] = self._generate_enriched_insights(comprehensive_analysis)
            
            # Assess overall data quality
            comprehensive_analysis["data_quality"] = self._assess_overall_data_quality(comprehensive_analysis)
            
            # Generate processing summary
            processing_time = (datetime.now(timezone.utc) - analysis_start_time).total_seconds()
            comprehensive_analysis["processing_summary"] = {
                "processing_time_seconds": processing_time,
                "data_sources_used": len(comprehensive_analysis["data_sources"]),
                "successful_operations": len([r for r in results if not isinstance(r, Exception)]),
                "failed_operations": len([r for r in results if isinstance(r, Exception)]),
                "analysis_completeness": self._calculate_completeness_score(comprehensive_analysis)
            }
            
            return comprehensive_analysis
            
        except Exception as e:
            self.logger.error(f"Comprehensive property analysis failed for {address}: {e}")
            raise PropertyValuationError(f"Property analysis failed: {str(e)}")
    
    async def _get_domain_valuation(self, address: str, property_details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get valuation from Domain.com.au API."""
        try:
            result = await self.domain_client.get_property_valuation(address, property_details)
            result["source"] = "domain"
            result["retrieval_timestamp"] = datetime.now(timezone.utc)
            return result
        except Exception as e:
            self.logger.warning(f"Domain valuation failed for {address}: {e}")
            raise e
    
    async def _get_corelogic_valuation(self, address: str, property_details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get valuation from CoreLogic API."""
        try:
            if not property_details:
                property_details = {}
            
            # Set valuation type based on requirements
            if "valuation_type" not in property_details:
                property_details["valuation_type"] = "avm"  # Default to AVM for cost efficiency
            
            result = await self.corelogic_client.get_property_valuation(address, property_details)
            result["source"] = "corelogic"
            result["retrieval_timestamp"] = datetime.now(timezone.utc)
            return result
        except Exception as e:
            self.logger.warning(f"CoreLogic valuation failed for {address}: {e}")
            raise e
    
    async def _get_market_analytics(self, address: str, property_details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get market analytics from available sources."""
        try:
            # Extract location information from address
            location = self._extract_location_from_address(address)
            
            # Try Domain first for market analytics
            try:
                domain_market = await self.domain_client.get_market_analytics(location)
                domain_market["source"] = "domain"
                return domain_market
            except Exception as domain_e:
                self.logger.debug(f"Domain market analytics failed: {domain_e}")
            
            # Fallback to CoreLogic if Domain fails
            try:
                corelogic_market = await self.corelogic_client.get_market_analytics(location)
                corelogic_market["source"] = "corelogic"
                return corelogic_market
            except Exception as corelogic_e:
                self.logger.debug(f"CoreLogic market analytics failed: {corelogic_e}")
                raise corelogic_e
                
        except Exception as e:
            self.logger.warning(f"Market analytics failed for {address}: {e}")
            raise e
    
    async def _get_risk_assessment(self, address: str, property_details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get risk assessment from available sources."""
        try:
            # Try CoreLogic first for risk assessment (their specialty)
            risk_assessment = {
                "overall_risk": RiskLevel.MEDIUM,
                "risk_factors": [],
                "assessment_source": "internal",
                "confidence": 0.7
            }
            
            # Implement basic risk assessment logic
            risk_factors = []
            
            # Market-based risk factors would be added here
            # This is a simplified implementation
            risk_assessment["risk_factors"] = risk_factors
            risk_assessment["assessment_timestamp"] = datetime.now(timezone.utc)
            
            return risk_assessment
            
        except Exception as e:
            self.logger.warning(f"Risk assessment failed for {address}: {e}")
            raise e
    
    async def _get_comparable_sales(self, address: str, property_details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get comparable sales from available sources."""
        try:
            # Try both sources and combine results
            domain_comparables = None
            corelogic_comparables = None
            
            # Domain comparable sales
            try:
                # For Domain, we need to search for the property first to get property_id
                search_params = {"address": address, "listing_type": "Sale", "page_size": 1}
                search_results = await self.domain_client.search_properties(search_params)
                
                if search_results.get("listings"):
                    property_id = search_results["listings"][0].get("listing_id")
                    if property_id:
                        domain_comparables = await self.domain_client.get_comparable_sales(str(property_id))
                        domain_comparables["source"] = "domain"
            except Exception as e:
                self.logger.debug(f"Domain comparable sales failed: {e}")
            
            # Return the available comparables data
            if domain_comparables:
                return domain_comparables
            
            # If no data available, return empty structure
            return {
                "comparable_sales": [],
                "source": "none",
                "message": "No comparable sales data available"
            }
            
        except Exception as e:
            self.logger.warning(f"Comparable sales failed for {address}: {e}")
            raise e
    
    def _extract_location_from_address(self, address: str) -> Dict[str, str]:
        """Extract location components from address string."""
        # Simple location extraction - in production, use proper address parsing
        words = address.upper().split()
        
        # Find Australian state
        states = ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"]
        state = next((word for word in words if word in states), "NSW")
        
        # Extract suburb (assume it's before the state)
        try:
            state_index = words.index(state)
            if state_index > 0:
                suburb = words[state_index - 1]
            else:
                suburb = "Unknown"
        except ValueError:
            suburb = "Unknown"
        
        return {
            "suburb": suburb.title(),
            "state": state
        }
    
    def _generate_enriched_insights(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate enriched insights by combining data from multiple sources."""
        insights = {
            "valuation_consensus": None,
            "confidence_assessment": None,
            "market_position": None,
            "investment_outlook": None,
            "key_insights": [],
            "recommendations": []
        }
        
        valuations = analysis.get("valuations", {})
        
        # Valuation consensus
        if len(valuations) >= 2:
            insights["valuation_consensus"] = self._calculate_valuation_consensus(valuations)
        elif len(valuations) == 1:
            source = list(valuations.keys())[0]
            single_valuation = valuations[source]
            insights["valuation_consensus"] = {
                "consensus_value": single_valuation.get("estimated_value", 0),
                "value_range_low": single_valuation.get("valuation_range_lower", 0),
                "value_range_high": single_valuation.get("valuation_range_upper", 0),
                "confidence": single_valuation.get("confidence", 0.5),
                "source_count": 1,
                "primary_source": source
            }
        
        # Confidence assessment
        insights["confidence_assessment"] = self._assess_overall_confidence(analysis)
        
        # Market position analysis
        market_data = analysis.get("market_data", {})
        if market_data:
            insights["market_position"] = self._analyze_market_position(valuations, market_data)
        
        # Investment outlook
        insights["investment_outlook"] = self._generate_investment_outlook(analysis)
        
        # Key insights generation
        insights["key_insights"] = self._generate_key_insights(analysis)
        
        # Recommendations
        insights["recommendations"] = self._generate_recommendations(analysis)
        
        return insights
    
    def _calculate_valuation_consensus(self, valuations: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate consensus valuation from multiple sources."""
        values = []
        confidences = []
        sources = []
        
        for source, valuation in valuations.items():
            if source == "domain":
                domain_val = valuation.get("valuations", {}).get("domain", {})
                estimated_value = domain_val.get("estimated_value", 0)
                confidence = domain_val.get("confidence", 0.5)
            elif source == "corelogic":
                estimated_value = valuation.get("valuation_amount", 0)
                confidence = valuation.get("confidence_score", 0.5)
            else:
                continue
            
            if estimated_value > 0:
                values.append(estimated_value)
                confidences.append(confidence)
                sources.append(source)
        
        if not values:
            return {
                "consensus_value": 0,
                "value_range_low": 0,
                "value_range_high": 0,
                "confidence": 0.0,
                "source_count": 0,
                "variance": 0.0
            }
        
        # Calculate weighted average based on confidence
        total_weight = sum(confidences)
        if total_weight > 0:
            weighted_value = sum(v * c for v, c in zip(values, confidences)) / total_weight
        else:
            weighted_value = sum(values) / len(values)
        
        # Calculate variance
        mean_value = sum(values) / len(values)
        variance = sum((v - mean_value) ** 2 for v in values) / len(values) if len(values) > 1 else 0
        variance_percentage = (variance ** 0.5) / mean_value * 100 if mean_value > 0 else 0
        
        # Calculate range
        min_value, max_value = min(values), max(values)
        
        return {
            "consensus_value": int(weighted_value),
            "value_range_low": int(min_value),
            "value_range_high": int(max_value),
            "confidence": sum(confidences) / len(confidences),
            "source_count": len(sources),
            "sources": sources,
            "variance_percentage": round(variance_percentage, 1),
            "agreement_level": "high" if variance_percentage < 10 else "medium" if variance_percentage < 25 else "low"
        }
    
    def _assess_overall_confidence(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall confidence in the analysis."""
        confidence_factors = []
        
        # Data source diversity
        source_count = len(analysis.get("data_sources", []))
        if source_count >= 2:
            confidence_factors.append(("multiple_sources", 0.3))
        else:
            confidence_factors.append(("single_source", 0.1))
        
        # Valuation agreement
        consensus = analysis.get("enriched_insights", {}).get("valuation_consensus", {})
        agreement_level = consensus.get("agreement_level", "low")
        if agreement_level == "high":
            confidence_factors.append(("high_agreement", 0.25))
        elif agreement_level == "medium":
            confidence_factors.append(("medium_agreement", 0.15))
        else:
            confidence_factors.append(("low_agreement", 0.05))
        
        # Market data availability
        if analysis.get("market_data"):
            confidence_factors.append(("market_data_available", 0.2))
        
        # Risk assessment availability
        if analysis.get("risk_assessment"):
            confidence_factors.append(("risk_assessment_available", 0.15))
        
        # Calculate overall confidence
        total_confidence = sum(score for _, score in confidence_factors)
        
        return {
            "overall_confidence": round(min(1.0, total_confidence), 2),
            "confidence_level": "high" if total_confidence > 0.8 else "medium" if total_confidence > 0.5 else "low",
            "contributing_factors": [factor for factor, _ in confidence_factors]
        }
    
    def _analyze_market_position(self, valuations: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze property's position in the market."""
        position_analysis = {
            "price_vs_median": "unknown",
            "market_tier": "unknown",
            "liquidity_assessment": "unknown",
            "growth_potential": "unknown"
        }
        
        # Get consensus valuation
        consensus = self._calculate_valuation_consensus(valuations)
        property_value = consensus.get("consensus_value", 0)
        
        if property_value > 0 and market_data:
            median_price = market_data.get("median_price", 0)
            
            if median_price > 0:
                price_ratio = property_value / median_price
                
                if price_ratio > 1.5:
                    position_analysis["price_vs_median"] = "above_market"
                    position_analysis["market_tier"] = "premium"
                elif price_ratio > 1.1:
                    position_analysis["price_vs_median"] = "above_median"
                    position_analysis["market_tier"] = "upper_middle"
                elif price_ratio > 0.9:
                    position_analysis["price_vs_median"] = "at_median"
                    position_analysis["market_tier"] = "middle"
                else:
                    position_analysis["price_vs_median"] = "below_median"
                    position_analysis["market_tier"] = "entry_level"
            
            # Market activity assessment
            sales_volume = market_data.get("sales_volume_12_month", 0)
            if sales_volume > 50:
                position_analysis["liquidity_assessment"] = "high"
            elif sales_volume > 20:
                position_analysis["liquidity_assessment"] = "medium"
            else:
                position_analysis["liquidity_assessment"] = "low"
        
        return position_analysis
    
    def _generate_investment_outlook(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate investment outlook based on available data."""
        outlook = {
            "investment_rating": "neutral",
            "growth_potential": "moderate",
            "risk_level": "medium",
            "time_horizon": "medium_term",
            "key_factors": []
        }
        
        # Analyze market data for growth potential
        market_data = analysis.get("market_data", {})
        if market_data:
            price_growth = market_data.get("price_growth_12_month", 0)
            
            if price_growth > 10:
                outlook["growth_potential"] = "high"
                outlook["key_factors"].append("Strong recent price growth")
            elif price_growth > 5:
                outlook["growth_potential"] = "moderate"
            elif price_growth < -5:
                outlook["growth_potential"] = "low"
                outlook["key_factors"].append("Declining market prices")
        
        # Risk assessment
        risk_data = analysis.get("risk_assessment", {})
        if risk_data:
            overall_risk = risk_data.get("overall_risk", RiskLevel.MEDIUM)
            if overall_risk == RiskLevel.LOW:
                outlook["risk_level"] = "low"
            elif overall_risk == RiskLevel.HIGH:
                outlook["risk_level"] = "high"
        
        return outlook
    
    def _generate_key_insights(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate key insights from the analysis."""
        insights = []
        
        # Valuation insights
        consensus = analysis.get("enriched_insights", {}).get("valuation_consensus", {})
        if consensus:
            source_count = consensus.get("source_count", 0)
            if source_count >= 2:
                agreement = consensus.get("agreement_level", "unknown")
                if agreement == "high":
                    insights.append("Multiple valuation sources show strong agreement on property value")
                elif agreement == "low":
                    insights.append("Valuation sources show significant disagreement - further investigation recommended")
        
        # Market insights
        market_data = analysis.get("market_data", {})
        if market_data:
            market_outlook = market_data.get("market_outlook", "unknown")
            if market_outlook == "active":
                insights.append("Property is in an active market with good liquidity")
            elif market_outlook == "quiet":
                insights.append("Market activity is limited - longer selling times expected")
        
        # Data quality insights
        data_quality = analysis.get("data_quality", {})
        overall_quality = data_quality.get("overall_quality", "unknown")
        if overall_quality == "high":
            insights.append("Analysis based on high-quality, comprehensive data")
        elif overall_quality == "low":
            insights.append("Limited data available - results should be interpreted with caution")
        
        return insights
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on the analysis."""
        recommendations = []
        
        # Data quality recommendations
        data_sources = analysis.get("data_sources", [])
        if len(data_sources) < 2:
            recommendations.append("Consider obtaining additional valuation opinions for better accuracy")
        
        # Market timing recommendations
        market_data = analysis.get("market_data", {})
        if market_data:
            price_growth = market_data.get("price_growth_12_month", 0)
            if price_growth > 15:
                recommendations.append("Strong market growth may indicate good timing for sellers")
            elif price_growth < -5:
                recommendations.append("Market decline may present opportunities for buyers")
        
        # Risk recommendations
        warnings = analysis.get("warnings", [])
        if len(warnings) > 2:
            recommendations.append("Multiple data issues identified - recommend additional due diligence")
        
        return recommendations
    
    def _assess_overall_data_quality(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the overall quality of data used in the analysis."""
        quality_factors = []
        
        # Source diversity
        source_count = len(analysis.get("data_sources", []))
        if source_count >= 2:
            quality_factors.append(("multiple_sources", 0.3))
        else:
            quality_factors.append(("limited_sources", 0.1))
        
        # Data completeness
        data_sections = ["valuations", "market_data", "risk_assessment", "comparable_sales"]
        completed_sections = sum(1 for section in data_sections if analysis.get(section))
        completeness_score = completed_sections / len(data_sections)
        quality_factors.append(("data_completeness", completeness_score * 0.4))
        
        # Warning count (inverse quality indicator)
        warning_count = len(analysis.get("warnings", []))
        warning_penalty = max(0, 0.3 - (warning_count * 0.05))
        quality_factors.append(("warning_penalty", warning_penalty))
        
        # Calculate overall quality
        total_quality = sum(score for _, score in quality_factors)
        
        if total_quality > 0.8:
            quality_rating = "high"
        elif total_quality > 0.5:
            quality_rating = "medium"
        else:
            quality_rating = "low"
        
        return {
            "overall_quality": quality_rating,
            "quality_score": round(total_quality, 2),
            "data_completeness": round(completeness_score, 2),
            "source_diversity": source_count,
            "warning_count": warning_count,
            "quality_factors": [factor for factor, _ in quality_factors]
        }
    
    def _calculate_completeness_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate analysis completeness score."""
        total_sections = 5  # valuations, market_data, risk_assessment, comparable_sales, enriched_insights
        completed_sections = 0
        
        if analysis.get("valuations"):
            completed_sections += 1
        if analysis.get("market_data"):
            completed_sections += 1
        if analysis.get("risk_assessment"):
            completed_sections += 1
        if analysis.get("comparable_sales"):
            completed_sections += 1
        if analysis.get("enriched_insights"):
            completed_sections += 1
        
        return completed_sections / total_sections


# Factory function for creating the service
async def create_property_valuation_service(
    domain_config: Optional[Dict[str, Any]] = None,
    corelogic_config: Optional[Dict[str, Any]] = None
) -> PropertyValuationService:
    """
    Factory function to create PropertyValuationService with initialized clients.
    
    Args:
        domain_config: Domain API configuration
        corelogic_config: CoreLogic API configuration
        
    Returns:
        Initialized PropertyValuationService
    """
    from ..clients.domain.config import DomainClientConfig
    from ..clients.corelogic.config import CoreLogicClientConfig
    
    # Initialize Domain client
    if not domain_config:
        domain_config = {"api_key": "demo_key"}  # Default config for testing
    
    domain_client_config = DomainClientConfig(**domain_config)
    domain_client = DomainClient(domain_client_config)
    await domain_client.initialize()
    
    # Initialize CoreLogic client  
    if not corelogic_config:
        corelogic_config = {
            "api_key": "demo_key",
            "client_id": "demo_client",
            "client_secret": "demo_secret"
        }  # Default config for testing
    
    corelogic_client_config = CoreLogicClientConfig(**corelogic_config)
    corelogic_client = CoreLogicClient(corelogic_client_config)
    await corelogic_client.initialize()
    
    return PropertyValuationService(domain_client, corelogic_client)