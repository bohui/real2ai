from datetime import datetime, UTC
from typing import Any, Optional, Dict, List
import traceback

from app.agents.subflows.step2_section_analysis_workflow import (
    Step2AnalysisState,
    Step2AnalysisWorkflow,
)
from app.agents.nodes.contract_llm_base import ContractLLMNode


class AnalyzeDiagramNode(ContractLLMNode):
    """Node for analyzing diagrams and extracting semantic information from images.

    This node processes uploaded diagram images concurrently to extract structured
    semantic information. It supports multiple diagram types and uses confidence-based
    schema selection for optimal parsing.

    Features:
    - Concurrent image processing with configurable concurrency limits
    - Confidence-based schema selection for different diagram types
    - Automatic fallback to generic schemas for low-confidence detections
    - Robust error handling with per-image failure isolation

    Args:
        workflow: The parent workflow instance
        progress_range: Progress range tuple for workflow tracking
        schema_confidence_threshold: Minimum confidence for specific schema selection
        concurrency_limit: Maximum number of images to process simultaneously (default: 5)

    Performance:
    - Sequential processing: O(n) where n = number of images
    - Concurrent processing: O(n/c) where c = concurrency_limit
    - Typical speedup: 3-5x faster for multiple images
    """

    def __init__(
        self,
        workflow: Step2AnalysisWorkflow,
        progress_range: tuple[int, int] = (52, 58),
        schema_confidence_threshold: float = 0.5,
        concurrency_limit: int = 5,
    ):
        super().__init__(
            workflow=workflow,
            node_name="analyze_diagram",
            contract_attribute="image_semantics",
            state_field="image_semantics_result",
        )
        self.progress_range = progress_range
        self.schema_confidence_threshold = schema_confidence_threshold
        self.concurrency_limit = concurrency_limit

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

    async def execute(self, state: Step2AnalysisState) -> Step2AnalysisState:  # type: ignore[override]
        # Progress tick
        progress_update = self._get_progress_update(state)
        state.update(progress_update)

        try:
            self._log_step_debug("Starting diagram semantics analysis", state)

            # 1) Short-circuit and ensure diagram URIs
            short = await self._short_circuit_check(state)
            if short is not None:
                return short

            # Ensure uploaded diagrams are available in state
            await self._ensure_uploaded_diagrams(state)

            uploaded = state.get("uploaded_diagrams") or {}
            if not uploaded:
                # If still empty after ensure, skip gracefully
                return self.update_state_step(
                    state,
                    f"{self.node_name}_skipped",
                    data={"reason": "no_diagrams_available"},
                )

            # 2) Build context + composition (parser chosen per-image)
            context, parser, composition_name = await self._build_context_and_parser(
                state
            )
            # PromptContext -> raw dict variables
            try:
                context_vars = getattr(context, "variables", {}) if context else {}
            except Exception:
                context_vars = {}

            # 3) Call image semantics per diagram (download bytes on-demand)
            from app.utils.storage_utils import ArtifactStorageService
            import asyncio

            storage_service = ArtifactStorageService()
            llm_service = await self._get_llm_service()

            # Create tasks for concurrent processing
            async def process_single_image(uri, info_list):
                """Process a single image concurrently."""
                try:
                    # Determine best type hint for this URI (highest confidence)
                    diagram_type_hint: str = "unknown"
                    if isinstance(info_list, list) and info_list:
                        try:
                            best = max(
                                [i for i in info_list if isinstance(i, dict)],
                                key=lambda x: float(x.get("confidence", 0.0)),
                            )
                            diagram_type_hint = str(
                                best.get("diagram_type_hint", "unknown")
                            )
                        except Exception:
                            # Fall back to first available if any issue
                            first = next(
                                (i for i in info_list if isinstance(i, dict)), None
                            )
                            if first:
                                diagram_type_hint = str(
                                    first.get("diagram_type_hint", "unknown")
                                )

                    # Download bytes just-in-time
                    try:
                        if isinstance(uri, str) and uri.startswith("supabase://"):
                            content_bytes = (
                                await storage_service.download_page_image_jpg(uri)
                            )
                        else:
                            # Unsupported URI scheme here; skip gracefully
                            self._log_warning(
                                "Unsupported image URI scheme; expected supabase://",
                                extra={"uri": str(uri)},
                            )
                            return None
                    except Exception as dl_err:
                        self._log_warning(
                            "Failed to download image bytes",
                            extra={"error": str(dl_err), "uri": str(uri)},
                        )
                        return None

                    # Infer content-type from filename/uri
                    lower = str(uri).lower()
                    if lower.endswith(".png"):
                        ctype = "image/png"
                    elif lower.endswith(".jpg") or lower.endswith(".jpeg"):
                        ctype = "image/jpeg"
                    elif lower.endswith(".webp"):
                        ctype = "image/webp"
                    elif lower.endswith(".pdf"):
                        ctype = "application/pdf"
                    else:
                        ctype = "image/jpeg"

                    # Choose parser schema per diagram_type_hint and confidence
                    try:
                        from app.schema.enums.diagrams import DiagramType
                        from app.prompts.schema.image_semantics_schema import (
                            get_semantic_schema_class,
                            GenericDiagramSemantics,
                        )
                        from app.core.prompts.parsers import (
                            create_parser as _create_parser,
                        )

                        try:
                            # If confidence is low, fall back to generic schema
                            hint_conf = 0.0
                            try:
                                hint_conf = (
                                    float(best.get("confidence", 0.0))
                                    if isinstance(best, dict)
                                    else 0.0
                                )
                            except Exception:
                                hint_conf = 0.0

                            enum_type = DiagramType(diagram_type_hint)
                            if hint_conf < self.schema_confidence_threshold:
                                enum_type = DiagramType.UNKNOWN
                        except Exception:
                            enum_type = DiagramType.UNKNOWN
                        schema_cls = get_semantic_schema_class(enum_type)
                        per_image_parser = _create_parser(
                            schema_cls, strict_mode=False, retry_on_failure=True
                        )
                    except Exception:
                        per_image_parser = None

                    # Inject per-image variables (avoid full entities)
                    per_image_context_vars = dict(context_vars or {})
                    per_image_context_vars["image_type"] = diagram_type_hint
                    per_image_context_vars["diagram_type_confidence"] = (
                        float(best.get("confidence", 0.0))
                        if isinstance(best, dict)
                        else 0.0
                    )
                    # Provide placeholder metadata for prompt while image bytes are passed separately
                    per_image_context_vars.setdefault(
                        "image_data", {"source": "binary", "uri": uri}
                    )
                    # Avoid passing full entities per image request
                    per_image_context_vars.pop("entities_extraction", None)

                    result = await llm_service.generate_image_semantics(
                        content=content_bytes,
                        content_type=ctype,
                        filename=str(uri),
                        composition_name=composition_name,
                        context_variables=per_image_context_vars,
                        output_parser=per_image_parser,
                    )

                    # Collect parsed object (ParsingResult or str)
                    parsed_obj = None
                    if hasattr(result, "success"):
                        parsed_obj = getattr(result, "parsed_data", None)
                    else:
                        parsed_obj = result

                    # Coerce to model, then to dict
                    model_obj = self._coerce_to_model(parsed_obj)
                    if model_obj is None:
                        return None
                    payload = (
                        model_obj.model_dump()
                        if hasattr(model_obj, "model_dump")
                        else model_obj
                    )
                    return {
                        "uri": uri,
                        "diagram_type": diagram_type_hint,
                        "semantics": payload,
                    }
                except Exception as per_err:
                    self._log_warning(
                        "Image semantics failed for one diagram",
                        extra={"error": str(per_err), "uri": str(uri)},
                    )
                    return None

            # Create concurrent tasks for all images
            tasks = []
            semaphore = asyncio.Semaphore(self.concurrency_limit)

            async def process_with_semaphore(uri, info_list):
                """Process a single image with concurrency control."""
                async with semaphore:
                    return await process_single_image(uri, info_list)

            for uri, info_list in (
                uploaded.items() if isinstance(uploaded, dict) else []
            ):
                task = process_with_semaphore(uri, info_list)
                tasks.append(task)

            # Execute all tasks concurrently
            if tasks:
                self._log_step_debug(
                    f"Processing {len(tasks)} images concurrently with limit {self.concurrency_limit}",
                    state,
                )
                start_time = datetime.now(UTC)
                results = await asyncio.gather(*tasks, return_exceptions=True)
                end_time = datetime.now(UTC)
                processing_time = (end_time - start_time).total_seconds()

                self._log_step_debug(
                    f"Completed concurrent processing in {processing_time:.2f}s", state
                )

                # Filter out None results and exceptions
                per_image_results = []
                failed_count = 0
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        failed_count += 1
                        uri = (
                            list(uploaded.keys())[i]
                            if isinstance(uploaded, dict)
                            else f"image_{i}"
                        )
                        self._log_warning(
                            "Image processing task failed with exception",
                            extra={"error": str(result), "uri": str(uri)},
                        )
                    elif result is not None:
                        per_image_results.append(result)

                if failed_count > 0:
                    self._log_step_debug(
                        f"Processed {len(per_image_results)} images successfully, {failed_count} failed",
                        state,
                    )
            else:
                per_image_results = []

            if not per_image_results:
                return self.update_state_step(
                    state,
                    f"{self.node_name}_skipped",
                    data={"reason": "no_results_from_diagrams"},
                )

            aggregate = {
                "images": per_image_results,
                "metadata": {
                    "diagram_count": len(per_image_results),
                    "uris": [r.get("uri") for r in per_image_results],
                    "generated_at": datetime.now(UTC).isoformat(),
                },
            }

            # 4) Quality assessment (simple)
            quality = {"ok": True, "diagram_count": len(per_image_results)}

            # 5) Persist and update state
            await self._persist_results(state, aggregate)
            return await self._update_state_success(state, aggregate, quality)

        except Exception as e:
            self._log_exception(e, state, {"operation": f"{self.node_name}_execute"})
            return self._handle_node_error(
                state, e, f"{self.node_name} failed: {str(e)}"
            )

    async def _ensure_uploaded_diagrams(self, state: Step2AnalysisState) -> None:
        """Populate state.uploaded_diagrams from artifacts if empty.

        Stores a lightweight filename->uri mapping only (no binary content) to
        avoid memory overhead. This node is text-only and does not require raw
        image bytes. Best-effort; logs are handled by base.
        """
        try:
            if (state.get("uploaded_diagrams") or {}) and isinstance(
                state.get("uploaded_diagrams"), dict
            ):
                return

            # Prefer true content_hmac; if missing, compute it from original bytes using content_hash
            content_hmac = state.get("content_hmac")
            if not content_hmac:
                try:
                    content_hash = state.get("content_hash")
                    if not content_hash:
                        return

                    # Resolve storage_path via user-scoped documents repository
                    from app.core.auth_context import AuthContext
                    from app.services.repositories.documents_repository import (
                        DocumentsRepository,
                    )
                    from app.clients.factory import get_service_supabase_client
                    from app.utils.content_utils import compute_content_hmac

                    user_id = AuthContext.get_user_id() or state.get("user_id")
                    docs_repo = DocumentsRepository(user_id=user_id)
                    docs = await docs_repo.get_documents_by_content_hash(
                        content_hash,
                        str(user_id) if user_id else "",
                        columns="storage_path",
                    )
                    if not docs:
                        return

                    storage_path = (
                        (docs[0] or {}).get("storage_path")
                        if isinstance(docs[0], dict)
                        else getattr(docs[0], "storage_path", None)
                    )
                    if not storage_path:
                        return

                    # Download original bytes and compute HMAC
                    client = await get_service_supabase_client()
                    file_content = await client.download_file(
                        bucket="documents", path=storage_path
                    )
                    if not isinstance(file_content, (bytes, bytearray)):
                        file_content = (
                            bytes(file_content, "utf-8")
                            if isinstance(file_content, str)
                            else bytes(file_content)
                        )

                    content_hmac = compute_content_hmac(bytes(file_content))
                    state["content_hmac"] = content_hmac
                except Exception:
                    # Best-effort; if we cannot compute HMAC, skip artifact lookup
                    return

            # Repositories and storage service
            from app.services.repositories.artifacts_repository import (
                ArtifactsRepository,
            )

            artifacts_repo = ArtifactsRepository()

            # Fetch diagram artifacts (includes diagrams and images)
            self._log_step_debug(
                f"Fetching diagram artifacts for content_hmac: {content_hmac}", state
            )
            try:
                diagram_artifacts = (
                    await artifacts_repo.get_diagram_artifacts_by_content_hmac(
                        content_hmac
                    )
                )
                self._log_step_debug(
                    f"Successfully fetched {len(diagram_artifacts)} diagram artifacts",
                    state,
                )
            except Exception as e:
                self._log_warning(f"Error fetching diagram artifacts: {e}")
                self._log_warning(f"Error type: {type(e)}")

                self._log_warning(f"Traceback: {traceback.format_exc()}")
                return
            if not diagram_artifacts:
                return

            result: Dict[str, List[Dict[str, Any]]] = {}
            for art in diagram_artifacts:
                try:
                    uri = getattr(art, "image_uri", None)
                    key = getattr(art, "diagram_key", None) or "diagram"
                    page = getattr(art, "page_number", None)
                    diagram_meta = getattr(art, "diagram_meta", {}) or {}
                    if uri:
                        # Initialize list for this URI if it doesn't exist
                        if uri not in result:
                            result[uri] = []
                        # Store metadata including diagram type
                        result[uri].append(
                            {
                                "diagram_type_hint": diagram_meta.get(
                                    "diagram_type", "unknown"
                                ),
                                "confidence": diagram_meta.get("confidence", 0.5),
                                "page_number": page,
                                "diagram_key": key,
                            }
                        )
                except Exception:
                    continue

            if result:
                state["uploaded_diagrams"] = result
                state["total_diagrams_processed"] = len(result)
                # Log diagram types for debugging
                diagram_types = []
                for uri, diagram_list in result.items():
                    for diagram_info in diagram_list:
                        if (
                            isinstance(diagram_info, dict)
                            and "diagram_type_hint" in diagram_info
                        ):
                            diagram_types.append(diagram_info["diagram_type_hint"])
                self._log_step_debug(
                    f"Processed diagrams with types: {diagram_types}", state
                )
        except Exception as e:
            # Best-effort; do not raise
            pass

    async def _build_context_and_parser(self, state: Step2AnalysisState):
        from app.core.prompts import PromptContext, ContextType
        from app.core.prompts.parsers import create_parser
        from app.prompts.schema.image_semantics_schema import DiagramSemanticsBase

        entities = state.get("entities_extraction", {}) or {}
        meta: Dict[str, Any] = (entities or {}).get("metadata") or {}

        # Text-only LLM node: we cannot pass binary images; focus on semantics guidance
        section_seeds = (state.get("section_seeds", {}) or {}).get("snippets", {})
        # Only use title_encumbrances seeds (we do not maintain a dedicated diagram seed set)
        encumbrance_seeds = section_seeds.get("title_encumbrances")
        uploaded = state.get("uploaded_diagrams") or {}
        diagram_uris = list(uploaded.keys()) if isinstance(uploaded, dict) else []
        # Extract diagram types for analysis context
        diagram_types = []
        if isinstance(uploaded, dict):
            for uri, diagram_list in uploaded.items():
                if isinstance(diagram_list, list):
                    for diagram_info in diagram_list:
                        if (
                            isinstance(diagram_info, dict)
                            and "diagram_type_hint" in diagram_info
                        ):
                            diagram_types.append(diagram_info["diagram_type_hint"])

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
                "diagram_uris": diagram_uris,
                "diagram_types": diagram_types,
                # steer the analysis; can be refined later
                "analysis_focus": "comprehensive",
            },
        )

        parser = create_parser(
            DiagramSemanticsBase, strict_mode=False, retry_on_failure=True
        )
        # Use a dedicated composition with a diagram-specific system prompt
        return context, parser, "step2_diagram_semantics"

    def _coerce_to_model(self, data: Any) -> Optional[Any]:
        try:
            from app.prompts.schema.image_semantics_schema import DiagramSemanticsBase

            if isinstance(data, DiagramSemanticsBase):
                return data
            if hasattr(data, "model_validate"):
                return DiagramSemanticsBase.model_validate(data)
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
