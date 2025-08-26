from datetime import datetime, UTC
from typing import Any, Optional, Dict

from app.agents.subflows.step2_section_analysis_workflow import (
    Step2AnalysisState,
    Step2AnalysisWorkflow,
)
from app.agents.nodes.contract_llm_base import ContractLLMNode


class AnalyzeDiagramNode(ContractLLMNode):
    def __init__(
        self,
        workflow: Step2AnalysisWorkflow,
        progress_range: tuple[int, int] = (52, 58),
    ):
        super().__init__(
            workflow=workflow,
            node_name="analyze_diagram",
            contract_attribute="image_semantics",
            state_field="image_semantics_result",
        )
        self.progress_range = progress_range

    def _flatten_seeds(self, raw: Any) -> list[str]:
        items: list[str] = []
        try:
            if raw is None:
                return []
            if isinstance(raw, str):
                return [raw]
            if isinstance(raw, list):
                for it in raw:
                    if isinstance(it, str):
                        items.append(it)
                    elif isinstance(it, dict):
                        txt = (
                            it.get("snippet_text")
                            or it.get("text")
                            or it.get("content")
                            or ""
                        )
                        if isinstance(txt, str) and txt:
                            items.append(txt)
            if isinstance(raw, dict):
                for v in raw.values():
                    items.extend(self._flatten_seeds(v))
        except Exception:
            return items
        return items

    def _score_seed(
        self, text: str, entities: Dict[str, Any], state: Step2AnalysisState
    ) -> float:
        if not isinstance(text, str) or not text:
            return 0.0
        t = text.lower()
        score = 0.0
        # Keyword match for diagram-relevant terms
        keywords = [
            "easement",
            "sewer",
            "drain",
            "stormwater",
            "water main",
            "gas",
            "electric",
            "telecom",
            "boundary",
            "title",
            "encumbrance",
            "right of way",
            "flood",
            "bushfire",
            "overlay",
            "setback",
        ]
        for k in keywords:
            if k in t:
                score += 1.0

        # Boost by legal requirements matrix topics
        try:
            lrm = state.get("legal_requirements_matrix") or {}
            lrm_terms = (
                " ".join([str(x).lower() for x in lrm.keys()])
                if isinstance(lrm, dict)
                else ""
            )
            if any(k in t for k in lrm_terms.split() if k):
                score += 1.0
        except Exception:
            pass

        # Boost by entities terms (address/lot/plan/title)
        try:
            ent_texts = []
            for v in (entities or {}).values():
                if isinstance(v, str):
                    ent_texts.append(v.lower())
                elif isinstance(v, dict):
                    for vv in v.values():
                        if isinstance(vv, str):
                            ent_texts.append(vv.lower())
            if any(e in t for e in ent_texts if e):
                score += 0.5
        except Exception:
            pass

        # Penalize overly long seeds
        if len(text) > 500:
            score -= 0.25
        return score

    def _select_filtered_seeds(
        self,
        raw: Any,
        entities: Dict[str, Any],
        state: Step2AnalysisState,
        max_items: int = 7,
        max_chars: int = 2000,
    ) -> list[str]:
        items = self._flatten_seeds(raw)
        dedup: dict[str, str] = {}
        for it in items:
            if not isinstance(it, str):
                continue
            trimmed = it.strip()
            if not trimmed:
                continue
            key = trimmed[:120].lower()
            if key not in dedup:
                # truncate individual seed to ~250 chars for focus
                dedup[key] = trimmed[:250]
        scored = sorted(
            dedup.values(),
            key=lambda s: self._score_seed(s, entities, state),
            reverse=True,
        )
        selected: list[str] = []
        total = 0
        for s in scored:
            if len(selected) >= max_items:
                break
            if total + len(s) > max_chars:
                continue
            selected.append(s)
            total += len(s)
        return selected

    async def _short_circuit_check(
        self, state: Step2AnalysisState
    ) -> Optional[Step2AnalysisState]:
        # First, run base idempotency check (contracts cache)
        base = await super()._short_circuit_check(state)  # type: ignore[misc]
        if base is not None:
            return base

        # If there are no uploaded diagrams, try to load from artifacts; skip if still empty
        try:
            uploaded = state.get("uploaded_diagrams") or {}
            if not uploaded:
                await self._ensure_uploaded_diagrams(state)
                uploaded = state.get("uploaded_diagrams") or {}
                if not uploaded:
                    return self.update_state_step(
                        state,
                        f"{self.node_name}_skipped",
                        data={
                            "reason": "no_uploaded_diagrams",
                            "contract_attribute": self.contract_attribute,
                        },
                    )
        except Exception:
            # If any issue accessing state, proceed without short-circuiting
            pass
        return None

    async def _ensure_uploaded_diagrams(self, state: Step2AnalysisState) -> None:
        """Populate state.uploaded_diagrams from artifacts if empty.

        Loads diagram/image artifacts by content hash/HMAC and downloads image bytes
        into a mapping of filename -> bytes. Best-effort; logs are handled by base.
        """
        try:
            if (state.get("uploaded_diagrams") or {}) and isinstance(
                state.get("uploaded_diagrams"), dict
            ):
                return

            content_hmac = state.get("content_hash") or state.get("content_hmac")
            if not content_hmac:
                return

            # Repositories and storage service
            from app.services.repositories.artifacts_repository import (
                ArtifactsRepository,
            )
            from app.utils.storage_utils import ArtifactStorageService

            artifacts_repo = ArtifactsRepository()
            storage_service = ArtifactStorageService()

            # Fetch diagram artifacts (includes diagrams and images)
            diagram_artifacts = (
                await artifacts_repo.get_diagram_artifacts_by_content_hmac(content_hmac)
            )
            if not diagram_artifacts:
                return

            result: Dict[str, bytes] = {}
            for art in diagram_artifacts:
                try:
                    uri = getattr(art, "image_uri", None)
                    key = getattr(art, "diagram_key", None) or "diagram"
                    page = getattr(art, "page_number", None)
                    filename = (
                        f"{key}_p{page}.bin" if page is not None else f"{key}.bin"
                    )
                    if uri:
                        # Only download known storage URIs
                        content = await storage_service.download_blob(uri)
                        if isinstance(content, (bytes, bytearray)):
                            result[filename] = bytes(content)
                except Exception:
                    continue

            if result:
                state["uploaded_diagrams"] = result
                state["total_diagrams_processed"] = len(result)
        except Exception:
            # Best-effort; do not raise
            pass

    async def _build_context_and_parser(self, state: Step2AnalysisState):
        from app.core.prompts import PromptContext, ContextType
        from app.core.prompts.parsers import create_parser
        from app.prompts.schema.image_semantics_schema import ImageSemantics

        entities = state.get("entities_extraction", {}) or {}
        meta: Dict[str, Any] = (entities or {}).get("metadata") or {}

        # Text-only LLM node: we cannot pass binary images; focus on semantics guidance
        section_seeds = (state.get("section_seeds", {}) or {}).get("snippets", {})
        # Only use title_encumbrances seeds (we do not maintain a dedicated diagram seed set)
        encumbrance_seeds = section_seeds.get("title_encumbrances")
        uploaded = state.get("uploaded_diagrams") or {}
        diagram_filenames = list(uploaded.keys()) if isinstance(uploaded, dict) else []

        # Filter and compress seeds to a small, high-signal subset
        filtered_seeds = self._select_filtered_seeds(encumbrance_seeds, entities, state)
        context = PromptContext(
            context_type=ContextType.ANALYSIS,
            variables={
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "contract_text": state.get("contract_text", ""),
                "australian_state": state.get("australian_state")
                or meta.get("state")
                or "NSW",
                "contract_type": state.get("contract_type")
                or meta.get("contract_type")
                or "purchase_agreement",
                "use_category": state.get("use_category") or meta.get("use_category"),
                "purchase_method": state.get("purchase_method")
                or meta.get("purchase_method"),
                "property_condition": state.get("property_condition")
                or meta.get("property_condition"),
                "legal_requirements_matrix": state.get("legal_requirements_matrix", {}),
                "retrieval_index_id": state.get("retrieval_index_id"),
                "seed_snippets": filtered_seeds if filtered_seeds else None,
                "entities_extraction": entities,
                "diagram_filenames": diagram_filenames,
                # steer the analysis; can be refined later
                "analysis_focus": "comprehensive",
            },
        )

        parser = create_parser(ImageSemantics, strict_mode=False, retry_on_failure=True)
        # Use a dedicated composition with a diagram-specific system prompt
        return context, parser, "step2_diagram_semantics"

    def _coerce_to_model(self, data: Any) -> Optional[Any]:
        try:
            from app.prompts.schema.image_semantics_schema import ImageSemantics

            if isinstance(data, ImageSemantics):
                return data
            if hasattr(data, "model_validate"):
                return ImageSemantics.model_validate(data)
        except Exception:
            return None
        return None

    def _evaluate_quality(
        self, result: Optional[Any], state: Step2AnalysisState
    ) -> Dict[str, Any]:
        if result is None:
            return {"ok": False}
        try:
            # Basic heuristic: presence of summary and at least one element list populated
            summary_ok = bool(getattr(result, "semantic_summary", "") or "")
            any_elements = any(
                len(getattr(result, field, []) or []) > 0
                for field in (
                    "infrastructure_elements",
                    "boundary_elements",
                    "environmental_elements",
                    "building_elements",
                    "other_elements",
                )
            )
            ok = summary_ok or any_elements
            return {
                "ok": ok,
                "summary_present": summary_ok,
                "has_elements": any_elements,
            }
        except Exception:
            return {"ok": False}

    async def _update_state_success(
        self, state: Step2AnalysisState, parsed: Any, quality: Dict[str, Any]
    ) -> Step2AnalysisState:
        value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        state["image_semantics_result"] = value

        # Update simple diagram processing metrics based on availability
        try:
            uploaded = state.get("uploaded_diagrams") or {}
            total = len(uploaded) if isinstance(uploaded, dict) else 0
            state["total_diagrams_processed"] = total
            state["diagram_processing_success_rate"] = 1.0 if total > 0 else 0.0
        except Exception:
            pass

        await self.emit_progress(
            state, self.progress_range[1], "Diagram semantics analyzed"
        )
        return {"image_semantics_result": value}
