### Stories: Step 2 Section-by-Section Analysis (LangGraph)

This document enumerates the implementation stories for the Step 2 sub-workflow. Each story references PRD 4.1.2 and the dependencies architecture.

#### Story S1: Orchestration and State Schema
- **As a** platform engineer
- **I want** a dedicated Step 2 LangGraph sub-workflow with three phases and dependency gating
- **So that** we can parallelize foundation analyses and sequence dependent/synthesis tasks reliably
- **Acceptance Criteria**:
  - State slice `analysis_results.step2` contains per-section results, confidences, and risk flags
  - Phase 1 uses `asyncio.gather`; Phases 2–3 enforce dependencies
  - Retries via exponential backoff with per-node timeouts
  - Partial failures for non-critical nodes degrade gracefully
  - Telemetry on durations and completion per node

#### Story S2: Parties & Property Verification Analyzer
- References: PRD 4.1.2.1; Dependencies (feeds Title)
- Inputs: full_text, entities.parties, entities.property_address, entities.property_details
- Outputs: verified parties, legal capacity flags, property legal description completeness, inclusions/exclusions list
- Success: 99% property match, 100% incomplete legal description detection, complete inventory
- Acceptance: Structured parser schema; confidence scoring; risk indicators

#### Story S3: Financial Terms Analyzer
- References: PRD 4.1.2.2; Dependencies (feeds Adjustments & Synthesis)
- Inputs: full_text, entities.financial_amounts, entities.dates
- Outputs: purchase price verification, deposit analysis, payment schedule review, GST implications
- Success: 100% calculation accuracy; complete obligations identification
- Acceptance: Structured parser schema; amount/date normalization; risk indicators

#### Story S4: Conditions Risk Assessment Analyzer
- References: PRD 4.1.2.4; Dependencies (feeds Settlement, Disclosure, Special Risks)
- Inputs: full_text, entities.conditions, entities.dates
- Outputs: classification, finance/inspection terms, special conditions, timelines
- Success: 100% identification; accurate risk scoring; dependency map
- Acceptance: Structured schema; computed deadlines and business day flags; risk factors

#### Story S5: Warranties & Representations Analyzer
- References: PRD 4.1.2.8; Low dependencies
- Inputs: full_text, entities.legal_references
- Outputs: vendor warranties, building warranty insurance, representation validation
- Success: Complete catalog; coverage/limitation assessment; misrep detection
- Acceptance: Structured schema; confidence and issues list

#### Story S6: Default & Termination Analyzer
- References: PRD 4.1.2.7; Low dependencies
- Inputs: full_text, entities.conditions
- Outputs: default scenarios, termination rights, remedies assessment
- Success: Complete identification; penalty/notice validation
- Acceptance: Structured schema; severity flags

#### Story S7: Settlement Logistics Analyzer (Dependent)
- References: PRD 4.1.2.3; High dependency on Conditions + Financial
- Inputs: full_text, outputs from Conditions (deadlines, finance/inspection), Financial (pricing), entities.dates
- Outputs: settlement date analysis, process validation, adjustment calculation prerequisites
- Success: 100% date calc accuracy; complete timeline mapping
- Acceptance: Enforce dependency gating; structured schema; risk timeline

#### Story S8: Title & Encumbrances Analyzer with Comprehensive Diagram Integration (Dependent)
- References: PRD 4.1.2.5 (Enhanced); High dependency on Parties/Property + diagrams/overlays
- Inputs: full_text, Parties/Property results (legal description, owners), uploaded diagrams (20+ types), optional overlays
- Outputs: registered encumbrances, visual constraints, integrated risks, discrepancies
- Success: 100% encumbrance identification; 95%+ diagram accuracy; cross-referencing completeness
- Acceptance: Diagram processors registry; parallel diagram processing; integrated result structure with risk flags

#### Story S9: Adjustments & Outgoings Calculator (Synthesis)
- References: PRD 4.1.2.9; Depends on Financial + Settlement
- Inputs: full_text, Financial results, Settlement results
- Outputs: statutory adjustments, body corporate adjustments, tax implications
- Success: 100% accuracy in calculations; complete outgoings identification
- Acceptance: Deterministic calculations; structured schema; evidence pointers

#### Story S10: Disclosure Compliance Check (Synthesis)
- References: PRD 4.1.2.6; Moderate dependencies on metadata, conditions, financial, property classification, settlement method
- Inputs: full_text, entities.metadata, Conditions, Financial, Parties/Property, Settlement, legal requirements matrix
- Outputs: compliance status, missing/insufficient disclosures, state-specific validation
- Success: 100% matrix verification; comprehensive identification
- Acceptance: Structured schema; per-state rules application; gaps list

#### Story S11: Special Risks Identification (Synthesis)
- References: PRD 4.1.2.10; Synthesis across prior analyses
- Inputs: full_text, all previous section outputs
- Outputs: consolidated risk indicators, prioritization inputs for Step 3
- Success: Complete identification and accurate prioritization feed
- Acceptance: Structured schema; aggregation logic; de-duplication and amplification detection

#### Story S12: Cross-Section Validation & Consistency Checks
- References: PRD 4.1.2.11
- Checks: dates consistency, financial cross-refs, condition dependencies, legal matrix application
- Outputs: validation report with red/amber/green flags and confidence
- Acceptance: Deterministic checks; structured output; ties into Step 3

#### Story S13: Prompt & Parser Infrastructure for Step 2
- Create system prompt for Step 2; user prompts per section (`backend/app/prompts/user/analysis/*`).
- Register compositions for each analyzer with appropriate system prompts and parsers.
- Acceptance: Prompt registry updated; composition rules added; model selection metadata present.

#### Story S14: Migration & Integration
- Replace `ContractTermsExtractionNode` call site with `Step2AnalysisWorkflow` entry point.
- Preserve API compatibility in `ContractAnalysisWorkflow` by mapping outputs to existing state fields.
- Acceptance: Tests green; no regressions in Step 1/3; progress tracking intact.
