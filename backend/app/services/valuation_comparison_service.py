"""
Valuation Comparison Service - Provides detailed comparison and analysis of property valuations from multiple sources.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class VarianceLevel(Enum):
    """Enumeration for valuation variance levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class ReliabilityRating(Enum):
    """Enumeration for source reliability ratings."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


@dataclass
class ValuationSource:
    """Data class representing a single valuation source."""
    name: str
    estimated_value: float
    confidence_score: float
    valuation_date: datetime
    methodology: str
    comparable_count: int = 0
    value_range_low: float = 0
    value_range_high: float = 0
    additional_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}


class ValuationComparisonService:
    """
    Service for comparing and analyzing property valuations from multiple sources.
    Provides detailed insights into valuation differences and reliability.
    """
    
    def __init__(self):
        self.logger = logger
        
        # Source reliability ratings based on typical accuracy and methodology
        self.source_reliability = {
            "corelogic": {
                "rating": ReliabilityRating.EXCELLENT,
                "accuracy_weight": 0.9,
                "methodology_weight": 0.95,
                "market_coverage": 0.9
            },
            "domain": {
                "rating": ReliabilityRating.GOOD,
                "accuracy_weight": 0.8,
                "methodology_weight": 0.75,
                "market_coverage": 0.85
            },
            "internal": {
                "rating": ReliabilityRating.FAIR,
                "accuracy_weight": 0.6,
                "methodology_weight": 0.5,
                "market_coverage": 0.6
            }
        }
        
        # Variance thresholds for classification
        self.variance_thresholds = {
            "low": 0.05,      # 5%
            "medium": 0.15,   # 15%
            "high": 0.30,     # 30%
            "very_high": 1.0  # Above 30%
        }
    
    def compare_valuations(
        self, 
        valuations: Dict[str, Any], 
        property_address: str,
        analysis_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Compare valuations from multiple sources and provide detailed analysis.
        
        Args:
            valuations: Dictionary of valuations from different sources
            property_address: Property address for context
            analysis_options: Optional analysis configuration
            
        Returns:
            Comprehensive valuation comparison analysis
        """
        if not valuations:
            raise ValueError("At least one valuation is required for comparison")
        
        if not analysis_options:
            analysis_options = {}
        
        # Parse valuations into standardized format
        valuation_sources = self._parse_valuations(valuations)
        
        if len(valuation_sources) < 1:
            raise ValueError("No valid valuations found for comparison")
        
        # Perform comprehensive comparison analysis
        comparison_analysis = {
            "property_address": property_address,
            "analysis_timestamp": datetime.now(timezone.utc),
            "valuation_sources": [self._serialize_valuation_source(vs) for vs in valuation_sources],
            "summary_statistics": self._calculate_summary_statistics(valuation_sources),
            "variance_analysis": self._analyze_variance(valuation_sources),
            "reliability_analysis": self._analyze_reliability(valuation_sources),
            "consensus_valuation": self._calculate_consensus_valuation(valuation_sources),
            "outlier_analysis": self._identify_outliers(valuation_sources),
            "methodology_comparison": self._compare_methodologies(valuation_sources),
            "confidence_analysis": self._analyze_confidence_levels(valuation_sources),
            "recommendations": self._generate_recommendations(valuation_sources),
            "risk_assessment": self._assess_valuation_risk(valuation_sources),
            "market_context": self._provide_market_context(valuation_sources, analysis_options),
            "quality_scores": self._calculate_quality_scores(valuation_sources)
        }
        
        return comparison_analysis
    
    def _parse_valuations(self, valuations: Dict[str, Any]) -> List[ValuationSource]:
        """Parse raw valuation data into standardized ValuationSource objects."""
        valuation_sources = []
        
        for source_name, valuation_data in valuations.items():
            try:
                # Handle different source formats
                if source_name == "domain":
                    source = self._parse_domain_valuation(valuation_data)
                elif source_name == "corelogic":
                    source = self._parse_corelogic_valuation(valuation_data)
                else:
                    source = self._parse_generic_valuation(source_name, valuation_data)
                
                if source:
                    valuation_sources.append(source)
                    
            except Exception as e:
                self.logger.warning(f"Failed to parse valuation from {source_name}: {e}")
                continue
        
        return valuation_sources
    
    def _parse_domain_valuation(self, data: Dict[str, Any]) -> Optional[ValuationSource]:
        """Parse Domain.com.au valuation data."""
        # Handle Domain's nested structure
        domain_val = data.get("valuations", {}).get("domain", {})
        
        if not domain_val.get("estimated_value"):
            return None
        
        return ValuationSource(
            name="domain",
            estimated_value=float(domain_val["estimated_value"]),
            confidence_score=float(domain_val.get("confidence", 0.5)),
            valuation_date=self._parse_date(domain_val.get("valuation_date")),
            methodology=domain_val.get("methodology", "market_comparison"),
            value_range_low=float(domain_val.get("valuation_range_lower", 0)),
            value_range_high=float(domain_val.get("valuation_range_upper", 0)),
            additional_data={
                "currency": domain_val.get("currency", "AUD"),
                "data_sources_used": data.get("data_sources_used", []),
                "warnings": data.get("warnings", [])
            }
        )
    
    def _parse_corelogic_valuation(self, data: Dict[str, Any]) -> Optional[ValuationSource]:
        """Parse CoreLogic valuation data."""
        if not data.get("valuation_amount"):
            return None
        
        return ValuationSource(
            name="corelogic",
            estimated_value=float(data["valuation_amount"]),
            confidence_score=float(data.get("confidence_score", 0.5)),
            valuation_date=self._parse_date(data.get("valuation_date")),
            methodology=data.get("methodology", "avm"),
            comparable_count=int(data.get("comparables_used", 0)),
            value_range_low=float(data.get("value_range", {}).get("low", 0)),
            value_range_high=float(data.get("value_range", {}).get("high", 0)),
            additional_data={
                "valuation_type": data.get("valuation_type", "avm"),
                "market_conditions": data.get("market_conditions", {}),
                "risk_factors": data.get("risk_factors", []),
                "quality_assessment": data.get("quality_assessment", {}),
                "cost_information": data.get("cost_information", {})
            }
        )
    
    def _parse_generic_valuation(self, source_name: str, data: Dict[str, Any]) -> Optional[ValuationSource]:
        """Parse generic valuation data format."""
        estimated_value = data.get("estimated_value") or data.get("valuation_amount") or data.get("value")
        
        if not estimated_value:
            return None
        
        return ValuationSource(
            name=source_name,
            estimated_value=float(estimated_value),
            confidence_score=float(data.get("confidence_score", data.get("confidence", 0.5))),
            valuation_date=self._parse_date(data.get("valuation_date", data.get("date"))),
            methodology=data.get("methodology", "unknown"),
            comparable_count=int(data.get("comparable_count", data.get("comparables_used", 0))),
            value_range_low=float(data.get("value_range_low", 0)),
            value_range_high=float(data.get("value_range_high", 0)),
            additional_data=data
        )
    
    def _parse_date(self, date_value: Any) -> datetime:
        """Parse date value into datetime object."""
        if isinstance(date_value, datetime):
            return date_value
        elif isinstance(date_value, str):
            try:
                return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            except:
                return datetime.now(timezone.utc)
        else:
            return datetime.now(timezone.utc)
    
    def _serialize_valuation_source(self, source: ValuationSource) -> Dict[str, Any]:
        """Serialize ValuationSource for JSON output."""
        return {
            "name": source.name,
            "estimated_value": source.estimated_value,
            "confidence_score": source.confidence_score,
            "valuation_date": source.valuation_date.isoformat(),
            "methodology": source.methodology,
            "comparable_count": source.comparable_count,
            "value_range": {
                "low": source.value_range_low,
                "high": source.value_range_high
            },
            "additional_data": source.additional_data
        }
    
    def _calculate_summary_statistics(self, sources: List[ValuationSource]) -> Dict[str, Any]:
        """Calculate summary statistics for all valuations."""
        values = [s.estimated_value for s in sources]
        confidences = [s.confidence_score for s in sources]
        
        if not values:
            return {}
        
        sorted_values = sorted(values)
        n = len(values)
        
        return {
            "count": n,
            "mean": sum(values) / n,
            "median": sorted_values[n // 2] if n % 2 == 1 else (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2,
            "min": min(values),
            "max": max(values),
            "range": max(values) - min(values),
            "standard_deviation": self._calculate_std_dev(values),
            "coefficient_of_variation": self._calculate_coefficient_of_variation(values),
            "average_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "confidence_range": {
                "min": min(confidences) if confidences else 0,
                "max": max(confidences) if confidences else 0
            }
        }
    
    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    def _calculate_coefficient_of_variation(self, values: List[float]) -> float:
        """Calculate coefficient of variation (CV)."""
        if not values:
            return 0.0
        
        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0
        
        std_dev = self._calculate_std_dev(values)
        return std_dev / mean
    
    def _analyze_variance(self, sources: List[ValuationSource]) -> Dict[str, Any]:
        """Analyze variance between valuations."""
        if len(sources) < 2:
            return {
                "variance_level": VarianceLevel.LOW,
                "variance_percentage": 0.0,
                "analysis": "Insufficient data for variance analysis"
            }
        
        values = [s.estimated_value for s in sources]
        mean_value = sum(values) / len(values)
        
        # Calculate coefficient of variation as variance measure
        cv = self._calculate_coefficient_of_variation(values)
        
        # Classify variance level
        if cv <= self.variance_thresholds["low"]:
            variance_level = VarianceLevel.LOW
        elif cv <= self.variance_thresholds["medium"]:
            variance_level = VarianceLevel.MEDIUM
        elif cv <= self.variance_thresholds["high"]:
            variance_level = VarianceLevel.HIGH
        else:
            variance_level = VarianceLevel.VERY_HIGH
        
        # Detailed variance analysis
        max_deviation = max(abs(v - mean_value) for v in values)
        max_deviation_percentage = (max_deviation / mean_value) * 100 if mean_value > 0 else 0
        
        return {
            "variance_level": variance_level,
            "coefficient_of_variation": cv,
            "variance_percentage": cv * 100,
            "max_deviation": max_deviation,
            "max_deviation_percentage": max_deviation_percentage,
            "analysis": self._generate_variance_analysis(variance_level, cv),
            "pairwise_differences": self._calculate_pairwise_differences(sources)
        }
    
    def _calculate_pairwise_differences(self, sources: List[ValuationSource]) -> List[Dict[str, Any]]:
        """Calculate pairwise differences between all valuation sources."""
        differences = []
        
        for i, source1 in enumerate(sources):
            for j, source2 in enumerate(sources):
                if i < j:  # Avoid duplicate pairs
                    diff = abs(source1.estimated_value - source2.estimated_value)
                    avg_value = (source1.estimated_value + source2.estimated_value) / 2
                    diff_percentage = (diff / avg_value) * 100 if avg_value > 0 else 0
                    
                    differences.append({
                        "source1": source1.name,
                        "source2": source2.name,
                        "absolute_difference": diff,
                        "percentage_difference": diff_percentage,
                        "higher_valuation": source1.name if source1.estimated_value > source2.estimated_value else source2.name
                    })
        
        return sorted(differences, key=lambda x: x["percentage_difference"], reverse=True)
    
    def _generate_variance_analysis(self, variance_level: VarianceLevel, cv: float) -> str:
        """Generate human-readable variance analysis."""
        if variance_level == VarianceLevel.LOW:
            return f"Low variance ({cv:.1%}) indicates strong agreement between valuation sources"
        elif variance_level == VarianceLevel.MEDIUM:
            return f"Medium variance ({cv:.1%}) suggests some disagreement that warrants investigation"
        elif variance_level == VarianceLevel.HIGH:
            return f"High variance ({cv:.1%}) indicates significant disagreement between sources"
        else:
            return f"Very high variance ({cv:.1%}) suggests major discrepancies requiring careful review"
    
    def _analyze_reliability(self, sources: List[ValuationSource]) -> Dict[str, Any]:
        """Analyze reliability of each valuation source."""
        reliability_scores = {}
        
        for source in sources:
            source_name = source.name.lower()
            base_reliability = self.source_reliability.get(source_name, {
                "rating": ReliabilityRating.FAIR,
                "accuracy_weight": 0.5,
                "methodology_weight": 0.5,
                "market_coverage": 0.5
            })
            
            # Adjust reliability based on confidence and comparable count
            confidence_factor = source.confidence_score
            comparable_factor = min(1.0, source.comparable_count / 10) if source.comparable_count > 0 else 0.5
            
            # Calculate overall reliability score
            reliability_score = (
                base_reliability["accuracy_weight"] * 0.4 +
                confidence_factor * 0.3 +
                comparable_factor * 0.2 +
                base_reliability["methodology_weight"] * 0.1
            )
            
            reliability_scores[source.name] = {
                "score": reliability_score,
                "rating": base_reliability["rating"],
                "confidence_score": source.confidence_score,
                "comparable_count": source.comparable_count,
                "methodology": source.methodology,
                "factors": {
                    "base_accuracy": base_reliability["accuracy_weight"],
                    "confidence_factor": confidence_factor,
                    "comparable_factor": comparable_factor,
                    "methodology_factor": base_reliability["methodology_weight"]
                }
            }
        
        return {
            "source_reliability": reliability_scores,
            "most_reliable": max(reliability_scores.keys(), key=lambda k: reliability_scores[k]["score"]),
            "least_reliable": min(reliability_scores.keys(), key=lambda k: reliability_scores[k]["score"]),
            "average_reliability": sum(r["score"] for r in reliability_scores.values()) / len(reliability_scores)
        }
    
    def _calculate_consensus_valuation(self, sources: List[ValuationSource]) -> Dict[str, Any]:
        """Calculate consensus valuation using weighted approach."""
        if not sources:
            return {}
        
        # Calculate weights based on reliability and confidence
        weighted_values = []
        total_weight = 0
        
        for source in sources:
            source_name = source.name.lower()
            base_reliability = self.source_reliability.get(source_name, {
                "accuracy_weight": 0.5
            })
            
            # Weight combines base reliability and confidence
            weight = base_reliability["accuracy_weight"] * source.confidence_score
            weighted_values.append(source.estimated_value * weight)
            total_weight += weight
        
        if total_weight == 0:
            # Fallback to simple average
            consensus_value = sum(s.estimated_value for s in sources) / len(sources)
            consensus_confidence = sum(s.confidence_score for s in sources) / len(sources)
        else:
            consensus_value = sum(weighted_values) / total_weight
            consensus_confidence = sum(s.confidence_score for s in sources) / len(sources)
        
        # Calculate consensus range
        values = [s.estimated_value for s in sources]
        consensus_range_low = min(values)
        consensus_range_high = max(values)
        
        return {
            "consensus_value": int(consensus_value),
            "consensus_confidence": consensus_confidence,
            "value_range": {
                "low": int(consensus_range_low),
                "high": int(consensus_range_high)
            },
            "weighting_method": "reliability_confidence_weighted",
            "contributing_sources": len(sources)
        }
    
    def _identify_outliers(self, sources: List[ValuationSource]) -> Dict[str, Any]:
        """Identify outlier valuations using statistical methods."""
        if len(sources) < 3:
            return {
                "outliers": [],
                "analysis": "Insufficient data for outlier detection (need at least 3 sources)"
            }
        
        values = [s.estimated_value for s in sources]
        mean = sum(values) / len(values)
        std_dev = self._calculate_std_dev(values)
        
        outliers = []
        
        # Use z-score method (values more than 2 standard deviations from mean)
        threshold = 2.0
        
        for source in sources:
            if std_dev > 0:
                z_score = abs(source.estimated_value - mean) / std_dev
                if z_score > threshold:
                    outliers.append({
                        "source": source.name,
                        "value": source.estimated_value,
                        "z_score": z_score,
                        "deviation_from_mean": source.estimated_value - mean,
                        "deviation_percentage": ((source.estimated_value - mean) / mean) * 100
                    })
        
        return {
            "outliers": outliers,
            "outlier_count": len(outliers),
            "analysis": f"Found {len(outliers)} outlier(s) using z-score method (threshold: {threshold})",
            "threshold_used": threshold
        }
    
    def _compare_methodologies(self, sources: List[ValuationSource]) -> Dict[str, Any]:
        """Compare valuation methodologies used by different sources."""
        methodology_analysis = {}
        
        for source in sources:
            method = source.methodology
            if method not in methodology_analysis:
                methodology_analysis[method] = {
                    "sources": [],
                    "values": [],
                    "average_confidence": 0,
                    "description": self._get_methodology_description(method)
                }
            
            methodology_analysis[method]["sources"].append(source.name)
            methodology_analysis[method]["values"].append(source.estimated_value)
        
        # Calculate statistics for each methodology
        for method, data in methodology_analysis.items():
            values = data["values"]
            data["count"] = len(values)
            data["average_value"] = sum(values) / len(values)
            data["value_range"] = {"min": min(values), "max": max(values)}
            
            # Get confidence scores for sources using this methodology
            method_sources = [s for s in sources if s.methodology == method]
            data["average_confidence"] = sum(s.confidence_score for s in method_sources) / len(method_sources)
        
        return {
            "methodology_breakdown": methodology_analysis,
            "unique_methodologies": len(methodology_analysis),
            "most_common_method": max(methodology_analysis.keys(), key=lambda k: methodology_analysis[k]["count"]),
            "methodology_diversity": len(methodology_analysis) / len(sources) if sources else 0
        }
    
    def _get_methodology_description(self, methodology: str) -> str:
        """Get description for valuation methodology."""
        descriptions = {
            "avm": "Automated Valuation Model - Uses algorithms and statistical models",
            "market_comparison": "Market Comparison - Based on recent comparable sales",
            "desktop": "Desktop Valuation - Professional analysis without site inspection",
            "professional": "Professional Valuation - Full inspection and analysis",
            "income_approach": "Income Approach - Based on rental income potential",
            "cost_approach": "Cost Approach - Based on replacement cost",
            "unknown": "Unknown methodology"
        }
        return descriptions.get(methodology.lower(), f"Unknown methodology: {methodology}")
    
    def _analyze_confidence_levels(self, sources: List[ValuationSource]) -> Dict[str, Any]:
        """Analyze confidence levels across all sources."""
        confidences = [s.confidence_score for s in sources]
        
        if not confidences:
            return {}
        
        # Categorize confidence levels
        high_confidence = [s for s in sources if s.confidence_score >= 0.8]
        medium_confidence = [s for s in sources if 0.6 <= s.confidence_score < 0.8]
        low_confidence = [s for s in sources if s.confidence_score < 0.6]
        
        return {
            "average_confidence": sum(confidences) / len(confidences),
            "confidence_distribution": {
                "high": len(high_confidence),
                "medium": len(medium_confidence),
                "low": len(low_confidence)
            },
            "highest_confidence_source": max(sources, key=lambda s: s.confidence_score).name,
            "lowest_confidence_source": min(sources, key=lambda s: s.confidence_score).name,
            "confidence_variance": self._calculate_std_dev(confidences),
            "sources_by_confidence": {
                "high": [s.name for s in high_confidence],
                "medium": [s.name for s in medium_confidence],
                "low": [s.name for s in low_confidence]
            }
        }
    
    def _generate_recommendations(self, sources: List[ValuationSource]) -> List[str]:
        """Generate recommendations based on valuation comparison."""
        recommendations = []
        
        # Variance-based recommendations
        variance_analysis = self._analyze_variance(sources)
        variance_level = variance_analysis["variance_level"]
        
        if variance_level == VarianceLevel.VERY_HIGH:
            recommendations.append("High variance detected - recommend obtaining additional valuations for verification")
        elif variance_level == VarianceLevel.HIGH:
            recommendations.append("Significant variance between sources - investigate methodology differences")
        
        # Confidence-based recommendations
        confidence_analysis = self._analyze_confidence_levels(sources)
        avg_confidence = confidence_analysis.get("average_confidence", 0)
        
        if avg_confidence < 0.6:
            recommendations.append("Low average confidence across sources - consider more detailed property analysis")
        
        # Source count recommendations
        if len(sources) < 2:
            recommendations.append("Single valuation source - strongly recommend obtaining additional opinions")
        elif len(sources) == 2:
            recommendations.append("Consider obtaining a third valuation opinion for better consensus")
        
        # Outlier recommendations
        outlier_analysis = self._identify_outliers(sources)
        if outlier_analysis.get("outlier_count", 0) > 0:
            recommendations.append("Outlier valuations detected - review methodology and property details")
        
        # Methodology recommendations
        methodology_analysis = self._compare_methodologies(sources)
        if methodology_analysis.get("methodology_diversity", 0) < 0.5:
            recommendations.append("Limited methodology diversity - consider different valuation approaches")
        
        return recommendations
    
    def _assess_valuation_risk(self, sources: List[ValuationSource]) -> Dict[str, Any]:
        """Assess risk associated with the valuations."""
        risk_factors = []
        risk_score = 0.0
        
        # Variance risk
        variance_analysis = self._analyze_variance(sources)
        variance_level = variance_analysis["variance_level"]
        
        if variance_level == VarianceLevel.VERY_HIGH:
            risk_factors.append("Very high variance between valuations")
            risk_score += 0.4
        elif variance_level == VarianceLevel.HIGH:
            risk_factors.append("High variance between valuations")
            risk_score += 0.25
        
        # Confidence risk
        confidence_analysis = self._analyze_confidence_levels(sources)
        avg_confidence = confidence_analysis.get("average_confidence", 0)
        
        if avg_confidence < 0.5:
            risk_factors.append("Low average confidence across sources")
            risk_score += 0.3
        elif avg_confidence < 0.7:
            risk_factors.append("Medium confidence levels")
            risk_score += 0.15
        
        # Source diversity risk
        if len(sources) < 2:
            risk_factors.append("Single valuation source")
            risk_score += 0.3
        
        # Methodology diversity risk
        methodology_analysis = self._compare_methodologies(sources)
        if methodology_analysis.get("unique_methodologies", 0) == 1:
            risk_factors.append("Single methodology used")
            risk_score += 0.2
        
        # Determine overall risk level
        if risk_score > 0.7:
            risk_level = "high"
        elif risk_score > 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "risk_level": risk_level,
            "risk_score": min(1.0, risk_score),
            "risk_factors": risk_factors,
            "mitigation_suggestions": self._suggest_risk_mitigation(risk_factors)
        }
    
    def _suggest_risk_mitigation(self, risk_factors: List[str]) -> List[str]:
        """Suggest risk mitigation strategies."""
        suggestions = []
        
        if "Very high variance between valuations" in risk_factors:
            suggestions.append("Obtain additional professional valuations to resolve discrepancies")
        
        if "Low average confidence across sources" in risk_factors:
            suggestions.append("Request detailed property inspections and market analysis")
        
        if "Single valuation source" in risk_factors:
            suggestions.append("Obtain at least one additional independent valuation")
        
        if "Single methodology used" in risk_factors:
            suggestions.append("Request valuations using different approaches (e.g., market comparison, income approach)")
        
        return suggestions
    
    def _provide_market_context(self, sources: List[ValuationSource], options: Dict[str, Any]) -> Dict[str, Any]:
        """Provide market context for the valuations."""
        # This would typically integrate with market data
        # For now, provide basic context analysis
        
        context = {
            "valuation_date_range": {
                "earliest": min(s.valuation_date for s in sources).isoformat(),
                "latest": max(s.valuation_date for s in sources).isoformat()
            },
            "temporal_analysis": "All valuations within acceptable timeframe" if self._check_temporal_consistency(sources) else "Valuations span significant time period",
            "market_segment": self._determine_market_segment(sources)
        }
        
        return context
    
    def _check_temporal_consistency(self, sources: List[ValuationSource]) -> bool:
        """Check if valuations are temporally consistent."""
        dates = [s.valuation_date for s in sources]
        if len(dates) < 2:
            return True
        
        date_range = (max(dates) - min(dates)).days
        return date_range <= 90  # Within 3 months
    
    def _determine_market_segment(self, sources: List[ValuationSource]) -> str:
        """Determine market segment based on valuation amounts."""
        values = [s.estimated_value for s in sources]
        avg_value = sum(values) / len(values)
        
        if avg_value > 2000000:
            return "luxury"
        elif avg_value > 1000000:
            return "premium"
        elif avg_value > 500000:
            return "mid_market"
        else:
            return "entry_level"
    
    def _calculate_quality_scores(self, sources: List[ValuationSource]) -> Dict[str, Any]:
        """Calculate quality scores for the overall comparison."""
        # Data quality score
        data_quality = 0.0
        
        # Source diversity (max 0.3)
        if len(sources) >= 3:
            data_quality += 0.3
        elif len(sources) == 2:
            data_quality += 0.2
        else:
            data_quality += 0.1
        
        # Average confidence (max 0.3)
        avg_confidence = sum(s.confidence_score for s in sources) / len(sources)
        data_quality += avg_confidence * 0.3
        
        # Methodology diversity (max 0.2)
        unique_methods = len(set(s.methodology for s in sources))
        methodology_diversity = min(1.0, unique_methods / len(sources))
        data_quality += methodology_diversity * 0.2
        
        # Comparable count (max 0.2)
        avg_comparables = sum(s.comparable_count for s in sources) / len(sources)
        comparable_score = min(1.0, avg_comparables / 10)  # Normalize to 10 comparables
        data_quality += comparable_score * 0.2
        
        return {
            "overall_quality": min(1.0, data_quality),
            "data_completeness": len(sources) / 3,  # Normalize to 3 sources
            "confidence_quality": avg_confidence,
            "methodology_diversity": methodology_diversity,
            "comparable_adequacy": comparable_score
        }