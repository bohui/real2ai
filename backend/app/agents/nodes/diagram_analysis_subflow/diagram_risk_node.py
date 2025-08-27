from typing import Any, Dict, List, Optional

from app.agents.nodes.contract_llm_base import ContractLLMNode


class DiagramRiskNode(ContractLLMNode):
    def __init__(self, workflow, *, progress_range: tuple[int, int] = (0, 100)):
        from app.prompts.schema.diagram_analysis.diagram_risk_schema import (
            DiagramRiskAssessment,
        )

        super().__init__(
            workflow=workflow,
            node_name="diagram_risk_assessment",
            contract_attribute="diagram_risks",
            result_model=DiagramRiskAssessment,
            progress_range=progress_range,
        )

    async def _short_circuit_check(self, state) -> Optional[Dict[str, Any]]:
        """Check if diagram risk assessment already exists and is current."""
        existing_risks = state.get("diagram_risks")
        image_semantics = state.get("image_semantics")

        # If no image semantics available, can't do risk assessment
        if not image_semantics:
            self._log_warning("No image semantics available for risk assessment")
            return {"diagram_risks": None, "reason": "no_image_semantics"}

        # If risk assessment already exists, check if it's current
        if existing_risks and isinstance(existing_risks, dict):
            try:
                # Check if the assessment is based on current semantics
                # Compare diagram sources with current uploaded diagrams
                uploaded = state.get("uploaded_diagrams") or {}
                current_diagram_types = (
                    list(uploaded.keys()) if isinstance(uploaded, dict) else []
                )

                existing_sources = existing_risks.get("diagram_sources", [])

                # Convert enum values to strings for comparison
                existing_source_strings = []
                for source in existing_sources:
                    if hasattr(source, "value"):
                        existing_source_strings.append(source.value)
                    else:
                        existing_source_strings.append(str(source))

                # If diagram types match, assessment is current
                if set(existing_source_strings) == set(current_diagram_types):
                    self._log_step_debug(
                        "Diagram risk assessment already current - skipping",
                        state,
                        {
                            "existing_sources": existing_source_strings,
                            "current_types": current_diagram_types,
                        },
                    )
                    return {
                        "diagram_risks": existing_risks,
                        "reason": "already_current",
                    }

            except Exception as e:
                self._log_warning(f"Error checking existing risk assessment: {e}")
                # Continue with new assessment if check fails

        return None  # Proceed with analysis

    async def _build_context_and_parser(self, state):
        from app.core.prompts import PromptContext, ContextType
        from app.core.prompts.parsers import create_parser
        from app.prompts.schema.diagram_analysis.diagram_risk_schema import (
            DiagramRiskAssessment,
        )

        uploaded = state.get("uploaded_diagrams") or {}
        diagram_types: List[str] = (
            list(uploaded.keys()) if isinstance(uploaded, dict) else []
        )
        diagram_uris: List[str] = []
        if isinstance(uploaded, dict):
            try:
                seen: set[str] = set()
                for _dtype, entries in uploaded.items():
                    if not isinstance(entries, list):
                        continue
                    for entry in entries:
                        if isinstance(entry, Dict):
                            uri = entry.get("uri")
                            if isinstance(uri, str) and uri and uri not in seen:
                                seen.add(uri)
                                diagram_uris.append(uri)
            except Exception:
                pass

        # Build context variables for diagram risk assessment
        context_vars = {
            "diagram_types": diagram_types,
            "diagram_uris": diagram_uris,
            "image_semantics_result": state.get("image_semantics"),
            "australian_state": state.get("australian_state", "NSW"),
            "contract_type": state.get("contract_type", "residential"),
        }

        # Add contract metadata if available
        contract_metadata = state.get("contract_metadata") or {}
        if contract_metadata:
            optional_vars = [
                "purchase_method",
                "use_category",
                "property_condition",
                "transaction_complexity",
            ]
            for var in optional_vars:
                if var in contract_metadata:
                    context_vars[var] = contract_metadata[var]

        # Add other optional context variables
        if state.get("user_experience"):
            context_vars["user_experience"] = state["user_experience"]
        if state.get("property_type"):
            context_vars["property_type"] = state["property_type"]
        if state.get("analysis_focus"):
            context_vars["analysis_focus"] = state["analysis_focus"]
        if state.get("address"):
            context_vars["address"] = state["address"]

        context = PromptContext(
            context_type=ContextType.ANALYSIS,
            variables=context_vars,
        )

        parser = create_parser(
            DiagramRiskAssessment, strict_mode=False, retry_on_failure=True
        )
        return context, parser, "step2_diagram_risk"

    def _evaluate_quality(self, result: Optional[Any], state) -> Dict[str, Any]:
        if result is None:
            return {"ok": False, "reason": "no_result"}

        try:
            # Extract key metrics from the risk assessment
            total = int(getattr(result, "total_risks_identified", 0) or 0)
            overall = getattr(result, "overall_risk_score", None)
            high_priority_risks = getattr(result, "high_priority_risks", []) or []
            recommended_actions = getattr(result, "recommended_actions", []) or []
            diagram_sources = getattr(result, "diagram_sources", []) or []

            # Check basic structure integrity
            has_property_id = bool(getattr(result, "property_identifier", None))
            has_diagram_sources = len(diagram_sources) > 0
            has_assessment_structure = has_property_id and has_diagram_sources

            if not has_assessment_structure:
                return {
                    "ok": False,
                    "reason": "missing_basic_structure",
                    "has_property_id": has_property_id,
                    "has_diagram_sources": has_diagram_sources,
                }

            # Quality metrics
            has_risks = total > 0
            has_priorities = len(high_priority_risks) > 0
            has_actions = len(recommended_actions) > 0
            has_valid_overall_score = overall is not None

            # Comprehensive quality check
            quality_checks = {
                "has_risks": has_risks,
                "has_priorities": has_priorities,
                "has_actions": has_actions,
                "has_valid_overall_score": has_valid_overall_score,
                "has_property_id": has_property_id,
                "has_diagram_sources": has_diagram_sources,
            }

            # Assessment is OK if it has basic structure and either:
            # 1. Identified specific risks with actions, OR
            # 2. Explicitly shows low risk with proper assessment
            basic_quality = has_assessment_structure and has_valid_overall_score
            detailed_analysis = has_risks and (has_priorities or has_actions)
            proper_low_risk = (
                not has_risks and overall and str(overall).lower() == "low"
            )

            ok = basic_quality and (detailed_analysis or proper_low_risk)

            return {
                "ok": ok,
                "total_risks_identified": total,
                "overall_risk_score": str(overall) if overall is not None else None,
                "high_priority_count": len(high_priority_risks),
                "recommended_actions_count": len(recommended_actions),
                "diagram_sources_count": len(diagram_sources),
                "quality_checks": quality_checks,
                "reason": "passed" if ok else "insufficient_analysis_quality",
            }

        except Exception as e:
            return {"ok": False, "reason": "evaluation_error", "error": str(e)}

    async def _update_state_success(self, state, parsed: Any, quality: Dict[str, Any]):
        value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        state["diagram_risks"] = value

        # Log success metrics for monitoring
        metrics = {
            "total_risks": quality.get("total_risks_identified", 0),
            "overall_risk_score": quality.get("overall_risk_score"),
            "high_priority_count": quality.get("high_priority_count", 0),
            "diagram_sources_count": quality.get("diagram_sources_count", 0),
        }

        progress_message = (
            f"Diagram risks assessed - {metrics['total_risks']} risks identified"
        )
        if metrics["overall_risk_score"]:
            progress_message += f" (Overall: {metrics['overall_risk_score']})"

        self._log_step_debug(
            "Diagram risk assessment completed successfully", state, metrics
        )

        await self.emit_progress(state, self.progress_range[1], progress_message)
        return {"diagram_risks": value}
