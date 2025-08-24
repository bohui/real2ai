from datetime import datetime, UTC
from typing import Dict, Any

from .base_node import Step2NodeBase
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState


class FinancialTermsNode(Step2NodeBase):
    def __init__(self, progress_range: tuple[int, int] = (12, 22)):
        super().__init__("analyze_financial_terms", progress_range)

    async def execute(self, state: Step2AnalysisState) -> Step2AnalysisState:
        self.logger.info("Starting financial terms analysis")
        updates: Dict[str, Any] = {}
        try:
            from app.services.repositories.contracts_repository import (
                ContractsRepository,
            )

            content_hash = (state.get("entities_extraction") or {}).get(
                "content_hash"
            ) or (state.get("entities_extraction") or {}).get("document", {}).get(
                "content_hash"
            )
            repo = None
            if content_hash:
                repo = ContractsRepository()
                existing = await repo.get_contract_by_content_hash(content_hash)
                persisted = (existing.financial_terms or {}) if existing else None
                if persisted:
                    self.logger.info(
                        "Short-circuiting financial_terms: found persisted result"
                    )
                    return {"financial_terms_result": persisted}

            from app.core.prompts import PromptContext, ContextType
            from app.services import get_llm_service
            from app.prompts.schema.step2.financial_terms_schema import (
                FinancialTermsAnalysisResult,
            )

            context = PromptContext(
                context_type=ContextType.ANALYSIS,
                variables={
                    "contract_text": state.get("contract_text", ""),
                    "australian_state": state.get("australian_state", "NSW"),
                    "contract_type": state.get("contract_type", "purchase_agreement"),
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                    "entities_extraction": state.get("entities_extraction", {}),
                    "legal_requirements_matrix": state.get(
                        "legal_requirements_matrix", {}
                    ),
                },
            )

            financial_parser = await self._get_parser(
                "financial_terms_analysis", FinancialTermsAnalysisResult
            )
            composition_result = await self._get_prompt_manager().render_composed(
                composition_name="step2_financial_terms",
                context=context,
                output_parser=financial_parser,
            )

            system_prompt = composition_result.get(
                "system_prompt",
                "You are an expert Australian real estate financial analyst.",
            )
            user_prompt = composition_result.get(
                "user_prompt",
                f"Analyze financial terms in this contract: {context.variables.get('contract_text', '')}",
            )
            model_name = composition_result.get("metadata", {}).get("model", "gpt-4")

            llm_service = await get_llm_service()

            if financial_parser:
                parsing_result = await llm_service.generate_content(
                    prompt=user_prompt,
                    system_message=system_prompt,
                    model=model_name,
                    output_parser=financial_parser,
                    parse_generation_max_attempts=2,
                )

                if parsing_result.success and parsing_result.parsed_data:
                    result = parsing_result.parsed_data
                    result_dict = (
                        result.model_dump() if hasattr(result, "model_dump") else result
                    )
                    result_dict["analyzer"] = "financial_terms"
                    result_dict["status"] = "completed"
                    result_dict["timestamp"] = datetime.now(UTC).isoformat()
                    updates = {"financial_terms_result": result_dict}

                    if content_hash and repo:
                        try:
                            await repo.update_section_analysis_key(
                                content_hash,
                                "financial_terms",
                                result_dict,
                                updated_by="step2_financial_terms",
                            )
                        except Exception as pe:
                            self.logger.warning(
                                f"Failed to persist financial_terms: {pe}"
                            )

                    await self.emit_progress(
                        state,
                        self.progress_range[1],
                        "Financial terms analysis completed",
                    )
                else:
                    result = {
                        "analyzer": "financial_terms",
                        "status": "parsing_failed",
                        "error": "Failed to parse LLM output",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                    updates = {
                        "financial_terms_result": result,
                        "processing_errors": [
                            "Financial terms analysis: parsing failed"
                        ],
                    }
            else:
                response = await llm_service.generate_content(
                    prompt=user_prompt, system_message=system_prompt, model=model_name
                )
                result = {
                    "analyzer": "financial_terms",
                    "status": "unstructured",
                    "response": response,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                updates = {"financial_terms_result": result}

        except Exception as e:
            error_msg = f"Financial terms analysis failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            updates = {
                "financial_terms_result": {
                    "analyzer": "financial_terms",
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            }
            updates.setdefault("processing_errors", []).append(error_msg)

        return updates

    def _get_prompt_manager(self):
        from app.core.prompts import get_prompt_manager

        return get_prompt_manager()

    async def _get_parser(self, parser_name: str, schema_class):
        try:
            from app.core.prompts.parsers import create_parser

            return create_parser(schema_class, strict_mode=False, retry_on_failure=True)
        except Exception as e:
            self.logger.warning(f"Failed to create parser {parser_name}: {e}")
            return None
