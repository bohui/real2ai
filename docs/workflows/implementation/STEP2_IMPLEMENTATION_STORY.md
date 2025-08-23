# Step 2 Section-by-Section Analysis Implementation Story

## Executive Summary

This document details the comprehensive refactor to replace `ContractTermsExtractionNode` with a LangGraph-powered Step 2 sub-workflow that performs specialized, concurrent analysis of 10 critical contract sections as defined in PRD 4.1.2.

## Implementation Approach

### Phase 1: Foundation Analysis (Parallel Execution)
- **Parties & Property Verification**: Identity validation, legal capacity, property description completeness
- **Financial Terms Analysis**: Purchase price verification, deposit analysis, payment schedules, GST implications
- **Conditions Risk Assessment**: Classification, finance/inspection terms, special conditions, timeline dependencies
- **Warranties & Representations**: Vendor warranties, building insurance, representation validation
- **Default & Termination Analysis**: Default scenarios, termination rights, remedies assessment

### Phase 2: Dependent Analysis (Sequential with Limited Parallelism)
- **Settlement Logistics**: Depends on Conditions + Financial results for timeline validation
- **Title & Encumbrances with Comprehensive Diagrams**: Depends on Parties/Property + 20+ diagram types

### Phase 3: Synthesis Analysis (Sequential)
- **Adjustments & Outgoings**: Depends on Financial + Settlement for calculation accuracy
- **Disclosure Compliance**: Depends on ALL_PREVIOUS + legal matrix for comprehensive validation
- **Special Risks Identification**: Synthesis across all sections for risk pattern recognition

## Technical Architecture

### LangGraph Workflow Structure
```python
class Step2AnalysisWorkflow:
    # Phase-based processing with dependency management
    # State management via Step2AnalysisState
    # Error recovery with graceful degradation
    # Cross-section validation framework
```

### State Schema Enhancement
- Add `analysis_results.step2` to `RealEstateAgentState`
- Per-section structured results with confidence and risk indicators
- Cross-section validation report with date consistency checks
- Comprehensive telemetry for Step 3 risk engine consumption

### Prompt & Schema Infrastructure
- System prompt: `backend/app/prompts/system/step2_section_analysis.md`
- User prompts: `backend/app/prompts/user/analysis/step2/*.md` (11 prompts)
- Output schemas: `backend/app/prompts/schema/step2/*.py` (11 schemas)
- Registry updates: `prompt_registry.yaml` and `composition_rules.yaml`

### Comprehensive Diagram Integration
Enhanced Title & Encumbrances analyzer supports 20+ diagram types:
- **Title/Survey**: title_plan, survey_diagram, contour_map
- **Development**: development_plan, subdivision_plan, building_envelope_plan
- **Strata/Body Corporate**: strata_plan, body_corporate_plan, parking_plan
- **Infrastructure/Utilities**: utility_plan, sewer_service_diagram, drainage_plan, site_plan
- **Environmental/Planning**: flood_map, bushfire_map, zoning_map, environmental_overlay, heritage_overlay, landscape_plan

## Implementation Stories

### Story S1: LangGraph Orchestration & State Schema ✓ APPROVED
**Objective**: Implement three-phase workflow with dependency gating and state management
**Deliverables**:
- `Step2AnalysisWorkflow` class with phase-based execution
- `Step2AnalysisState` schema extension to `RealEstateAgentState`
- Dependency resolution engine with graceful degradation
- Retry mechanisms with exponential backoff
- Telemetry and monitoring integration

**Acceptance Criteria**:
- Phase 1 uses `asyncio.gather` for parallel execution
- Phases 2-3 enforce dependency requirements
- Partial failures degrade gracefully for non-critical analyzers
- All nodes include duration and completion telemetry
- Cross-section validation runs after all phases complete

### Story S2: Parties & Property Verification Analyzer ✓ APPROVED
**PRD Reference**: 4.1.2.1
**Dependencies**: None (Phase 1 - Foundation)
**Success Criteria**: 99% property match, 100% incomplete legal description detection

**Implementation**:
- Validate buyer/seller names and legal capacity
- Cross-reference property identification with title records
- Complete inventory of inclusions/exclusions
- Risk indicators for identity and property description issues

### Story S3: Financial Terms Analyzer ✓ APPROVED  
**PRD Reference**: 4.1.2.2
**Dependencies**: None (Phase 1 - Foundation)
**Success Criteria**: 100% calculation accuracy, complete obligation identification

**Implementation**:
- Purchase price verification against market comparables
- Deposit analysis with trust account validation
- Payment schedule review including progress payments
- GST implications and tax calculations

### Story S4: Conditions Risk Assessment Analyzer ✓ APPROVED
**PRD Reference**: 4.1.2.4  
**Dependencies**: None (Phase 1 - Foundation)
**Success Criteria**: 100% condition identification, accurate risk scoring, dependency mapping

**Implementation**:
- Classification of conditions (standard vs special, precedent vs subsequent)
- Finance condition analysis with approval timeframes
- Inspection condition review with scope validation
- Special condition assessment including sunset clauses

### Story S5: Warranties & Representations Analyzer ✓ APPROVED
**PRD Reference**: 4.1.2.8
**Dependencies**: Low (Phase 1 - Foundation)
**Success Criteria**: Complete warranty catalog, coverage assessment, misrepresentation detection

**Implementation**:
- Vendor warranty analysis including structural and defect warranties
- Building warranty insurance verification
- Representation validation against factual accuracy
- Risk indicators for warranty gaps or misrepresentations

### Story S6: Default & Termination Analyzer ✓ APPROVED
**PRD Reference**: 4.1.2.7
**Dependencies**: Low (Phase 1 - Foundation)  
**Success Criteria**: Complete scenario identification, penalty validation, termination mapping

**Implementation**:
- Default clause analysis for buyer and seller scenarios
- Termination rights review with notice requirements
- Remedies assessment including specific performance
- Risk indicators for harsh or one-sided terms

### Story S7: Settlement Logistics Analyzer ✓ APPROVED
**PRD Reference**: 4.1.2.3
**Dependencies**: HIGH - Conditions (deadlines) + Financial (pricing)
**Success Criteria**: 100% date calculation accuracy, complete timeline mapping

**Implementation**:
- Settlement date analysis against condition deadlines
- Process validation (PEXA vs physical settlement)
- Adjustment calculation prerequisites
- Risk timeline with buffer period recommendations

### Story S8: Title & Encumbrances with Comprehensive Diagram Integration ✓ APPROVED
**PRD Reference**: 4.1.2.5 (Enhanced)
**Dependencies**: HIGH - Parties/Property (legal description) + diagrams/overlays
**Success Criteria**: 100% encumbrance identification, 95%+ diagram accuracy, complete cross-referencing

**Implementation**:
- Traditional title verification with registered encumbrances
- Comprehensive diagram processing across 20+ document types
- Visual constraint analysis and infrastructure mapping
- Integrated risk assessment combining registered and visual data
- Cross-referencing validation between contract and visual documents

### Story S9: Adjustments & Outgoings Calculator ✓ APPROVED
**PRD Reference**: 4.1.2.9
**Dependencies**: HIGH - Financial (amounts) + Settlement (dates)
**Success Criteria**: 100% calculation accuracy, complete outgoing identification

**Implementation**:
- Statutory adjustment calculations (rates, water, land tax)
- Body corporate adjustment apportionment
- GST and tax implication assessment
- Evidence-based calculation validation

### Story S10: Disclosure Compliance Check ✓ APPROVED
**PRD Reference**: 4.1.2.6
**Dependencies**: MODERATE - Multi-input synthesis
**Success Criteria**: 100% matrix verification, comprehensive gap identification

**Implementation**:
- State-specific disclosure requirement validation
- Mandatory disclosure item verification
- Strata/body corporate disclosure compliance
- Legal requirements matrix application

### Story S11: Special Risks Identification ✓ APPROVED
**PRD Reference**: 4.1.2.10
**Dependencies**: MODERATE - Synthesis across all previous analyses
**Success Criteria**: Complete risk identification, accurate prioritization feed

**Implementation**:
- Off-plan specific risk analysis
- Strata title risk assessment
- Environmental and planning risk evaluation
- Risk pattern recognition and amplification detection

### Story S12: Cross-Section Validation & Consistency Checks ✓ APPROVED
**PRD Reference**: 4.1.2.11
**Success Criteria**: Deterministic validation, structured red/amber/green output

**Implementation**:
- Date consistency validation across all sections
- Financial cross-reference verification
- Condition dependency mapping and validation
- Legal requirements matrix application across sections

### Story S13: Prompt & Parser Infrastructure ✓ APPROVED
**Objective**: Create comprehensive prompt and schema infrastructure for Step 2
**Deliverables**:
- System prompt for section modularity and cross-validation
- 11 user prompts (one per section + cross-validation)
- 11 Pydantic output schemas for structured parsing
- Registry and composition rule updates

**Files to Create**:
- `backend/app/prompts/system/step2_section_analysis.md`
- `backend/app/prompts/user/analysis/step2/` (11 prompt files)
- `backend/app/prompts/schema/step2/` (11 schema files)
- Updates to `prompt_registry.yaml` and `composition_rules.yaml`

### Story S14: Migration & Integration ✓ APPROVED
**Objective**: Replace ContractTermsExtractionNode with Step2AnalysisWorkflow
**Deliverables**:
- New `SectionAnalysisNode` invoking `Step2AnalysisWorkflow`
- API compatibility maintenance via state field mapping
- Feature flag rollout strategy (shadow → dual-run → default)
- Integration testing and regression prevention

## Success Metrics & Acceptance

### Performance Targets
- **Total Step 2 Duration**: ≤ 390 seconds (4.5-6.5 minutes median)
- **Phase 1 (Foundation)**: 120-180 seconds parallel execution
- **Phase 2 (Dependent)**: 90-120 seconds with diagram processing
- **Phase 3 (Synthesis)**: 60-90 seconds sequential analysis
- **Completion Rate**: ≥ 99.5% with LangGraph retry mechanisms

### Accuracy Requirements
- **Critical Dependencies**: ≥ 95% accuracy
- **Comprehensive Visual Analysis**: ≥ 95% across all diagram types
- **Infrastructure/Utility Identification**: ≥ 98%
- **Environmental Overlay Interpretation**: ≥ 92%
- **Strata/Body Corporate Constraints**: ≥ 96%

### Quality Gates
- All section outputs include confidence scores and risk indicators
- Cross-section validation report with actionable findings
- Step 3 consumption without regression
- Complete PRD 4.1.2 success criteria compliance

## Risk Mitigation

### Technical Risks
- **Token Pressure**: Section-scoped prompts, context slicing, aggressive caching
- **Dependency Failures**: Graceful degradation, skip-with-reason flows, fallback data
- **Diagram Variability**: Retry mechanisms, quality heuristics, diagnostic surfacing
- **Latency**: Per-story timeouts, short-circuit synthesis, performance monitoring

### Implementation Risks
- **Integration Complexity**: Feature flag rollout, shadow mode validation, dual-run comparison
- **State Management**: LangGraph state persistence, concurrent update handling
- **Error Recovery**: Comprehensive error handling, partial failure tolerance

## Rollout Strategy

### Phase A: Shadow Mode
- Compute Step 2 alongside legacy ContractTermsExtractionNode
- No functional replacement, pure observation and validation
- Performance and accuracy comparison metrics

### Phase B: Dual-Run with Comparison  
- Run both systems with active comparison
- Alert on drift beyond configured thresholds
- Gradual confidence building and issue identification

### Phase C: Production Default
- Step 2 becomes primary execution path
- Legacy fallback retained for two release cycles
- Monitoring and rollback capabilities maintained

## Dependencies & Integration Points

### Upstream Dependencies
- Step 1 entity extraction results (`ContractEntityExtraction`)
- Document processing completion with full_text availability
- Optional diagram uploads and planning overlay data
- Legal requirements matrix for jurisdiction-specific validation

### Downstream Integration
- Step 3 risk prioritization engine consumption
- Existing report generation and UI display
- Progress tracking and user notification systems
- Analytics and monitoring infrastructure

### External Systems
- Diagram processing services for visual analysis
- Title registry APIs for encumbrance verification
- Planning overlay services for environmental constraints
- Legal requirements database for compliance validation

## Conclusion

This implementation transforms contract analysis from a monolithic extraction process into a sophisticated, multi-phase workflow that delivers comprehensive, accurate, and explainable results. The LangGraph-powered architecture provides robust error recovery, dependency management, and scalability while maintaining compatibility with existing systems and achieving the ambitious performance and accuracy targets defined in the PRD.

The phased rollout strategy ensures safe deployment with comprehensive validation, while the comprehensive diagram integration delivers unprecedented depth of analysis for property constraints and risks. This implementation positions Real2.AI as the leading platform for professional-grade contract analysis with both speed and accuracy.