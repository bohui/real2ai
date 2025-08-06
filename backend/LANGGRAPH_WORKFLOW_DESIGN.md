# LangGraph Workflow Design for ContractAnalysisService

## Overview

This document outlines the enhanced LangGraph workflow integration for Real2.AI's ContractAnalysisService (Tier 2). The workflow performs sophisticated contract analysis using structured entity extraction, page-specific diagram analysis, and comprehensive compliance checking.

## Workflow Architecture

### **State Management**
```python
from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph
from pydantic import BaseModel

class ContractAnalysisState(TypedDict):
    # Input data
    document_id: str
    document_data: Dict[str, Any]  # From DocumentService
    user_id: str
    australian_state: str
    analysis_options: Dict[str, Any]
    
    # Workflow control
    current_step: str
    progress_percentage: int
    session_id: str
    
    # Processing results
    detailed_entities: Optional[Dict[str, Any]]
    diagram_analyses: Dict[int, Dict[str, Any]]  # page_number -> analysis
    compliance_results: Optional[Dict[str, Any]]
    risk_assessment: Optional[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    
    # Quality and validation
    confidence_scores: Dict[str, float]
    validation_results: Dict[str, Any]
    processing_quality: Dict[str, Any]
    
    # Error handling
    errors: List[str]
    warnings: List[str]
    retry_count: int
    
    # WebSocket integration
    websocket_session_id: Optional[str]
    send_progress_updates: bool
```

### **Workflow Graph Structure**
```
Start → Document Validation → Entity Extraction → Diagram Analysis → Compliance Check → Risk Assessment → Recommendations → Report Generation → End

With conditional paths:
- Validation failure → Error handling
- Low confidence → Enhanced extraction
- Missing data → Data augmentation
- Critical issues → Priority alerts
```

## Workflow Nodes

### **1. Document Validation Node**
```python
async def validate_document_node(state: ContractAnalysisState) -> ContractAnalysisState:
    """
    Validate document completeness and quality for advanced analysis
    """
    # Progress: 0-10%
    await send_progress_update(state, "document_validation", 5, "Validating document data")
    
    validation_checks = {
        "document_exists": validate_document_exists(state.document_id),
        "pages_available": validate_pages_available(state.document_data),
        "text_quality": assess_text_extraction_quality(state.document_data),
        "basic_entities": validate_basic_entities(state.document_data),
        "diagrams_available": check_diagram_availability(state.document_data),
        "australian_context": validate_australian_context(state.document_data, state.australian_state)
    }
    
    state["validation_results"] = validation_checks
    state["current_step"] = "validation_complete"
    state["progress_percentage"] = 10
    
    # Determine next step based on validation
    if all(validation_checks.values()):
        state["confidence_scores"]["document_validation"] = 0.9
    else:
        state["warnings"].extend([f"Validation issue: {k}" for k, v in validation_checks.items() if not v])
        state["confidence_scores"]["document_validation"] = 0.6
    
    return state
```

### **2. Detailed Entity Extraction Node**
```python
async def extract_detailed_entities_node(state: ContractAnalysisState) -> ContractAnalysisState:
    """
    Extract detailed entities using ContractEntityExtraction schema
    """
    # Progress: 10-35%
    await send_progress_update(state, "entity_extraction", 15, "Extracting detailed contract entities")
    
    try:
        # Initialize extraction service with document context
        entity_extractor = StructuredEntityExtractor(
            australian_state=state.australian_state,
            document_context=state.document_data
        )
        
        # Extract entities page by page for better accuracy
        extracted_entities = await entity_extractor.extract_comprehensive_entities(
            document_data=state.document_data,
            basic_entities=state.document_data.get("basic_entities", []),
            context_enhancement=True
        )
        
        # Validate extraction against schema
        validated_entities = ContractEntityExtraction(**extracted_entities)
        
        state["detailed_entities"] = validated_entities.dict()
        state["confidence_scores"]["entity_extraction"] = calculate_extraction_confidence(validated_entities)
        
        await send_progress_update(state, "entity_extraction", 35, "Entity extraction completed")
        
    except Exception as e:
        state["errors"].append(f"Entity extraction failed: {str(e)}")
        state["confidence_scores"]["entity_extraction"] = 0.0
        # Continue with partial data
    
    state["current_step"] = "entity_extraction_complete"
    state["progress_percentage"] = 35
    
    return state
```

### **3. Page-Specific Diagram Analysis Node**
```python
async def analyze_diagrams_by_page_node(state: ContractAnalysisState) -> ContractAnalysisState:
    """
    Analyze diagrams page by page using vision models
    """
    # Progress: 35-55%
    await send_progress_update(state, "diagram_analysis", 40, "Analyzing diagrams with AI vision models")
    
    diagram_results = {}
    diagrams = state.document_data.get("diagrams", [])
    
    for diagram in diagrams:
        try:
            page_number = diagram["page_number"]
            
            # Get page context for better analysis
            page_data = next(
                (p for p in state.document_data.get("pages", []) if p["page_number"] == page_number), 
                None
            )
            
            # Vision analysis with context
            vision_analyzer = DiagramVisionAnalyzer(
                australian_state=state.australian_state,
                document_context=state.document_data
            )
            
            analysis_result = await vision_analyzer.analyze_diagram_with_context(
                image_path=diagram["extracted_image_path"],
                diagram_type=diagram["diagram_type"],
                page_text=page_data.get("text_content", "") if page_data else "",
                page_number=page_number
            )
            
            # Structure analysis using DiagramEntityExtraction schema
            structured_analysis = DiagramEntityExtraction(
                diagram_id=diagram["id"],
                diagram_type=diagram["diagram_type"],
                page_number=page_number,
                infrastructure_elements=analysis_result.get("infrastructure_elements", []),
                utilities=analysis_result.get("utilities", []),
                boundaries=analysis_result.get("boundaries", []),
                measurements=analysis_result.get("measurements", []),
                specifications=analysis_result.get("specifications", []),
                risk_indicators=analysis_result.get("risk_indicators", []),
                compliance_elements=analysis_result.get("compliance_elements", []),
                extraction_confidence=analysis_result.get("confidence", 0.7),
                analysis_notes=analysis_result.get("analysis_notes", [])
            )
            
            diagram_results[page_number] = structured_analysis.dict()
            
        except Exception as e:
            error_msg = f"Failed to analyze diagram on page {page_number}: {str(e)}"
            state["errors"].append(error_msg)
            diagram_results[page_number] = {
                "error": error_msg,
                "confidence": 0.0
            }
    
    state["diagram_analyses"] = diagram_results
    state["confidence_scores"]["diagram_analysis"] = calculate_average_diagram_confidence(diagram_results)
    
    await send_progress_update(state, "diagram_analysis", 55, f"Analyzed {len(diagrams)} diagrams")
    state["current_step"] = "diagram_analysis_complete"
    state["progress_percentage"] = 55
    
    return state
```

### **4. Australian Compliance Analysis Node**
```python
async def analyze_compliance_node(state: ContractAnalysisState) -> ContractAnalysisState:
    """
    Analyze compliance with Australian property laws and regulations
    """
    # Progress: 55-70%
    await send_progress_update(state, "compliance_analysis", 60, "Checking Australian property law compliance")
    
    try:
        compliance_analyzer = AustralianComplianceAnalyzer(
            state=state.australian_state,
            document_entities=state.get("detailed_entities", {}),
            diagram_analyses=state.get("diagram_analyses", {})
        )
        
        compliance_results = await compliance_analyzer.analyze_comprehensive_compliance(
            contract_type=state.document_data.get("document_metadata", {}).get("contract_type"),
            property_details=state.get("detailed_entities", {}).get("property_details"),
            contract_dates=state.get("detailed_entities", {}).get("dates", []),
            financial_terms=state.get("detailed_entities", {}).get("financial_amounts", []),
            legal_references=state.get("detailed_entities", {}).get("legal_references", []),
            diagram_compliance=extract_compliance_from_diagrams(state.get("diagram_analyses", {}))
        )
        
        state["compliance_results"] = compliance_results
        state["confidence_scores"]["compliance_analysis"] = compliance_results.get("overall_confidence", 0.8)
        
        # Flag critical compliance issues
        if compliance_results.get("critical_issues"):
            state["warnings"].extend([f"Critical compliance issue: {issue}" for issue in compliance_results["critical_issues"]])
        
        await send_progress_update(state, "compliance_analysis", 70, "Compliance analysis completed")
        
    except Exception as e:
        state["errors"].append(f"Compliance analysis failed: {str(e)}")
        state["confidence_scores"]["compliance_analysis"] = 0.0
    
    state["current_step"] = "compliance_analysis_complete"
    state["progress_percentage"] = 70
    
    return state
```

### **5. Risk Assessment Node**
```python
async def assess_risks_node(state: ContractAnalysisState) -> ContractAnalysisState:
    """
    Comprehensive risk assessment combining all analysis results
    """
    # Progress: 70-85%
    await send_progress_update(state, "risk_assessment", 75, "Performing comprehensive risk assessment")
    
    try:
        risk_assessor = ContractRiskAssessor(
            australian_state=state.australian_state,
            user_context={
                "user_type": state.analysis_options.get("user_type", "buyer"),
                "experience_level": state.analysis_options.get("user_experience", "novice")
            }
        )
        
        risk_assessment = await risk_assessor.assess_comprehensive_risks(
            detailed_entities=state.get("detailed_entities", {}),
            compliance_results=state.get("compliance_results", {}),
            diagram_analyses=state.get("diagram_analyses", {}),
            document_quality=state.document_data.get("document_metadata", {}).get("overall_quality_score", 0.5)
        )
        
        state["risk_assessment"] = risk_assessment
        state["confidence_scores"]["risk_assessment"] = risk_assessment.get("assessment_confidence", 0.8)
        
        # Escalate high-risk findings
        if risk_assessment.get("overall_risk_score", 0) > 0.7:
            state["warnings"].append(f"High-risk contract detected: {risk_assessment.get('primary_risk_factors', [])}")
        
        await send_progress_update(state, "risk_assessment", 85, "Risk assessment completed")
        
    except Exception as e:
        state["errors"].append(f"Risk assessment failed: {str(e)}")
        state["confidence_scores"]["risk_assessment"] = 0.0
    
    state["current_step"] = "risk_assessment_complete"
    state["progress_percentage"] = 85
    
    return state
```

### **6. Generate Recommendations Node**
```python
async def generate_recommendations_node(state: ContractAnalysisState) -> ContractAnalysisState:
    """
    Generate actionable recommendations based on all analysis results
    """
    # Progress: 85-95%
    await send_progress_update(state, "recommendation_generation", 90, "Generating actionable recommendations")
    
    try:
        recommendation_generator = RecommendationEngine(
            australian_state=state.australian_state,
            user_profile={
                "user_type": state.analysis_options.get("user_type", "buyer"),
                "experience_level": state.analysis_options.get("user_experience", "novice"),
                "preferences": state.analysis_options.get("user_preferences", {})
            }
        )
        
        recommendations = await recommendation_generator.generate_comprehensive_recommendations(
            detailed_entities=state.get("detailed_entities", {}),
            compliance_results=state.get("compliance_results", {}),
            risk_assessment=state.get("risk_assessment", {}),
            diagram_insights=extract_actionable_diagram_insights(state.get("diagram_analyses", {}))
        )
        
        # Prioritize recommendations by urgency and impact
        prioritized_recommendations = sort_recommendations_by_priority(
            recommendations, 
            risk_level=state.get("risk_assessment", {}).get("overall_risk_score", 0.5)
        )
        
        state["recommendations"] = prioritized_recommendations
        state["confidence_scores"]["recommendation_generation"] = calculate_recommendation_confidence(recommendations)
        
        await send_progress_update(state, "recommendation_generation", 95, f"Generated {len(recommendations)} recommendations")
        
    except Exception as e:
        state["errors"].append(f"Recommendation generation failed: {str(e)}")
        state["confidence_scores"]["recommendation_generation"] = 0.0
        state["recommendations"] = []
    
    state["current_step"] = "recommendation_generation_complete"
    state["progress_percentage"] = 95
    
    return state
```

### **7. Compile Final Report Node**
```python
async def compile_final_report_node(state: ContractAnalysisState) -> ContractAnalysisState:
    """
    Compile comprehensive analysis report with all results
    """
    # Progress: 95-100%
    await send_progress_update(state, "report_compilation", 98, "Compiling comprehensive analysis report")
    
    try:
        report_compiler = AnalysisReportCompiler(
            australian_state=state.australian_state,
            template_options=state.analysis_options.get("report_format", {})
        )
        
        final_report = await report_compiler.compile_comprehensive_report(
            document_metadata=state.document_data.get("document_metadata", {}),
            detailed_entities=state.get("detailed_entities", {}),
            diagram_analyses=state.get("diagram_analyses", {}),
            compliance_results=state.get("compliance_results", {}),
            risk_assessment=state.get("risk_assessment", {}),
            recommendations=state.get("recommendations", []),
            confidence_scores=state.get("confidence_scores", {}),
            processing_quality=calculate_overall_processing_quality(state),
            errors=state.get("errors", []),
            warnings=state.get("warnings", [])
        )
        
        state["final_report"] = final_report
        state["overall_confidence"] = calculate_overall_analysis_confidence(state.get("confidence_scores", {}))
        
        await send_progress_update(state, "report_compilation", 100, "Analysis completed successfully")
        
    except Exception as e:
        state["errors"].append(f"Report compilation failed: {str(e)}")
        state["final_report"] = create_error_report(state)
    
    state["current_step"] = "analysis_complete"
    state["progress_percentage"] = 100
    
    return state
```

## Conditional Logic and Error Handling

### **Conditional Routing**
```python
def route_after_validation(state: ContractAnalysisState) -> str:
    """Route based on validation results"""
    validation_score = state.get("confidence_scores", {}).get("document_validation", 0)
    
    if validation_score < 0.5:
        return "enhance_document_data"  # Try to improve data quality
    elif validation_score < 0.7:
        return "proceed_with_warnings"  # Continue with reduced expectations
    else:
        return "proceed_normal"  # Full analysis

def route_after_entity_extraction(state: ContractAnalysisState) -> str:
    """Route based on entity extraction success"""
    extraction_score = state.get("confidence_scores", {}).get("entity_extraction", 0)
    
    if extraction_score < 0.4:
        if state.get("retry_count", 0) < 2:
            return "retry_entity_extraction"
        else:
            return "continue_with_partial_data"
    else:
        return "proceed_to_diagram_analysis"

def route_on_critical_errors(state: ContractAnalysisState) -> str:
    """Handle critical errors that prevent continuation"""
    critical_errors = [e for e in state.get("errors", []) if "critical" in e.lower()]
    
    if critical_errors and len(state.get("errors", [])) > 3:
        return "abort_with_error_report"
    else:
        return "continue_analysis"
```

### **Error Recovery Mechanisms**
```python
async def enhance_document_data_node(state: ContractAnalysisState) -> ContractAnalysisState:
    """Attempt to enhance document data quality"""
    # Try alternative extraction methods
    # Request missing data from user
    # Apply data augmentation techniques
    state["retry_count"] = state.get("retry_count", 0) + 1
    return state

async def retry_with_fallback_node(state: ContractAnalysisState) -> ContractAnalysisState:
    """Retry failed operations with fallback methods"""
    # Use simpler extraction methods
    # Reduce analysis depth
    # Focus on critical elements only
    return state
```

## Workflow Configuration

### **LangGraph Workflow Definition**
```python
def create_contract_analysis_workflow() -> StateGraph:
    """Create the complete LangGraph workflow"""
    
    workflow = StateGraph(ContractAnalysisState)
    
    # Add nodes
    workflow.add_node("validate_document", validate_document_node)
    workflow.add_node("extract_entities", extract_detailed_entities_node)
    workflow.add_node("analyze_diagrams", analyze_diagrams_by_page_node)
    workflow.add_node("analyze_compliance", analyze_compliance_node)
    workflow.add_node("assess_risks", assess_risks_node)
    workflow.add_node("generate_recommendations", generate_recommendations_node)
    workflow.add_node("compile_report", compile_final_report_node)
    
    # Error handling nodes
    workflow.add_node("enhance_data", enhance_document_data_node)
    workflow.add_node("retry_extraction", retry_with_fallback_node)
    workflow.add_node("handle_errors", handle_critical_errors_node)
    
    # Define edges
    workflow.set_entry_point("validate_document")
    
    # Conditional routing
    workflow.add_conditional_edges(
        "validate_document",
        route_after_validation,
        {
            "enhance_document_data": "enhance_data",
            "proceed_with_warnings": "extract_entities",
            "proceed_normal": "extract_entities"
        }
    )
    
    workflow.add_conditional_edges(
        "extract_entities",
        route_after_entity_extraction,
        {
            "retry_entity_extraction": "retry_extraction",
            "continue_with_partial_data": "analyze_diagrams",
            "proceed_to_diagram_analysis": "analyze_diagrams"
        }
    )
    
    # Linear progression for successful path
    workflow.add_edge("analyze_diagrams", "analyze_compliance")
    workflow.add_edge("analyze_compliance", "assess_risks")
    workflow.add_edge("assess_risks", "generate_recommendations")
    workflow.add_edge("generate_recommendations", "compile_report")
    
    # Error handling edges
    workflow.add_edge("enhance_data", "extract_entities")
    workflow.add_edge("retry_extraction", "analyze_diagrams")
    
    # Terminal nodes
    workflow.add_edge("compile_report", END)
    workflow.add_edge("handle_errors", END)
    
    return workflow.compile()
```

## WebSocket Integration

### **Progress Update System**
```python
async def send_progress_update(
    state: ContractAnalysisState,
    step: str,
    progress: int,
    description: str
):
    """Send WebSocket progress update"""
    if not state.get("send_progress_updates", False):
        return
    
    websocket_manager = get_websocket_manager()
    session_id = state.get("websocket_session_id")
    
    if websocket_manager and session_id:
        await websocket_manager.send_message(
            session_id,
            {
                "type": "analysis_progress",
                "document_id": state["document_id"],
                "step": step,
                "progress_percentage": progress,
                "description": description,
                "timestamp": datetime.now(UTC).isoformat(),
                "confidence_scores": state.get("confidence_scores", {}),
                "warnings": state.get("warnings", [])
            }
        )
```

## Integration with ContractAnalysisService

### **Service Method Integration**
```python
class EnhancedContractAnalysisService(ContractAnalysisService):
    """Enhanced service with LangGraph workflow integration"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workflow = create_contract_analysis_workflow()
        self.document_service = get_document_service()
    
    async def analyze_contract_with_langgraph(
        self,
        document_id: str,
        user_id: str,
        australian_state: str,
        analysis_options: Optional[Dict[str, Any]] = None,
        websocket_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Main analysis method using LangGraph workflow"""
        
        try:
            # Get document data from Tier 1
            document_data = await self.document_service.get_document_summary(document_id, db)
            if not document_data:
                raise ValueError(f"Document {document_id} not found or not ready")
            
            # Initialize workflow state
            initial_state = ContractAnalysisState(
                document_id=document_id,
                document_data=document_data,
                user_id=user_id,
                australian_state=australian_state,
                analysis_options=analysis_options or {},
                current_step="initialized",
                progress_percentage=0,
                session_id=f"analysis_{uuid.uuid4().hex[:8]}",
                detailed_entities=None,
                diagram_analyses={},
                compliance_results=None,
                risk_assessment=None,
                recommendations=[],
                confidence_scores={},
                validation_results={},
                processing_quality={},
                errors=[],
                warnings=[],
                retry_count=0,
                websocket_session_id=websocket_session_id,
                send_progress_updates=websocket_session_id is not None
            )
            
            # Execute workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            # Process and return results
            return self._format_analysis_results(final_state)
            
        except Exception as e:
            logger.error(f"LangGraph workflow failed: {str(e)}")
            return self._create_error_response(str(e), document_id)
    
    def _format_analysis_results(self, state: ContractAnalysisState) -> Dict[str, Any]:
        """Format workflow results into API response"""
        
        return {
            "success": state.get("current_step") == "analysis_complete",
            "session_id": state.get("session_id"),
            "document_id": state.get("document_id"),
            "analysis_timestamp": datetime.now(UTC).isoformat(),
            "overall_confidence": state.get("overall_confidence", 0.0),
            
            # Core results
            "detailed_entities": state.get("detailed_entities"),
            "diagram_analyses": state.get("diagram_analyses"),
            "compliance_results": state.get("compliance_results"),
            "risk_assessment": state.get("risk_assessment"),
            "recommendations": state.get("recommendations"),
            "final_report": state.get("final_report"),
            
            # Quality metrics
            "confidence_scores": state.get("confidence_scores"),
            "validation_results": state.get("validation_results"),
            "processing_quality": state.get("processing_quality"),
            
            # Issues
            "errors": state.get("errors", []),
            "warnings": state.get("warnings", []),
            
            # Workflow metadata
            "workflow_metadata": {
                "steps_completed": state.get("current_step"),
                "progress_percentage": state.get("progress_percentage"),
                "retry_count": state.get("retry_count", 0),
                "total_processing_time": calculate_processing_time(state)
            }
        }
```

## Performance and Monitoring

### **Workflow Metrics**
```python
workflow_metrics = {
    "step_completion_times": track_step_durations,
    "confidence_score_distribution": monitor_confidence_scores,
    "error_rates_by_step": track_error_patterns,
    "retry_success_rates": measure_recovery_effectiveness,
    "overall_workflow_success_rate": calculate_success_metrics,
    "user_satisfaction_scores": collect_feedback_metrics
}
```

### **Quality Gates**
```python
quality_gates = {
    "minimum_confidence_threshold": 0.6,
    "maximum_acceptable_error_rate": 0.1,
    "required_entity_extraction_completeness": 0.8,
    "diagram_analysis_success_rate": 0.7,
    "compliance_analysis_coverage": 0.9
}
```

This LangGraph workflow design provides a robust, scalable, and maintainable foundation for sophisticated contract analysis while maintaining clean integration with the existing Real2.AI architecture.