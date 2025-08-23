# Step 2: Section-by-Section Analysis - Dependencies & Architecture

## Overview

Step 2 of the contract analysis pipeline performs specialized review of 10 critical contract areas. While each section operates as an independent specialist, there are significant dependencies and cross-references between analyzers that must be managed for optimal accuracy and efficiency.

## LangGraph Workflow Architecture

### Overview
The Step 2 analysis pipeline is implemented using **LangGraph** for robust workflow orchestration, eliminating the need for manual context management and caching. LangGraph provides:

- **State Management**: Automatic state persistence across all analyzer nodes
- **Error Recovery**: Built-in retry mechanisms and graceful failure handling  
- **Parallel Execution**: Native support for concurrent analyzer execution
- **Dependency Resolution**: Automatic dependency management between analyzers
- **Scalability**: Built-in support for distributed processing and load balancing

## Dependencies Analysis

### High Dependencies (Sequential Processing Required)
**Dependency Type:** Timeline Coordination
```python
# Settlement dates must consider condition deadlines
settlement_analyzer.analyze(
    contract_text=full_text,
    condition_deadlines=conditions_analysis.deadlines,  # REQUIRED
    finance_approval_period=conditions_analysis.finance_terms,  # REQUIRED
    inspection_periods=conditions_analysis.inspection_terms  # REQUIRED
)
```

**Why:** Settlement logistics analyzer needs to validate that:
- Settlement date allows sufficient time for all conditions to be satisfied
- Business day calculations align with condition deadlines
- Finance approval periods are realistic given settlement timeline

#### 2. Financial Terms → Adjustments & Outgoings
**Dependency Type:** Calculation Foundation
```python
# Adjustments depend on identified financial amounts
adjustments_analyzer.analyze(
    contract_text=full_text,
    purchase_price=financial_analysis.purchase_price,  # REQUIRED
    settlement_date=settlement_analysis.settlement_date,  # REQUIRED
    identified_fees=financial_analysis.ongoing_costs,  # REQUIRED
    deposit_structure=financial_analysis.deposit_terms  # REQUIRED
)
```

**Why:** Adjustment calculations require:
- Base purchase price for percentage calculations
- Settlement date for pro-rata adjustments
- Identified fee structures to avoid double-counting

#### 3. Parties & Property → Title & Encumbrances (Enhanced)
**Dependency Type:** Identity Verification + Visual Analysis
```python
# Title search needs exact property identifiers + diagram analysis
title_analyzer.analyze(
    contract_text=full_text,
    verified_property=parties_analysis.property_details,  # REQUIRED
    registered_owners=parties_analysis.current_owners,  # REQUIRED
    property_identifiers=parties_analysis.legal_description,  # REQUIRED
    survey_diagrams=uploaded_diagrams,  # NEW: REQUIRED for complete analysis
    planning_overlays=external_planning_data  # NEW: OPTIONAL but recommended
)
```

**Why:** Enhanced title analysis cannot proceed without:
- Verified property legal description (lot/plan numbers)
- Current registered proprietor information
- Property type classification for relevant encumbrance rules
- **NEW:** Comprehensive visual diagram analysis across 20+ document types
- **NEW:** Cross-referenced infrastructure mapping from utility plans, sewer diagrams, and environmental overlays
- **NEW:** Development constraint analysis from building envelope plans, zoning maps, and heritage overlays

### Moderate Dependencies (Cross-Validation Required)

#### 4. Disclosure Compliance ← Multiple Inputs
**Dependency Type:** Comprehensive Validation
```python
disclosure_analyzer.analyze(
    contract_text=full_text,
    contract_metadata=entities.metadata,  # From Step 1
    identified_conditions=conditions_analysis.special_conditions,  # Moderate
    financial_structure=financial_analysis.payment_terms,  # Moderate
    property_classification=parties_analysis.property_type,  # Moderate
    settlement_method=settlement_analysis.settlement_process  # Low
)
```

**Why:** Disclosure requirements vary based on:
- Contract type and purchase method (auction vs. standard)
- Property type (residential vs. commercial vs. strata)
- Special conditions that trigger additional disclosures
- Financial arrangements affecting GST/tax disclosure

#### 5. Special Risks ← Synthesis Requirements
**Dependency Type:** Risk Pattern Recognition
```python
special_risks_analyzer.analyze(
    contract_text=full_text,
    all_section_analyses=previous_analyses,  # Moderate to High
    risk_indicators={
        'financial_red_flags': financial_analysis.risk_indicators,
        'condition_complications': conditions_analysis.risk_factors,
        'title_concerns': title_analysis.risk_elements,
        'timeline_pressures': settlement_analysis.risk_timeline
    }
)
```

**Why:** Special risks emerge from:
- Combinations of issues across multiple sections
- Unusual patterns not visible in isolated analysis
- Risk amplification effects between different contract areas

### Low Dependencies (Minimal Cross-Reference)

#### 6. Warranties & Representations
**Dependency Type:** Reference Validation
- **Low dependency** on property type from parties analysis
- **Low dependency** on building status from conditions analysis
- Can run with preliminary data and validate later

#### 7. Default & Termination Analysis
**Dependency Type:** Context Enhancement
- **Low dependency** on financial penalty calculations
- **Low dependency** on condition failure scenarios
- Mostly self-contained legal analysis

---

## LangGraph Workflow Definition

### Step 2 Workflow Graph Structure

```python
class Step2AnalysisWorkflow:
    def __init__(self):
        self.graph = Graph()
        self.setup_workflow_nodes()
        self.setup_workflow_edges()
        
    def setup_workflow_nodes(self):
        """Define all analysis nodes in the LangGraph workflow"""
        
        # Phase 1: Foundation Nodes (Parallel)
        self.graph.add_node("parties_property_analysis", analyze_parties_and_property)
        self.graph.add_node("financial_terms_analysis", analyze_financial_terms)
        self.graph.add_node("conditions_assessment", analyze_conditions)
        self.graph.add_node("warranties_analysis", analyze_warranties)
        self.graph.add_node("default_terms_analysis", analyze_default_terms)
        
        # Phase 2: Dependent Nodes (Sequential)
        self.graph.add_node("settlement_logistics_analysis", analyze_settlement_logistics)
        self.graph.add_node("title_comprehensive_analysis", analyze_title_with_comprehensive_diagrams)
        
        # Phase 3: Synthesis Nodes (Sequential)
        self.graph.add_node("adjustments_calculation", calculate_adjustments)
        self.graph.add_node("disclosure_compliance_check", check_disclosure_compliance)
        self.graph.add_node("special_risks_identification", identify_special_risks)
        
        # Workflow control nodes
        self.graph.add_node("phase1_completion_check", validate_phase1_completion)
        self.graph.add_node("phase2_completion_check", validate_phase2_completion)
        self.graph.add_node("final_validation", validate_all_analyses)
        
    def setup_workflow_edges(self):
        """Define dependencies and execution flow"""
        
        # Phase 1: All foundation nodes run in parallel from start
        foundation_nodes = [
            "parties_property_analysis",
            "financial_terms_analysis", 
            "conditions_assessment",
            "warranties_analysis",
            "default_terms_analysis"
        ]
        
        for node in foundation_nodes:
            self.graph.add_edge("start", node)
            self.graph.add_edge(node, "phase1_completion_check")
            
        # Phase 2: Dependent analysis (requires Phase 1 completion)
        self.graph.add_edge("phase1_completion_check", "settlement_logistics_analysis")
        self.graph.add_edge("phase1_completion_check", "title_comprehensive_analysis") 
        
        # Settlement depends on conditions and financial
        self.graph.add_conditional_edge(
            "settlement_logistics_analysis",
            condition=lambda state: state.get("conditions_assessment_complete") and 
                                   state.get("financial_analysis_complete"),
            if_true="phase2_completion_check"
        )
        
        # Title analysis depends on parties/property + comprehensive diagrams
        self.graph.add_conditional_edge(
            "title_comprehensive_analysis", 
            condition=lambda state: state.get("parties_property_complete") and
                                   len(state.get("uploaded_diagrams", {})) > 0,
            if_true="phase2_completion_check"
        )
        
        # Phase 3: Synthesis analysis (requires Phase 2 completion)
        self.graph.add_edge("phase2_completion_check", "adjustments_calculation")
        self.graph.add_edge("phase2_completion_check", "disclosure_compliance_check")
        self.graph.add_edge("phase2_completion_check", "special_risks_identification")
        
        # Final validation requires all Phase 3 completion
        synthesis_nodes = ["adjustments_calculation", "disclosure_compliance_check", "special_risks_identification"]
        for node in synthesis_nodes:
            self.graph.add_edge(node, "final_validation")
            
        self.graph.add_edge("final_validation", "end")
```

### State Management

```python
class Step2AnalysisState(State):
    """LangGraph state schema for Step 2 analysis"""
    
    # Input data
    contract_text: str
    extracted_entities: ContractEntityExtraction
    uploaded_diagrams: Dict[DiagramType, bytes]
    legal_requirements_matrix: Dict
    
    # Phase 1 results
    parties_property_results: Optional[PartiesPropertyResult] = None
    financial_terms_results: Optional[FinancialTermsResult] = None
    conditions_results: Optional[ConditionsResult] = None
    warranties_results: Optional[WarrantiesResult] = None
    default_terms_results: Optional[DefaultTermsResult] = None
    
    # Phase 2 results  
    settlement_results: Optional[SettlementResult] = None
    title_results: Optional[TitleAnalysisResult] = None
    
    # Phase 3 results
    adjustments_results: Optional[AdjustmentsResult] = None
    compliance_results: Optional[ComplianceResult] = None
    special_risks_results: Optional[SpecialRisksResult] = None
    
    # Workflow control
    phase1_complete: bool = False
    phase2_complete: bool = False
    phase3_complete: bool = False
    total_risk_flags: List[str] = []
    processing_errors: List[str] = []
    
    # Performance tracking
    start_time: datetime
    phase_completion_times: Dict[str, datetime] = {}
    total_diagrams_processed: int = 0
    diagram_processing_success_rate: float = 0.0
```

### Phase-Based Processing Model

#### Phase 1: Foundation Analysis (Parallel Execution)
**Duration:** 60-90 seconds
**Parallelization:** Full parallel execution

```python
foundation_tasks = {
    "parties_property": {
        "analyzer": analyze_parties_and_property,
        "inputs": [full_text, entities.property_address, entities.parties],
        "priority": "CRITICAL",
        "timeout": 90
    },
    "financial_terms": {
        "analyzer": analyze_financial_terms,
        "inputs": [full_text, entities.financial_amounts],
        "priority": "CRITICAL", 
        "timeout": 90
    },
    "conditions_assessment": {
        "analyzer": analyze_conditions,
        "inputs": [full_text, entities.conditions, entities.dates],
        "priority": "CRITICAL",
        "timeout": 120  # Most complex analysis
    },
    "warranties": {
        "analyzer": analyze_warranties,
        "inputs": [full_text, entities.legal_references],
        "priority": "STANDARD",
        "timeout": 60
    },
    "default_terms": {
        "analyzer": analyze_default_terms,
        "inputs": [full_text, entities.conditions],
        "priority": "STANDARD",
        "timeout": 60
    }
}

# Execute all foundation tasks simultaneously
phase1_results = await asyncio.gather(*[
    task["analyzer"](task["inputs"]) for task in foundation_tasks.values()
])
```

#### Phase 2: Dependent Analysis (Sequential with Limited Parallelism)
**Duration:** 45-60 seconds
**Parallelization:** Limited by dependencies

```python
dependent_tasks = {
    "settlement_logistics": {
        "analyzer": analyze_settlement,
        "dependencies": ["conditions_assessment", "financial_terms"],
        "inputs": [
            full_text, 
            entities, 
            phase1_results["conditions_assessment"],
            phase1_results["financial_terms"]
        ]
    },
    "title_review": {
        "analyzer": analyze_title_with_diagrams,  # ENHANCED
        "dependencies": ["parties_property"],
        "inputs": [
            full_text,
            entities,
            phase1_results["parties_property"],
            survey_diagrams,  # NEW INPUT
            planning_overlays  # NEW INPUT
        ]
    }
}

# Execute with dependency management
phase2_results = {}
for task_name, task_config in dependent_tasks.items():
    # Wait for dependencies
    await wait_for_dependencies(task_config["dependencies"])
    
    # Execute task
    phase2_results[task_name] = await task_config["analyzer"](
        task_config["inputs"]
    )
```

#### Phase 3: Synthesis Analysis (Sequential)
**Duration:** 30-45 seconds
**Parallelization:** Limited synthesis tasks

```python
synthesis_tasks = {
    "adjustments": {
        "analyzer": calculate_adjustments,
        "dependencies": ["financial_terms", "settlement_logistics"],
        "inputs": [
            full_text,
            phase1_results["financial_terms"],
            phase2_results["settlement_logistics"]
        ]
    },
    "disclosure_compliance": {
        "analyzer": check_compliance,
        "dependencies": ["ALL_PREVIOUS"],
        "inputs": [
            full_text,
            entities,
            legal_requirements_matrix,
            {**phase1_results, **phase2_results}
        ]
    },
    "special_risks": {
        "analyzer": identify_risks,
        "dependencies": ["ALL_PREVIOUS"],
        "inputs": [
            full_text,
            entities,
            {**phase1_results, **phase2_results}
        ]
    }
}
```

---

## Implementation Workflow

### Workflow Configuration

```python
class Step2Workflow:
    def __init__(self):
        self.phases = [
            Phase1FoundationAnalysis(),
            Phase2DependentAnalysis(), 
            Phase3SynthesisAnalysis()
        ]
        self.timeout_total = 300  # 5 minutes max
        self.retry_policy = ExponentialBackoff(max_retries=2)
        
    async def execute(self, contract_text: str, entities: ContractEntityExtraction):
        results = {}
        
        for phase in self.phases:
            try:
                phase_results = await phase.execute(
                    contract_text=contract_text,
                    entities=entities,
                    previous_results=results
                )
                results.update(phase_results)
                
            except PhaseFailure as e:
                # Handle partial failures
                results = await self.handle_phase_failure(e, phase, results)
                
        return SectionAnalysisResults(**results)
```

### Error Handling Strategy

#### 1. Graceful Degradation
```python
async def handle_analyzer_failure(analyzer_name: str, error: Exception):
    if analyzer_name in CRITICAL_ANALYZERS:
        # Critical analyzer failure - cannot proceed
        raise CriticalAnalysisFailure(f"{analyzer_name} failed: {error}")
    else:
        # Non-critical - proceed with warning
        logger.warning(f"Non-critical analyzer {analyzer_name} failed: {error}")
        return create_fallback_result(analyzer_name)
```

#### 2. Dependency Recovery
```python
async def recover_from_dependency_failure(failed_analyzer: str, dependent_analyzers: List[str]):
    for dependent in dependent_analyzers:
        if dependent in REQUIRES_FULL_DEPENDENCY:
            # Skip dependent analyzer
            mark_as_skipped(dependent, reason=f"Dependency {failed_analyzer} failed")
        else:
            # Use fallback/partial data
            execute_with_fallback_data(dependent, failed_analyzer)
```

#### 3. Timeout Management
```python
async def execute_with_timeout(analyzer, timeout: int):
    try:
        return await asyncio.wait_for(analyzer.run(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Analyzer {analyzer.name} timed out after {timeout}s")
        return create_timeout_fallback(analyzer)
```

## Diagram Analysis Integration

### New Component: Visual Document Analysis

#### Supported Document Types (20+ Categories)
- **Title and Survey Documents**
  - `title_plan`: Legal boundary definitions and registered interests
  - `survey_diagram`: Precise measurements and infrastructure locations
  - `contour_map`: Elevation data and natural drainage patterns

- **Property Development Documents**  
  - `development_plan`: Proposed constructions and site modifications
  - `subdivision_plan`: Lot layouts and shared infrastructure
  - `off_the_plan_marketing`: Unit specifications and building features
  - `building_envelope_plan`: Construction boundaries and setback requirements

- **Strata and Body Corporate Documents**
  - `strata_plan`: Unit boundaries and common property definitions
  - `body_corporate_plan`: Shared facilities and maintenance responsibilities  
  - `parking_plan`: Allocated spaces and vehicular access routes

- **Infrastructure and Utility Documents**
  - `utility_plan`: Gas, water, electricity, and telecommunications infrastructure
  - `sewer_service_diagram`: Sewerage connections and maintenance access
  - `drainage_plan`: Stormwater management and flood mitigation systems
  - `site_plan`: Building footprints and site access arrangements

- **Environmental and Planning Overlays**
  - `flood_map`: Inundation levels, flood zones, and evacuation routes
  - `bushfire_map`: Risk zones and asset protection requirements
  - `zoning_map`: Permitted land uses and development restrictions
  - `environmental_overlay`: Protected areas and vegetation preservation zones
  - `heritage_overlay`: Protected structures and archaeological significance
  - `landscape_plan`: Vegetation requirements and ongoing maintenance obligations

#### LangGraph Implementation
```python
from langgraph.graph import Graph, Node, Edge
from langgraph.state import State

class DiagramAnalyzer:
    def __init__(self):
        self.processors = {
            # Title and Survey Processing
            DiagramType.TITLE_PLAN: TitlePlanProcessor(),
            DiagramType.SURVEY_DIAGRAM: SurveyDiagramProcessor(), 
            DiagramType.CONTOUR_MAP: ContourMapProcessor(),
            
            # Development and Planning Processing
            DiagramType.DEVELOPMENT_PLAN: DevelopmentPlanProcessor(),
            DiagramType.SUBDIVISION_PLAN: SubdivisionPlanProcessor(),
            DiagramType.OFF_THE_PLAN_MARKETING: MarketingPlanProcessor(),
            DiagramType.BUILDING_ENVELOPE_PLAN: BuildingEnvelopeProcessor(),
            
            # Strata and Body Corporate Processing
            DiagramType.STRATA_PLAN: StrataPlanProcessor(),
            DiagramType.BODY_CORPORATE_PLAN: BodyCorporateProcessor(),
            DiagramType.PARKING_PLAN: ParkingPlanProcessor(),
            
            # Infrastructure and Utilities Processing  
            DiagramType.UTILITY_PLAN: UtilityPlanProcessor(),
            DiagramType.SEWER_SERVICE_DIAGRAM: SewerDiagramProcessor(),
            DiagramType.DRAINAGE_PLAN: DrainagePlanProcessor(),
            DiagramType.SITE_PLAN: SitePlanProcessor(),
            
            # Environmental and Planning Processing
            DiagramType.FLOOD_MAP: FloodMapProcessor(),
            DiagramType.BUSHFIRE_MAP: BushfireMapProcessor(), 
            DiagramType.ZONING_MAP: ZoningMapProcessor(),
            DiagramType.ENVIRONMENTAL_OVERLAY: EnvironmentalProcessor(),
            DiagramType.HERITAGE_OVERLAY: HeritageProcessor(),
            DiagramType.LANDSCAPE_PLAN: LandscapeProcessor()
        }
        
    def process_diagrams_parallel(self, diagram_batch: Dict[DiagramType, bytes]):
        """Process multiple diagram types in parallel using LangGraph"""
        results = {}
        for diagram_type, image_data in diagram_batch.items():
            processor = self.processors.get(diagram_type, self.processors[DiagramType.UNKNOWN])
            results[diagram_type] = processor.analyze(image_data)
        return results
        
    def integrate_analysis_results(self, diagram_results: Dict, contract_text: str):
        """Integrate all diagram analysis results with contract analysis"""
        return {
            "infrastructure_constraints": self.combine_utility_analysis(diagram_results),
            "environmental_restrictions": self.combine_environmental_analysis(diagram_results),
            "development_limitations": self.combine_development_analysis(diagram_results),
            "access_and_parking": self.combine_access_analysis(diagram_results),
            "flood_and_bushfire_risks": self.combine_natural_hazard_analysis(diagram_results),
            "heritage_and_zoning": self.combine_planning_analysis(diagram_results),
            "strata_considerations": self.combine_strata_analysis(diagram_results),
            "comprehensive_risk_map": self.create_integrated_risk_overlay(diagram_results, contract_text)
        }
```
```

#### LangGraph Integration with Title Analysis
```python
@Node
def analyze_title_with_comprehensive_diagrams(state: State):
    """Enhanced title analysis node in LangGraph workflow"""
    
    # Extract required data from LangGraph state
    contract_text = state.get("contract_text")
    entities = state.get("extracted_entities")
    all_diagrams = state.get("uploaded_diagrams", {})
    
    # Traditional title analysis
    registered_data = extract_title_information(contract_text, entities)
    
    # Comprehensive diagram analysis across all types
    diagram_analyzer = DiagramAnalyzer()
    visual_analysis = diagram_analyzer.process_diagrams_parallel(all_diagrams)
    integrated_results = diagram_analyzer.integrate_analysis_results(visual_analysis, contract_text)
    
    # Enhanced combined analysis
    combined_analysis = {
        # Core title information
        "registered_encumbrances": registered_data.encumbrances,
        "title_verification": registered_data.verification_status,
        
        # Comprehensive visual constraints
        "infrastructure_constraints": integrated_results["infrastructure_constraints"],
        "environmental_restrictions": integrated_results["environmental_restrictions"], 
        "development_limitations": integrated_results["development_limitations"],
        "access_and_parking_constraints": integrated_results["access_and_parking"],
        
        # Risk assessments
        "flood_bushfire_risks": integrated_results["flood_and_bushfire_risks"],
        "heritage_zoning_impacts": integrated_results["heritage_and_zoning"],
        "strata_body_corporate_issues": integrated_results["strata_considerations"],
        
        # Integration and validation
        "registered_vs_visual_discrepancies": compare_all_sources(registered_data, visual_analysis),
        "comprehensive_buildable_analysis": calculate_total_development_potential(integrated_results),
        "integrated_risk_assessment": create_comprehensive_risk_matrix(registered_data, integrated_results),
        
        # Specific constraint categories
        "utility_easements_and_access": extract_utility_constraints(visual_analysis),
        "drainage_and_flooding_impacts": extract_water_management_constraints(visual_analysis),
        "bushfire_asset_protection": extract_bushfire_requirements(visual_analysis),
        "heritage_development_controls": extract_heritage_restrictions(visual_analysis)
    }
    
    # Update LangGraph state with results
    state.update({
        "title_analysis_complete": True,
        "title_analysis_results": TitleAnalysisResult(**combined_analysis),
        "identified_constraints_count": len(combined_analysis["registered_encumbrances"]) + 
                                      len(integrated_results["infrastructure_constraints"]),
        "risk_flags": extract_high_priority_risks(combined_analysis)
    })
    
    return state
```

### 1. Smart Context Sharing
```python
class SharedContractContext:
    def __init__(self, contract_text: str):
        self.full_text = contract_text
        self.common_clauses = self.extract_common_clauses()
        self.cross_references = self.build_reference_map()
        
    def extract_common_clauses(self):
        return {
            'settlement_clauses': extract_settlement_related(self.full_text),
            'financial_clauses': extract_financial_related(self.full_text),
            'condition_clauses': extract_condition_related(self.full_text),
            'legal_references': extract_legal_references(self.full_text)
        }
        
    def get_context_for_analyzer(self, analyzer_type: str):
        return {
            'full_text': self.full_text,
            'relevant_clauses': self.common_clauses.get(f"{analyzer_type}_clauses", []),
            'cross_references': self.cross_references
        }
```

### 2. Incremental Processing
```python
async def incremental_analysis(contract_text: str, entities: ContractEntityExtraction):
    """Process in stages with intermediate validation"""
    
    # Stage 1: Quick validation pass
    validation_results = await quick_validation_pass(contract_text, entities)
    if validation_results.has_critical_issues():
        return early_termination_result(validation_results)
    
    # Stage 2: Foundation analysis with checkpoints
    foundation_checkpoint = await run_foundation_with_checkpoints(contract_text, entities)
    
    # Stage 3: Dependent analysis with partial results
    return await complete_analysis_with_foundation(foundation_checkpoint)
```

### 3. Caching Strategy
```python
class AnalysisCache:
    def __init__(self):
        self.clause_analysis_cache = {}
        self.cross_reference_cache = {}
        
    async def get_or_analyze(self, clause_hash: str, analyzer_func):
        if clause_hash in self.clause_analysis_cache:
            return self.clause_analysis_cache[clause_hash]
            
        result = await analyzer_func()
        self.clause_analysis_cache[clause_hash] = result
        return result
```

---

## Performance Targets

### Phase Execution Times (LangGraph Optimized)
- **Phase 1 (Foundation):** 120-180 seconds (parallel execution with comprehensive diagram processing)
- **Phase 2 (Dependent):** 90-120 seconds (limited parallel with enhanced title analysis across 20+ diagram types)  
- **Phase 3 (Synthesis):** 60-90 seconds (sequential with integrated risk assessment)
- **Total Step 2 Duration:** 270-390 seconds (4.5-6.5 minutes)

### Success Criteria (LangGraph Enhanced)
- **Completion Rate:** 99.5%+ successful completion with LangGraph error recovery
- **Accuracy:** 
  - 95%+ accuracy on critical dependencies and comprehensive visual analysis
  - 98% accuracy in infrastructure and utility identification across all diagram types
  - 92% accuracy in environmental overlay interpretation
  - 96% accuracy in strata and body corporate constraint identification
- **Error Recovery:** 95%+ successful recovery from non-critical failures using LangGraph retry mechanisms
- **Scalability:** Support 500+ concurrent Step 2 executions with LangGraph distributed processing
- **Comprehensive Diagram Processing:** 
  - 95%+ successful processing rate across all 20+ diagram types
  - 90%+ accuracy in cross-referencing visual constraints with contract terms
  - Complete integration of all constraint types into unified risk assessment

### Monitoring & Alerting (LangGraph Integration)
```python
class Step2LangGraphMonitoring:
    def track_node_performance(self, node_name: str, state: Step2AnalysisState):
        """Track individual node performance within LangGraph"""
        duration = (datetime.now() - state.phase_completion_times.get(node_name + "_start", datetime.now())).total_seconds()
        
        metrics.timing(f"step2.langgraph.{node_name}.duration", duration)
        metrics.increment(f"step2.langgraph.{node_name}.completion")
        
        # Track diagram processing metrics
        if node_name == "title_comprehensive_analysis":
            metrics.gauge("step2.diagrams.processed_count", state.total_diagrams_processed)
            metrics.gauge("step2.diagrams.success_rate", state.diagram_processing_success_rate)
            
    def track_workflow_health(self, state: Step2AnalysisState):
        """Monitor overall workflow health and performance"""
        total_duration = (datetime.now() - state.start_time).total_seconds()
        error_count = len(state.processing_errors)
        risk_flag_count = len(state.total_risk_flags)
        
        metrics.timing("step2.langgraph.total_duration", total_duration)
        metrics.gauge("step2.langgraph.error_count", error_count) 
        metrics.gauge("step2.langgraph.risk_flags", risk_flag_count)
        
        # Alert on performance degradation
        if total_duration > 420:  # 7 minutes
            send_alert(f"Step 2 analysis exceeding target duration: {total_duration}s", severity="MEDIUM")
        
        if error_count > 2:
            send_alert(f"Multiple errors in Step 2 analysis: {state.processing_errors}", severity="HIGH")
            
    def alert_on_diagram_processing_failure(self, diagram_type: DiagramType, error: str):
        """Alert on specific diagram processing issues"""
        alert_message = f"Diagram processing failure for {diagram_type.value}: {error}"
        
        # Critical diagram types require immediate attention
        critical_types = [DiagramType.TITLE_PLAN, DiagramType.SURVEY_DIAGRAM, DiagramType.FLOOD_MAP]
        severity = "HIGH" if diagram_type in critical_types else "MEDIUM"
        
        send_alert(alert_message, severity=severity)
```

This LangGraph-based architecture provides robust workflow orchestration with automatic state management, error recovery, and scalable processing of comprehensive diagram analysis across all 20+ document types. The enhanced approach increases processing time to 4.5-6.5 minutes but delivers significantly more comprehensive risk assessment capabilities.