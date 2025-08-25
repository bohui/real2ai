"""
Confidence scoring tools for workflow analysis
"""

from typing import Dict, Any, Optional
from langchain.tools import tool


@tool
def calculate_overall_confidence_score(
    confidence_scores: Dict[str, float],
    step_weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Calculate overall confidence score for contract analysis workflow
    
    Args:
        confidence_scores: Dictionary of step-wise confidence scores
        step_weights: Optional weights for different steps
        
    Returns:
        Dictionary containing overall confidence metrics
    """
    
    if not confidence_scores:
        return {
            "overall_confidence": 0.0,
            "confidence_level": "unknown",
            "recommendation": "No confidence data available",
            "breakdown": {}
        }
    
    # Default step weights if not provided
    if step_weights is None:
        step_weights = {
            "input_validation": 0.05,
            "document_processing": 0.15,
            "term_extraction": 0.25,
            "compliance_check": 0.20,
            "risk_assessment": 0.20,
            "recommendations": 0.15
        }
    
    # Calculate weighted average
    total_weighted_score = 0.0
    total_weight = 0.0
    breakdown = {}
    
    for step, score in confidence_scores.items():
        weight = step_weights.get(step, 0.1)  # Default weight for unknown steps
        weighted_score = score * weight
        total_weighted_score += weighted_score
        total_weight += weight
        
        breakdown[step] = {
            "score": score,
            "weight": weight,
            "weighted_contribution": weighted_score
        }
    
    # Calculate overall confidence
    overall_confidence = total_weighted_score / total_weight if total_weight > 0 else 0.0
    
    # Determine confidence level
    confidence_level = _get_confidence_level(overall_confidence)
    
    # Generate recommendation
    recommendation = _get_confidence_recommendation(overall_confidence)
    
    # Identify weak areas
    weak_areas = [
        step for step, score in confidence_scores.items() 
        if score < 0.6
    ]
    
    return {
        "overall_confidence": round(overall_confidence, 3),
        "confidence_level": confidence_level,
        "recommendation": recommendation,
        "breakdown": breakdown,
        "weak_areas": weak_areas,
        "total_steps_analyzed": len(confidence_scores),
        "minimum_step_confidence": min(confidence_scores.values()) if confidence_scores else 0.0,
        "maximum_step_confidence": max(confidence_scores.values()) if confidence_scores else 0.0,
        "confidence_range": max(confidence_scores.values()) - min(confidence_scores.values()) if confidence_scores else 0.0
    }


def _get_confidence_level(confidence: float) -> str:
    """Get confidence level description"""
    if confidence >= 0.9:
        return "very_high"
    elif confidence >= 0.8:
        return "high"
    elif confidence >= 0.7:
        return "good"
    elif confidence >= 0.6:
        return "moderate"
    elif confidence >= 0.4:
        return "low"
    else:
        return "very_low"


def _get_confidence_recommendation(confidence: float) -> str:
    """Get recommendation based on confidence level"""
    if confidence >= 0.9:
        return "Analysis results are highly reliable. Proceed with confidence."
    elif confidence >= 0.8:
        return "Analysis results are reliable. Minor review recommended."
    elif confidence >= 0.7:
        return "Analysis results are generally good. Review key findings."
    elif confidence >= 0.6:
        return "Analysis results are moderate. Professional review recommended."
    elif confidence >= 0.4:
        return "Analysis results have low confidence. Professional legal advice strongly recommended."
    else:
        return "Analysis results have very low confidence. Manual review and professional legal advice required."