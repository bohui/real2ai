"""
LangGraph Contract Analysis Workflow for Real2.AI
"""

from typing import Dict, Any, Optional, List
from langgraph.graph import StateGraph
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import json
import time
from datetime import datetime

from app.models.contract_state import (
    RealEstateAgentState, 
    ProcessingStatus, 
    ContractTerms,
    RiskFactor,
    ComplianceCheck,
    update_state_step,
    calculate_confidence_score
)
from app.agents.australian_tools import (
    extract_australian_contract_terms,
    validate_cooling_off_period,
    calculate_stamp_duty,
    analyze_special_conditions
)


class ContractAnalysisWorkflow:
    """LangGraph workflow for Australian contract analysis"""
    
    def __init__(self, openai_api_key: str, model_name: str = "gpt-4", openai_api_base: Optional[str] = None):
        self.llm = ChatOpenAI(
            openai_api_key=openai_api_key,
            model_name=model_name,
            temperature=0.1,  # Low temperature for consistent analysis
            openai_api_base=openai_api_base
        )
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow"""
        
        workflow = StateGraph(RealEstateAgentState)
        
        # Core Processing Nodes
        workflow.add_node("validate_input", self.validate_input)
        workflow.add_node("process_document", self.process_document)
        workflow.add_node("extract_terms", self.extract_contract_terms)
        workflow.add_node("analyze_compliance", self.analyze_australian_compliance)
        workflow.add_node("assess_risks", self.assess_contract_risks)
        workflow.add_node("generate_recommendations", self.generate_recommendations)
        workflow.add_node("compile_report", self.compile_analysis_report)
        
        # Error Handling Nodes
        workflow.add_node("handle_error", self.handle_processing_error)
        workflow.add_node("retry_processing", self.retry_failed_step)
        
        # Entry Point
        workflow.set_entry_point("validate_input")
        
        # Linear Processing Flow
        workflow.add_edge("validate_input", "process_document")
        workflow.add_edge("process_document", "extract_terms")
        workflow.add_edge("extract_terms", "analyze_compliance")
        workflow.add_edge("analyze_compliance", "assess_risks")
        workflow.add_edge("assess_risks", "generate_recommendations")
        workflow.add_edge("generate_recommendations", "compile_report")
        
        # Conditional Error Handling
        workflow.add_conditional_edges(
            "process_document",
            self.check_processing_success,
            {
                "success": "extract_terms",
                "retry": "retry_processing",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "extract_terms",
            self.check_extraction_quality,
            {
                "high_confidence": "analyze_compliance",
                "low_confidence": "retry_processing",
                "error": "handle_error"
            }
        )
        
        # Terminal Conditions
        workflow.add_edge("compile_report", "__end__")
        workflow.add_edge("handle_error", "__end__")
        
        return workflow.compile()
    
    async def analyze_contract(self, initial_state: RealEstateAgentState) -> RealEstateAgentState:
        """Execute the complete contract analysis workflow"""
        
        start_time = time.time()
        
        try:
            # Run the workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            final_state["processing_time"] = processing_time
            
            # Calculate overall confidence
            final_state["analysis_results"]["overall_confidence"] = calculate_confidence_score(final_state)
            
            return final_state
            
        except Exception as e:
            # Handle workflow-level errors
            error_state = update_state_step(
                initial_state, 
                "workflow_error", 
                error=f"Workflow execution failed: {str(e)}"
            )
            error_state["processing_time"] = time.time() - start_time
            return error_state
    
    def validate_input(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """Validate document and user input"""
        
        if not state.get("document_data"):
            return update_state_step(state, "validation_failed", error="No document provided")
        
        if not state.get("australian_state"):
            return update_state_step(state, "validation_failed", error="Australian state not specified")
        
        # Validate document format
        document_data = state["document_data"]
        if not document_data.get("content") and not document_data.get("file_path"):
            return update_state_step(state, "validation_failed", error="Document content not accessible")
        
        return update_state_step(state, "input_validated")
    
    def process_document(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """Process document and extract text content"""
        
        try:
            document_data = state["document_data"]
            
            # Use actual extracted text if available
            if document_data.get("content"):
                extracted_text = document_data["content"]
                extraction_method = "pre_processed"
                extraction_confidence = 0.95
            else:
                # Fallback to simulation if no content available
                extracted_text = self._simulate_document_extraction(document_data)
                extraction_method = "simulation"
                extraction_confidence = 0.7
            
            # Validate extracted text quality
            if not extracted_text or len(extracted_text.strip()) < 100:
                return update_state_step(
                    state,
                    "document_processing_failed",
                    error="Insufficient text content extracted from document"
                )
            
            # Calculate text quality metrics
            text_quality = self._assess_text_quality(extracted_text)
            
            # Update state with extracted text
            updated_data = {
                "document_metadata": {
                    "extracted_text": extracted_text,
                    "extraction_method": extraction_method,
                    "extraction_confidence": extraction_confidence,
                    "text_quality": text_quality,
                    "character_count": len(extracted_text),
                    "word_count": len(extracted_text.split()),
                    "processing_timestamp": datetime.utcnow().isoformat()
                },
                "parsing_status": ProcessingStatus.COMPLETED
            }
            
            return update_state_step(state, "document_processed", data=updated_data)
            
        except Exception as e:
            return update_state_step(
                state, 
                "document_processing_failed", 
                error=f"Document processing failed: {str(e)}"
            )
    
    def extract_contract_terms(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """Extract key contract terms using Australian-specific tools"""
        
        try:
            document_text = state["document_metadata"]["extracted_text"]
            australian_state = state["australian_state"]
            
            # Use the Australian contract tools
            extraction_result = extract_australian_contract_terms.invoke({
                "document_text": document_text,
                "state": australian_state
            })
            
            # Store results in state
            updated_data = {
                "contract_terms": extraction_result["terms"],
                "confidence_scores": {
                    "term_extraction": extraction_result["overall_confidence"]
                }
            }
            
            return update_state_step(state, "terms_extracted", data=updated_data)
            
        except Exception as e:
            return update_state_step(
                state,
                "term_extraction_failed",
                error=f"Term extraction failed: {str(e)}"
            )
    
    def analyze_australian_compliance(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """Analyze compliance with Australian property laws"""
        
        try:
            contract_terms = state["contract_terms"]
            australian_state = state["australian_state"]
            
            # Validate cooling-off period
            cooling_off_result = validate_cooling_off_period.invoke({
                "contract_terms": contract_terms,
                "state": australian_state
            })
            
            # Calculate stamp duty
            purchase_price = contract_terms.get("purchase_price", 0)
            if purchase_price > 0:
                stamp_duty_result = calculate_stamp_duty.invoke({
                    "purchase_price": purchase_price,
                    "state": australian_state,
                    "is_first_home": state["user_preferences"].get("is_first_home_buyer", False),
                    "is_foreign_buyer": state["user_preferences"].get("is_foreign_buyer", False)
                })
            else:
                stamp_duty_result = None
            
            # Analyze special conditions
            special_conditions_result = analyze_special_conditions.invoke({
                "contract_terms": contract_terms,
                "state": australian_state
            })
            
            # Compile compliance check
            compliance_check = {
                "state_compliance": cooling_off_result.get("compliant", False),
                "cooling_off_validation": cooling_off_result,
                "stamp_duty_calculation": stamp_duty_result,
                "special_conditions_analysis": special_conditions_result,
                "compliance_issues": [],
                "warnings": cooling_off_result.get("warnings", [])
            }
            
            # Add compliance issues
            if not cooling_off_result.get("compliant", False):
                compliance_check["compliance_issues"].append("Cooling-off period non-compliant")
            
            updated_data = {
                "compliance_check": compliance_check,
                "confidence_scores": {
                    **state.get("confidence_scores", {}),
                    "compliance_check": 0.9  # High confidence in rule-based analysis
                }
            }
            
            return update_state_step(state, "compliance_analyzed", data=updated_data)
            
        except Exception as e:
            return update_state_step(
                state,
                "compliance_analysis_failed",
                error=f"Compliance analysis failed: {str(e)}"
            )
    
    def assess_contract_risks(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """Assess contract risks using LLM analysis"""
        
        try:
            contract_terms = state["contract_terms"]
            compliance_check = state["compliance_check"]
            
            # Create risk assessment prompt
            risk_prompt = self._create_risk_assessment_prompt(
                contract_terms, 
                compliance_check, 
                state["australian_state"]
            )
            
            # Get LLM risk analysis
            messages = [
                SystemMessage(content="You are an expert Australian property lawyer analyzing contract risks."),
                HumanMessage(content=risk_prompt)
            ]
            
            llm_response = self.llm(messages)
            risk_analysis = self._parse_risk_analysis(llm_response.content)
            
            updated_data = {
                "risk_assessment": risk_analysis,
                "confidence_scores": {
                    **state.get("confidence_scores", {}),
                    "risk_assessment": 0.85  # Good confidence in LLM analysis
                }
            }
            
            return update_state_step(state, "risks_assessed", data=updated_data)
            
        except Exception as e:
            return update_state_step(
                state,
                "risk_assessment_failed",
                error=f"Risk assessment failed: {str(e)}"
            )
    
    def generate_recommendations(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """Generate actionable recommendations"""
        
        try:
            # Create recommendations prompt
            recommendations_prompt = self._create_recommendations_prompt(state)
            
            messages = [
                SystemMessage(content="You are an expert Australian property advisor providing actionable recommendations."),
                HumanMessage(content=recommendations_prompt)
            ]
            
            llm_response = self.llm(messages)
            recommendations = self._parse_recommendations(llm_response.content)
            
            updated_data = {
                "final_recommendations": recommendations,
                "recommendations": recommendations  # For backwards compatibility
            }
            
            return update_state_step(state, "recommendations_generated", data=updated_data)
            
        except Exception as e:
            return update_state_step(
                state,
                "recommendation_generation_failed",
                error=f"Recommendation generation failed: {str(e)}"
            )
    
    def compile_analysis_report(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """Compile the final analysis report"""
        
        try:
            # Compile all analysis results
            analysis_results = {
                "contract_id": state.get("session_id"),
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "user_id": state["user_id"],
                "australian_state": state["australian_state"],
                "contract_terms": state.get("contract_terms", {}),
                "risk_assessment": state.get("risk_assessment", {}),
                "compliance_check": state.get("compliance_check", {}),
                "recommendations": state.get("final_recommendations", []),
                "confidence_scores": state.get("confidence_scores", {}),
                "overall_confidence": calculate_confidence_score(state),
                "processing_summary": {
                    "steps_completed": state["current_step"],
                    "processing_time": state.get("processing_time"),
                    "analysis_version": state["agent_version"]
                }
            }
            
            updated_data = {
                "analysis_results": analysis_results,
                "report_data": self._create_report_summary(analysis_results),
                "parsing_status": ProcessingStatus.COMPLETED
            }
            
            return update_state_step(state, "report_compiled", data=updated_data)
            
        except Exception as e:
            return update_state_step(
                state,
                "report_compilation_failed",
                error=f"Report compilation failed: {str(e)}"
            )
    
    def handle_processing_error(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """Handle processing errors"""
        
        error_message = state.get("error_state", "Unknown error occurred")
        
        # Log error details
        error_details = {
            "error_message": error_message,
            "failed_step": state["current_step"],
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": state["session_id"]
        }
        
        updated_data = {
            "analysis_results": {
                "error_details": error_details,
                "status": "failed"
            },
            "parsing_status": ProcessingStatus.FAILED
        }
        
        return update_state_step(state, "error_handled", data=updated_data)
    
    def retry_failed_step(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """Retry a failed processing step"""
        
        # Simple retry logic - in production would implement more sophisticated retry
        retry_count = state.get("retry_count", 0)
        
        if retry_count >= 2:  # Max 2 retries
            return self.handle_processing_error(state)
        
        updated_data = {"retry_count": retry_count + 1}
        return update_state_step(state, "retrying", data=updated_data)
    
    # Conditional edge functions
    
    def check_processing_success(self, state: RealEstateAgentState) -> str:
        """Check if document processing was successful"""
        
        if state.get("error_state"):
            return "error"
        
        if state.get("parsing_status") == ProcessingStatus.COMPLETED:
            return "success"
        
        retry_count = state.get("retry_count", 0)
        return "retry" if retry_count < 2 else "error"
    
    def check_extraction_quality(self, state: RealEstateAgentState) -> str:
        """Check quality of term extraction"""
        
        if state.get("error_state"):
            return "error"
        
        confidence_scores = state.get("confidence_scores", {})
        extraction_confidence = confidence_scores.get("term_extraction", 0.0)
        
        if extraction_confidence >= 0.7:
            return "high_confidence"
        elif extraction_confidence >= 0.4:
            return "low_confidence"
        else:
            return "error"
    
    # Helper methods
    
    def _simulate_document_extraction(self, document_data: Dict[str, Any]) -> str:
        """Simulate document text extraction"""
        # In production, this would use actual OCR/document processing
        return """
        SALE OF LAND CONTRACT
        
        VENDOR: John Smith
        PURCHASER: Jane Doe
        
        PROPERTY: 123 Collins Street, Melbourne VIC 3000
        
        PURCHASE PRICE: $850,000
        DEPOSIT: $85,000 (10%)
        SETTLEMENT DATE: 45 days from exchange
        
        COOLING OFF PERIOD: 3 business days
        
        SPECIAL CONDITIONS:
        1. Subject to finance approval within 21 days
        2. Subject to satisfactory building and pest inspection
        3. Subject to strata search and review of strata documents
        
        This contract is governed by Victorian law.
        """
    
    def _create_risk_assessment_prompt(self, contract_terms: Dict, compliance_check: Dict, state: str) -> str:
        """Create prompt for LLM risk assessment"""
        
        return f"""
        Analyze the following Australian property contract for risks and issues:
        
        CONTRACT TERMS:
        {json.dumps(contract_terms, indent=2)}
        
        COMPLIANCE STATUS:
        {json.dumps(compliance_check, indent=2)}
        
        STATE: {state}
        
        Please provide a comprehensive risk assessment including:
        1. Overall risk score (0-10, where 10 is highest risk)
        2. Specific risk factors with severity levels
        3. Potential financial impacts
        4. Legal compliance issues
        
        Format response as JSON with the following structure:
        {{
            "overall_risk_score": <number>,
            "risk_factors": [
                {{
                    "factor": "<description>",
                    "severity": "<low|medium|high|critical>",
                    "description": "<detailed explanation>",
                    "impact": "<potential consequences>",
                    "australian_specific": <boolean>
                }}
            ]
        }}
        """
    
    def _create_recommendations_prompt(self, state: RealEstateAgentState) -> str:
        """Create prompt for recommendations"""
        
        return f"""
        Based on this contract analysis, provide specific actionable recommendations:
        
        ANALYSIS SUMMARY:
        - Risk Assessment: {json.dumps(state.get("risk_assessment", {}), indent=2)}
        - Compliance Issues: {json.dumps(state.get("compliance_check", {}), indent=2)}
        - Australian State: {state["australian_state"]}
        - User Type: {state["user_type"]}
        
        Provide recommendations in JSON format:
        {{
            "recommendations": [
                {{
                    "priority": "<low|medium|high|critical>",
                    "category": "<legal|financial|practical>",
                    "recommendation": "<specific action>",
                    "action_required": <boolean>,
                    "australian_context": "<state-specific notes>",
                    "estimated_cost": <number or null>
                }}
            ]
        }}
        """
    
    def _parse_risk_analysis(self, llm_response: str) -> Dict[str, Any]:
        """Parse LLM risk analysis response"""
        try:
            return json.loads(llm_response)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "overall_risk_score": 5.0,
                "risk_factors": [
                    {
                        "factor": "Unable to parse detailed risk analysis",
                        "severity": "medium",
                        "description": "LLM response could not be parsed",
                        "impact": "Manual review recommended",
                        "australian_specific": False
                    }
                ]
            }
    
    def _parse_recommendations(self, llm_response: str) -> List[Dict[str, Any]]:
        """Parse LLM recommendations response"""
        try:
            parsed = json.loads(llm_response)
            return parsed.get("recommendations", [])
        except json.JSONDecodeError:
            # Fallback recommendations
            return [
                {
                    "priority": "high",
                    "category": "legal",
                    "recommendation": "Seek professional legal advice due to analysis parsing issues",
                    "action_required": True,
                    "australian_context": "Consult qualified property lawyer",
                    "estimated_cost": 500.0
                }
            ]
    
    def _assess_text_quality(self, text: str) -> Dict[str, Any]:
        """Assess quality of extracted text"""
        
        if not text:
            return {"score": 0.0, "issues": ["No text content"]}
        
        # Calculate quality metrics
        words = text.split()
        total_chars = len(text)
        total_words = len(words)
        
        issues = []
        score = 1.0
        
        # Check for minimum content
        if total_chars < 200:
            issues.append("Very short document")
            score *= 0.5
        
        if total_words < 50:
            issues.append("Too few words extracted")
            score *= 0.5
        
        # Check for garbled text
        if words:
            single_char_words = sum(1 for word in words if len(word) == 1)
            single_char_ratio = single_char_words / total_words
            
            if single_char_ratio > 0.3:
                issues.append("High ratio of single characters (poor OCR)")
                score *= 0.6
        
        # Check for contract-relevant keywords
        contract_keywords = [
            "contract", "agreement", "purchase", "sale", "property",
            "vendor", "purchaser", "settlement", "deposit", "price"
        ]
        text_lower = text.lower()
        found_keywords = sum(1 for keyword in contract_keywords if keyword in text_lower)
        
        if found_keywords < 3:
            issues.append("Few contract-relevant keywords found")
            score *= 0.8
        else:
            score = min(1.0, score + (found_keywords - 3) * 0.05)
        
        return {
            "score": max(0.0, min(1.0, score)),
            "issues": issues,
            "character_count": total_chars,
            "word_count": total_words,
            "contract_keywords_found": found_keywords
        }
    
    def _create_report_summary(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary report for display"""
        
        risk_assessment = analysis_results.get("risk_assessment", {})
        compliance_check = analysis_results.get("compliance_check", {})
        recommendations = analysis_results.get("recommendations", [])
        
        return {
            "executive_summary": {
                "overall_risk_score": risk_assessment.get("overall_risk_score", 0),
                "compliance_status": "compliant" if compliance_check.get("state_compliance", False) else "non-compliant",
                "total_recommendations": len(recommendations),
                "critical_issues": len([r for r in recommendations if r.get("priority") == "critical"]),
                "confidence_level": analysis_results.get("overall_confidence", 0)
            },
            "key_findings": {
                "highest_risks": [rf for rf in risk_assessment.get("risk_factors", []) if rf.get("severity") in ["high", "critical"]][:3],
                "compliance_issues": compliance_check.get("compliance_issues", []),
                "immediate_actions": [r for r in recommendations if r.get("action_required", False)][:5]
            },
            "financial_summary": {
                "stamp_duty": compliance_check.get("stamp_duty_calculation", {}),
                "estimated_costs": sum(r.get("estimated_cost", 0) or 0 for r in recommendations)
            }
        }