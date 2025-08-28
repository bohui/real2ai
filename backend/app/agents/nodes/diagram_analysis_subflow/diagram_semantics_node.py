from typing import Any, Dict, List, Optional

from app.agents.nodes.contract_llm_base import ContractLLMNode
from app.core.langsmith_config import langsmith_trace
from app.agents.states.contract_state import RealEstateAgentState


class DiagramSemanticsNode(ContractLLMNode):
    def __init__(
        self,
        workflow,
        diagram_type: str,
        *,
        schema_confidence_threshold: float = 0.5,
        progress_range: tuple[int, int] = (0, 100),
    ):
        from app.prompts.schema.diagram_analysis.image_semantics_schema import (
            get_semantic_schema_class,
        )
        from app.schema.enums.diagrams import DiagramType

        # Get the appropriate schema class for this diagram type
        try:
            enum_type = DiagramType(diagram_type)
        except Exception:
            enum_type = DiagramType.UNKNOWN
        result_model = get_semantic_schema_class(enum_type)

        super().__init__(
            workflow=workflow,
            node_name=f"diagram_semantics_{diagram_type}",
            contract_attribute="image_semantics",
            result_model=result_model,
            progress_range=progress_range,
        )
        self.diagram_type = diagram_type
        self.schema_confidence_threshold = schema_confidence_threshold

    @langsmith_trace(name="diagram_semantics_execute", run_type="tool")
    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:  # type: ignore[override]
        """Override execute to handle image-specific processing while following ContractLLMNode workflow."""
        progress_update = self._get_progress_update(state)
        state.update(progress_update)

        try:
            self._log_step_debug("Starting diagram semantics node execution", state)

            # 1) Short-circuit check
            short_circuit = await self._short_circuit_check(state)
            if short_circuit is not None:
                return short_circuit

            # 2) Check for uploaded diagrams
            uploaded = state.get("uploaded_diagrams") or {}
            entries: List[Dict[str, Any]] = uploaded.get(self.diagram_type) or []
            if not isinstance(entries, list) or not entries:
                self._log_warning(
                    f"No {self.diagram_type} diagrams found; skipping node"
                )
                return self.update_state_step(
                    state,
                    f"{self.node_name}_skipped",
                    data={"reason": "no_diagrams_available"},
                )

            # 3) Download all diagrams available for this type
            downloads = await self._download_all_diagrams(entries)
            if not downloads:
                self._log_warning(
                    f"No downloadable {self.diagram_type} diagrams; skipping node"
                )
                return self.update_state_step(
                    state,
                    f"{self.node_name}_skipped",
                    data={"reason": "diagram_download_failed"},
                )

            # 4) Build context and parser
            context_vars, parser, composition_name = (
                await self._build_context_and_parser(state)
            )

            # 5) Get LLM service and fetch model configuration from prompt metadata
            llm_service = await self._get_llm_service()
            composition_result = await self.prompt_manager.render_composed(
                composition_name=composition_name,
                context=context_vars,
                output_parser=parser,
            )
            metadata = composition_result.get("metadata", {})

            primary_model = (
                metadata.get("primary_model")
                or metadata.get("model")
                or (metadata.get("model_compatibility", []) or [None])[0]
            )
            fallback_models = list(metadata.get("fallback_models") or [])
            if not fallback_models:
                compat = list(metadata.get("model_compatibility") or [])
                fallback_models = [m for m in compat if m and m != primary_model]

            max_retries = int(self.CONFIG_KEYS["max_retries"])

            # 6) Prepare a single batched LLM call with all images
            contents_list: List[Dict[str, Any]] = []
            uris: List[str] = []
            for item in downloads:
                uri = item.get("uri")
                content_bytes = item.get("content")
                ctype = item.get("content_type") or "image/jpeg"
                if not content_bytes:
                    self._log_warning(
                        "Skipping diagram with empty content",
                        state,
                        {"diagram_type": self.diagram_type, "uri": uri},
                    )
                    continue
                contents_list.append(
                    {
                        "content": content_bytes,
                        "content_type": ctype,
                        "filename": str(uri) if uri else None,
                    }
                )
                if uri:
                    uris.append(str(uri))

            if not contents_list:
                self._log_warning(
                    f"No valid {self.diagram_type} diagram contents to analyze; skipping node"
                )
                return self.update_state_step(
                    state,
                    f"{self.node_name}_skipped",
                    data={"reason": "no_valid_diagram_contents"},
                )

            # Enrich context with all image URIs and render prompts once
            batched_context = dict(context_vars)
            if uris:
                batched_context["image_uris"] = uris

            composition_batched = await self.prompt_manager.render_composed(
                composition_name=composition_name,
                context=batched_context,
                output_parser=parser,
            )
            analysis_prompt = composition_batched.get("user_prompt", "")
            system_prompt = composition_batched.get("system_prompt", "")

            parsing_result = await llm_service.generate_image_semantics(
                contents=contents_list,
                analysis_prompt=analysis_prompt,
                system_prompt=system_prompt,
                output_parser=parser,
                model=primary_model,
                parse_generation_max_attempts=max_retries,
            )

            parsed = (
                self._coerce_to_model(parsing_result.parsed_data)
                if getattr(parsing_result, "success", False)
                else None
            )
            quality = self._evaluate_quality(parsed, state)

            if parsed is None or not quality.get("ok"):
                # Not fatal; allow workflow to proceed gracefully
                self._log_warning(
                    "Image semantics parsing failed; skipping node result"
                )
                return self.update_state_step(
                    state,
                    f"{self.node_name}_skipped",
                    data={"reason": "parse_failed_or_low_quality"},
                )

            # 8) Persist results
            await self._persist_results(state, parsed)

            # 9) Update state
            return await self._update_state_success(state, parsed, quality)

        except Exception as e:
            self._log_exception(e, state, {"operation": f"{self.node_name}_execute"})
            return self._handle_node_error(
                state, e, f"{self.node_name} failed: {str(e)}"
            )

    async def _download_all_diagrams(
        self, entries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Download all diagrams from entries and return list of {uri, content, content_type}."""
        from app.utils.storage_utils import ArtifactStorageService

        results: List[Dict[str, Any]] = []
        if not isinstance(entries, list):
            return results

        storage_service = ArtifactStorageService()
        for item in entries:
            try:
                if not isinstance(item, dict):
                    continue
                uri = item.get("uri")
                if not isinstance(uri, str) or not uri.startswith("supabase://"):
                    continue
                content_bytes = await storage_service.download_page_image_jpg(str(uri))
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
                results.append(
                    {"uri": uri, "content": content_bytes, "content_type": ctype}
                )
            except Exception:
                # Skip failed downloads; higher-level logic will log as needed
                continue

        return results

    async def _evaluate_image_fallbacks(
        self,
        llm_service,
        parser,
        content_bytes: bytes,
        content_type: str,
        filename: str,
        composition_name: str,
        context_vars: Dict[str, Any],
        fallback_models: List[str],
        max_retries: int,
        parsed: Any,
        quality: Dict[str, Any],
        state: RealEstateAgentState,
    ) -> tuple[Any, Dict[str, Any]]:
        """Evaluate fallback models for image analysis."""
        for fallback_model in fallback_models:
            try:
                self._log_step_debug(
                    f"Trying fallback model {fallback_model} for image analysis",
                    state,
                    {"diagram_type": self.diagram_type},
                )

                fallback_result = await llm_service.generate_image_semantics(
                    content=content_bytes,
                    content_type=content_type,
                    filename=filename,
                    composition_name=composition_name,
                    context_variables=context_vars,
                    output_parser=parser,
                    model=fallback_model,
                    parse_generation_max_attempts=max_retries,
                )

                fallback_parsed = (
                    self._coerce_to_model(fallback_result.parsed_data)
                    if getattr(fallback_result, "success", False)
                    else None
                )
                fallback_quality = self._evaluate_quality(fallback_parsed, state)

                if fallback_quality.get("ok"):
                    self._log_step_debug(
                        f"Fallback model {fallback_model} succeeded",
                        state,
                        {"diagram_type": self.diagram_type},
                    )
                    return fallback_parsed, fallback_quality

            except Exception as fallback_err:
                self._log_warning(
                    f"Fallback model {fallback_model} failed: {fallback_err}",
                    state,
                    {"diagram_type": self.diagram_type},
                )
                continue

        return parsed, quality

    # --- ContractLLMNode pattern hooks ---
    async def _short_circuit_check(
        self, state: RealEstateAgentState
    ) -> Optional[RealEstateAgentState]:
        """Check for cached diagram-type-specific image semantics."""
        try:
            from app.services.repositories.contracts_repository import (
                ContractsRepository,
            )

            content_hash = state.get("content_hash")
            if not content_hash:
                return None

            contracts_repo = ContractsRepository()
            existing_contract = await contracts_repo.get_contract_by_content_hash(
                content_hash
            )
            if not existing_contract:
                return None

            # Check for diagram-type-specific cached value in image_semantics
            image_semantics = getattr(existing_contract, "image_semantics", None)
            if isinstance(image_semantics, dict):
                cached_value = image_semantics.get(self.diagram_type)
                if isinstance(cached_value, dict) and bool(cached_value):
                    # Store in state using diagram-type-specific structure
                    if "image_semantics" not in state:
                        state["image_semantics"] = {}
                    state["image_semantics"][self.diagram_type] = cached_value

                    # Extract confidence score if available
                    try:
                        metadata = cached_value.get("metadata", {})
                        overall_confidence = metadata.get("overall_confidence")
                        if overall_confidence is not None:
                            state.setdefault("confidence_scores", {})[
                                f"image_semantics_{self.diagram_type}"
                            ] = overall_confidence
                    except Exception:
                        pass

                    self._log_step_debug(
                        f"Skipping {self.node_name}; using cached {self.diagram_type} semantics",
                        state,
                        {
                            "content_hash": content_hash,
                            "diagram_type": self.diagram_type,
                        },
                    )
                    return self.update_state_step(
                        state,
                        f"{self.node_name}_skipped",
                        data={
                            "reason": "existing_cached_value",
                            "source": "contracts_cache",
                            "diagram_type": self.diagram_type,
                        },
                    )
        except Exception as check_err:
            self._log_warning(
                f"{self.__class__.__name__}: Idempotency check failed (non-fatal): {check_err}"
            )
        return None

    async def _build_context_and_parser(self, state: RealEstateAgentState):  # type: ignore[override]
        """Build context variables and parser for image analysis."""
        from app.core.prompts.parsers import create_parser

        # Build context variables
        context_vars = {
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

        # Add any seed snippets or diagram filenames
        if state.get("seed_snippets"):
            context_vars["seed_snippets"] = state["seed_snippets"]
        if state.get("diagram_filenames"):
            context_vars["diagram_filenames"] = state["diagram_filenames"]

        # Create parser
        parser = create_parser(
            self.result_model, strict_mode=False, retry_on_failure=True
        )

        # Select diagram-specific composition
        composition_name = f"step2_diagram_semantics_{self.diagram_type}"

        return context_vars, parser, composition_name

    async def _persist_results(self, state: RealEstateAgentState, parsed: Any) -> None:  # type: ignore[override]
        """Persist diagram-type-specific results using specialized repository method."""
        try:
            from app.services.repositories.contracts_repository import (
                ContractsRepository,
            )

            content_hash = state.get("content_hash")
            if not content_hash:
                self._log_warning(
                    f"{self.__class__.__name__}: Missing content_hash; skipping contract persist"
                )
                return

            # Use diagram-type-specific persistence to avoid conflicts
            value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
            repo = ContractsRepository()
            await repo.update_image_semantics_for_diagram_type(
                content_hash,
                self.diagram_type,
                value,
                updated_by=self.node_name,
            )
        except Exception as repo_err:
            self._log_warning(
                f"{self.__class__.__name__}: Diagram semantics persist failed (non-fatal): {repo_err}"
            )

    def _validate_content(self, result: Any) -> bool:
        """Validate that the diagram semantics result contains meaningful content."""
        try:
            if hasattr(result, "model_dump"):
                data = result.model_dump()
            else:
                data = result

            if not isinstance(data, dict):
                return False

            # Check for diagram-specific semantic content
            has_content = bool(
                data.get("textual_information")
                or data.get("spatial_relationships")
                or data.get("semantic_summary")
                or data.get("areas_of_concern")
                or data.get("key_findings")
            )

            return has_content

        except Exception:
            return False

    async def _update_state_success(
        self, state: RealEstateAgentState, parsed: Any, quality: Dict[str, Any]
    ) -> RealEstateAgentState:  # type: ignore[override]
        """Update state with diagram-type-specific results."""
        try:
            value = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        except Exception:
            value = None

        # Update state with diagram-type-specific structure
        if "image_semantics" not in state:
            state["image_semantics"] = {}
        state["image_semantics"][self.diagram_type] = value

        # Propagate confidence score for this specific diagram type
        try:
            confidence_score = getattr(parsed, "confidence_score", None)
            if confidence_score is not None:
                state.setdefault("confidence_scores", {})[
                    f"image_semantics_{self.diagram_type}"
                ] = confidence_score
        except Exception:
            pass

        return self.update_state_step(
            state,
            f"{self.node_name}_complete",
            data={
                "quality": quality,
                "diagram_type": self.diagram_type,
            },
        )
