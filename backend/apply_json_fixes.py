#!/usr/bin/env python3
"""
Script to apply targeted JSON parsing fixes to contract_workflow.py
This addresses the "Invalid JSON. Error: Expecting value: line 1 column 1" issues
"""

import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def apply_json_fixes():
    """Apply all the JSON parsing fixes to contract_workflow.py"""
    
    workflow_path = "app/agents/contract_workflow.py"
    
    with open(workflow_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Fix 1: Replace direct json.loads() calls with structured parsing
    replacements = [
        # Compliance analysis methods
        {
            "pattern": r"compliance_result = json\.loads\(llm_response\)",
            "replacement": "compliance_result, success, error_msg = self._parse_structured_response(llm_response, 'compliance_analysis')\n                if not success:\n                    logger.warning(f'Compliance analysis parsing failed: {error_msg}')\n                    compliance_result = self._create_fallback_compliance_result()"
        },
        
        # Risk analysis methods
        {
            "pattern": r"risk_result = json\.loads\(llm_response\)",
            "replacement": "risk_result, success, error_msg = self._parse_structured_response(llm_response, 'risk_analysis')\n                if not success:\n                    logger.warning(f'Risk analysis parsing failed: {error_msg}')\n                    risk_result = self._create_fallback_risk_result()"
        },
        
        # Recommendations methods
        {
            "pattern": r"recommendations_result = json\.loads\(llm_response\)",
            "replacement": "recommendations_result, success, error_msg = self._parse_structured_response(llm_response, 'recommendations')\n                if not success:\n                    logger.warning(f'Recommendations parsing failed: {error_msg}')\n                    recommendations_result = {'recommendations': self._create_fallback_recommendations()}"
        },
        
        # Quality assessment methods
        {
            "pattern": r"quality_result = json\.loads\(llm_response\)",
            "replacement": "quality_result, success, error_msg = self._parse_structured_response(llm_response, 'document_quality')\n                if not success:\n                    logger.warning(f'Quality assessment parsing failed: {error_msg}')\n                    quality_result = self._create_fallback_quality_result()"
        },
        
        # Validation methods
        {
            "pattern": r"validation_result = json\.loads\(llm_response\)",
            "replacement": "validation_result, success, error_msg = self._parse_structured_response(llm_response, 'terms_validation')\n                if not success:\n                    logger.warning(f'Terms validation parsing failed: {error_msg}')\n                    validation_result = self._create_fallback_validation_result()"
        },
        
        # Contract extraction method
        {
            "pattern": r"extraction_result = json\.loads\(llm_response\)",
            "replacement": "extraction_result, success, error_msg = self._parse_structured_response(llm_response, 'contract_terms')\n                    if not success:\n                        logger.warning(f'Contract extraction parsing failed: {error_msg}')\n                        raise ValueError(f'Contract extraction failed: {error_msg}')"
        }
    ]
    
    # Apply replacements
    for replacement in replacements:
        pattern = replacement["pattern"]
        new_code = replacement["replacement"]
        
        if re.search(pattern, content):
            content = re.sub(pattern, new_code, content)
            logger.info(f"Applied fix: {pattern}")
        else:
            logger.warning(f"Pattern not found: {pattern}")
    
    # Add fallback methods if they don't exist
    fallback_methods = """
    def _create_fallback_compliance_result(self) -> Dict[str, Any]:
        '''Fallback compliance result when parsing fails'''
        return {
            "overall_compliance_score": 5,
            "state_compliance": False,
            "compliance_issues": [
                {
                    "area": "analysis",
                    "issue": "Unable to complete automated compliance analysis",
                    "severity": "medium",
                    "recommendation": "Manual legal review required"
                }
            ],
            "mandatory_disclosures": [],
            "cooling_off_period": {"applicable": None, "period_days": None}
        }
    
    def _create_fallback_risk_result(self) -> Dict[str, Any]:
        '''Fallback risk result when parsing fails'''
        return {
            "overall_risk_score": 5,
            "risk_factors": [
                {
                    "factor": "Parsing Error",
                    "severity": "medium",
                    "description": "Unable to perform complete risk analysis due to parsing issues",
                    "mitigation_suggestions": ["Manual review required", "Re-analyze with updated system"]
                }
            ],
            "critical_issues": [],
            "recommendations": ["Manual review of contract recommended"],
            "confidence_score": 0.3
        }
    
    def _create_fallback_quality_result(self) -> Dict[str, Any]:
        '''Fallback quality result when parsing fails'''
        return {
            "overall_quality_score": 0.5,
            "quality_issues": ["Automated quality assessment failed"],
            "recommendations": ["Manual quality review required"],
            "processing_notes": ["Parsing error occurred during analysis"]
        }
    
    def _create_fallback_validation_result(self) -> Dict[str, Any]:
        '''Fallback validation result when parsing fails'''
        return {
            "terms_validated": {},
            "missing_mandatory_terms": ["Unable to validate"],
            "validation_confidence": 0.2,
            "recommendations": ["Manual validation required"]
        }
    
    def _create_fallback_recommendations(self) -> List[Dict[str, Any]]:
        '''Fallback recommendations when parsing fails'''
        return [
            {
                "category": "system",
                "priority": "high", 
                "title": "Manual Review Required",
                "description": "Automated analysis was incomplete. Manual legal review recommended.",
                "action_items": ["Contact legal professional", "Review contract manually"],
                "timeline": "immediate",
                "cost_impact": "medium"
            }
        ]
"""
    
    # Check if fallback methods already exist
    if "_create_fallback_compliance_result" not in content:
        # Find a good place to insert the fallback methods (before the last class method)
        insertion_point = content.rfind("    def _create_workflow")
        if insertion_point != -1:
            content = content[:insertion_point] + fallback_methods + "\n" + content[insertion_point:]
            logger.info("Added fallback methods")
    
    # Save the modified content
    if content != original_content:
        with open(workflow_path, 'w') as f:
            f.write(content)
        logger.info("Applied JSON parsing fixes to contract_workflow.py")
        return True
    else:
        logger.warning("No changes were made")
        return False


if __name__ == "__main__":
    try:
        success = apply_json_fixes()
        if success:
            print("✅ Successfully applied JSON parsing fixes!")
            print("\n🔧 Fixed Issues:")
            print("- Invalid JSON parsing errors (line 1 column 1)")
            print("- Response quality monitoring failures")
            print("- Code block wrapped JSON responses")
            print("- Added comprehensive fallback methods")
            print("\n📝 Next Steps:")
            print("1. Test the contract analysis pipeline")
            print("2. Verify no more JSON parsing errors occur")
            print("3. Check that structured parsing is working correctly")
        else:
            print("❌ No fixes were applied - check the patterns")
    except Exception as e:
        print(f"❌ Error applying fixes: {e}")
        import traceback
        traceback.print_exc()