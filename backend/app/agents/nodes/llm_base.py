"""
Abstract LLMNode that encapsulates common LLM workflow steps for nodes:

- short-circuit checks (idempotency/cache)
- building PromptContext
- rendering composed prompts
- invoking LLM with primary/fallback models from metadata
- quality evaluation and backup calling
- persistence hooks
- state update

Concrete nodes implement small hooks only, avoiding magic numbers and reusing config.
"""

import logging
from abc import abstractmethod
from typing import Any, Dict, Optional, Tuple, List

from app.agents.states.contract_state import RealEstateAgentState
from .base import BaseNode

logger = logging.getLogger(__name__)


class LLMNode(BaseNode):
    """
    Abstract base for LLM-driven nodes. Subclasses provide domain-specific hooks.
    """

    # Config keys expected in workflow.extraction_config
    CONFIG_KEYS = {
        "max_retries": 2,
        "min_confidence": 0.5,
    }

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:  # type: ignore[override]
        progress_update = self._get_progress_update(state)
        state.update(progress_update)

        try:
            self._log_step_debug("Starting LLM node execution", state)

            # 1) Short-circuit
            short_circuit = await self._short_circuit_check(state)
            if short_circuit is not None:
                return short_circuit

            # 2) Build context
            context, parser, composition_name = await self._build_context_and_parser(
                state
            )

            # 3) Render prompts
            composition_result = await self.prompt_manager.render_composed(
                composition_name=composition_name,
                context=context,
                output_parser=parser,
            )
            rendered_prompt = composition_result["user_prompt"]
            system_prompt = composition_result.get("system_prompt", "")
            metadata = composition_result.get("metadata", {})

            # Determine primary and fallback models from metadata
            primary_model = (
                metadata.get("primary_model")
                or metadata.get("model")
                or (metadata.get("model_compatibility", []) or [None])[0]
            )
            fallback_models = list(metadata.get("fallback_models") or [])
            if not fallback_models:
                compat = list(metadata.get("model_compatibility") or [])
                fallback_models = [m for m in compat if m and m != primary_model]

            # 4) LLM call with retries for parsing
            llm_service = await self._get_llm_service()
            # Use static defaults; do not depend on workflow/node extraction_config
            max_retries = int(self.CONFIG_KEYS["max_retries"])

            parsing_result = await llm_service.generate_content(
                prompt=rendered_prompt,
                system_message=system_prompt,
                model=primary_model,
                output_parser=parser,
                parse_generation_max_attempts=max_retries,
            )

            parsed = (
                self._coerce_to_model(parsing_result.parsed_data)
                if getattr(parsing_result, "success", False)
                else None
            )
            quality = self._evaluate_quality(parsed, state)

            # 5) Backup call if quality not passed
            if not quality.get("ok") and fallback_models:
                parsed, quality = await self._evaluate_fallbacks(
                    llm_service,
                    parser,
                    rendered_prompt,
                    system_prompt,
                    fallback_models,
                    max_retries,
                    parsed,
                    quality,
                    state,
                )

            if parsed is None:
                # Not fatal; allow workflow to proceed gracefully
                self._log_warning("LLM parsing failed; skipping node result")
                return self.update_state_step(
                    state,
                    f"{self.node_name}_skipped",
                    data={"reason": "parse_failed_or_empty"},
                )

            # 6) Persist domain-specific fields
            await self._persist_results(state, parsed)

            # 7) Update state
            return await self._update_state_success(state, parsed, quality)

        except Exception as e:
            self._log_exception(e, state, {"operation": f"{self.node_name}_execute"})
            return self._handle_node_error(
                state, e, f"{self.node_name} failed: {str(e)}"
            )

    # ---------- Hooks to implement in subclasses ----------

    @abstractmethod
    async def _short_circuit_check(
        self, state: RealEstateAgentState
    ) -> Optional[RealEstateAgentState]:
        """Return updated state to short-circuit, or None to continue."""

    @abstractmethod
    async def _build_context_and_parser(
        self, state: RealEstateAgentState
    ) -> Tuple[Any, Any, str]:
        """Return (PromptContext, parser, composition_name)."""

    @abstractmethod
    def _coerce_to_model(self, data: Any) -> Optional[Any]:
        """Coerce parsed object into target Pydantic model or None."""

    @abstractmethod
    def _evaluate_quality(
        self, result: Optional[Any], state: RealEstateAgentState
    ) -> Dict[str, Any]:
        """Return quality dict including key 'ok' boolean."""

    @abstractmethod
    async def _persist_results(self, state: RealEstateAgentState, parsed: Any) -> None:
        """Persist important artifacts/results to repositories if needed."""

    @abstractmethod
    async def _update_state_success(
        self, state: RealEstateAgentState, parsed: Any, quality: Dict[str, Any]
    ) -> RealEstateAgentState:
        """Update state for success and return it."""

    # ---------- Shared helpers ----------

    async def _get_llm_service(self):
        from app.services import get_llm_service

        return await get_llm_service()

    async def _evaluate_fallbacks(
        self,
        llm_service: Any,
        parser: Any,
        rendered_prompt: str,
        system_prompt: str,
        fallback_models: List[str],
        max_retries: int,
        current_parsed: Optional[Any],
        current_quality: Dict[str, Any],
        state: RealEstateAgentState,
    ) -> Tuple[Optional[Any], Dict[str, Any]]:
        def _score(q: Dict[str, Any]) -> float:
            conf = q.get("overall_confidence")
            cov = q.get("coverage_score", 0.0)
            return (conf if isinstance(conf, (int, float)) else 0.0) * 0.7 + cov * 0.3

        best_parsed = current_parsed
        best_quality = current_quality

        self._log_warning(
            "Primary model quality low; evaluating fallback models",
            state=state,
            details={
                "fallback_models": fallback_models,
                "primary_quality": current_quality,
            },
        )

        for fb_model in fallback_models:
            try:
                fb = await llm_service.generate_content(
                    prompt=rendered_prompt,
                    system_message=system_prompt,
                    model=fb_model,
                    output_parser=parser,
                    parse_generation_max_attempts=max_retries,
                )
                if (
                    getattr(fb, "success", False)
                    and getattr(fb, "parsed_data", None) is not None
                ):
                    fb_parsed = self._coerce_to_model(fb.parsed_data)
                    if fb_parsed is not None:
                        fb_quality = self._evaluate_quality(fb_parsed, state)
                        if _score(fb_quality) > _score(best_quality):
                            best_parsed = fb_parsed
                            best_quality = fb_quality
            except Exception as inner_err:
                logger.warning(
                    f"{self.node_name}: fallback model '{fb_model}' failed: {inner_err}"
                )

        return best_parsed, best_quality
