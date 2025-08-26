---
title: "Step 3 Synthesis Stories"
status: draft
owner: workflows
depends_on:
  - docs/workflows/step2-section-analysis-workflow.md
  - docs/workflows/step_assessment_architect_dependencies.md
  - docs/workflows/step_assessment_workflow-prd.md
---

## Overview

Step 3 synthesizes Step 2 section outputs into buyer-facing decisions and scores using a DAG-first design. Nodes consume Phase outputs (no Step 1 entities or full text), rely on seeds + targeted retrieval, and persist structured JSON to contracts for idempotency and UI reads.

### Inputs (from Step 2)
- parties_property_result, financial_terms_result, conditions_result, warranties_result, default_termination_result
- settlement_logistics_result, title_encumbrances_result, adjustments_outgoings_result
- disclosure_compliance_result, special_risks_result, cross_section_validation_result
- legal_requirements_matrix, retrieval_index_id, section seeds

### Outputs (Step 3)
- risk_summary (contracts.risk_summary)
- action_plan (contracts.action_plan)
- compliance_summary (contracts.compliance_summary)
- buyer_report (contracts.buyer_report)

### DAG (Step 3)
- RiskAggregator ← cross_section_validation + special_risks + disclosure + title + settlement
- ActionPlan ← cross_section_validation + settlement + adjustments + disclosure + conditions
- ComplianceScore ← cross_section_validation + disclosure + conditions + settlement
- BuyerReport ← RiskAggregator + ActionPlan + ComplianceScore + all Step 2 results

---

## S3.1 Cross-Section Validation (already planned in Step 2 Phase 3)

- Node: ContractLLMNode CrossSectionValidationNode (implemented in Step 2 Phase 3)
- Prompt: step2_cross_validation.md (v2; Phase outputs only)
- Schema: CrossValidationResult
- Persist: contracts.cross_section_validation
- Acceptance: identifies contradictions, date/amount mismatches, risk coherence; proposes fixes.

---

## S3.2 Risk Aggregation and Prioritization

- Goal: Aggregate risks into an overall profile and prioritized list.
- Inputs: special_risks_result, disclosure_compliance_result, cross_section_validation_result, title_encumbrances_result, settlement_logistics_result
- Outputs (Schema: RiskSummaryResult):
  - overall_risk_score (0–1), top_risks[], category_breakdown, rationale, confidence
- Node/Prompt:
  - Node: ContractLLMNode RiskAggregatorNode
  - Prompt: backend/app/prompts/user/analysis/step3/risk_aggregation.md
- Persistence: contracts.risk_summary (JSONB)
- Acceptance:
  - Stable scoring (+/−0.05 across reruns with same inputs)
  - Top risks reflect upstream issues (fixture tests)

---

## S3.3 Recommended Actions & Timeline

- Goal: Convert findings into a sequenced action plan keyed to settlement deadlines.
- Inputs: cross_section_validation_result, settlement_logistics_result, adjustments_outgoings_result, disclosure_compliance_result, conditions_result
- Outputs (Schema: ActionPlanResult):
  - actions[] (title, description, owner, due_by, dependencies, blocking_risks)
- Node/Prompt:
  - Node: ContractLLMNode ActionPlanNode
  - Prompt: backend/app/prompts/user/analysis/step3/action_plan.md
- Persistence: contracts.action_plan (JSONB)
- Acceptance:
  - Every critical discrepancy has a mapped action; due dates align with settlement/condition deadlines

---

## S3.4 Compliance Readiness Score

- Goal: Summarize compliance health vs statutory and contract obligations.
- Inputs: disclosure_compliance_result, cross_section_validation_result, conditions_result, settlement_logistics_result
- Outputs (Schema: ComplianceSummaryResult):
  - score (0–1), gaps[], remediation_readiness, key dependencies
- Node/Prompt:
  - Node: ContractLLMNode ComplianceScoreNode
  - Prompt: backend/app/prompts/user/analysis/step3/compliance_score.md
- Persistence: contracts.compliance_summary (JSONB)
- Acceptance:
  - Score responds predictably to disclosure/validation changes; clear remediation mapping

---

## S3.5 Buyer Report Synthesis

- Goal: Consolidate all results into a buyer-facing report.
- Inputs: all Step 2 results + S3.2 risk_summary + S3.3 action_plan + S3.4 compliance_summary
- Outputs (Schema: BuyerReportResult):
  - executive_summary, section_summaries, key_risks, action_plan_overview, evidence_refs
- Node/Prompt:
  - Node: ContractLLMNode BuyerReportNode
  - Prompt: backend/app/prompts/user/analysis/step3/buyer_report.md
- Persistence: contracts.buyer_report (JSONB); generate artifact for UI rendering
- Acceptance:
  - Clear executive summary; consistent references; structure ready for frontend rendering

---

## System and Prompts

- Create step3 system prompt (backend/app/prompts/system/step3_synthesis.md):
  - Principles: consistency, prioritization, buyer-facing tone, evidence referencing, stability across runs
- User prompts (backend/app/prompts/user/analysis/step3/*): risk_aggregation.md, action_plan.md, compliance_score.md, buyer_report.md
- All use Phase outputs + seeds + retrieval; no Step 1 entities/full text.

---

## Schema & Repository

- contracts adds JSONB columns (core DDL):
  - risk_summary, action_plan, compliance_summary, buyer_report
- Repository upsert/select include these fields for short-circuiting and UI access.

---

## Quality & Testing

- Unit tests for each Step 3 node (parse success, quality gates)
- E2E tests for DAG sequencing and final report content
- Stability tests (scores vary ≤0.05 for same inputs)


