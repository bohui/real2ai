from datetime import datetime, UTC

from .base_node import Step2NodeBase
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState


class AdjustmentsOutgoingsNode(Step2NodeBase):
    def __init__(self, progress_range: tuple[int, int] = (77, 83)):
        super().__init__("calculate_adjustments_outgoings", progress_range)

    async def execute(self, state: Step2AnalysisState) -> Step2AnalysisState:
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
                persisted = (
                    (existing.section_analysis or {}).get("adjustments_outgoings")
                    if existing
                    else None
                )
                if persisted:
                    self.logger.info(
                        "Short-circuiting adjustments_outgoings: found persisted result"
                    )
                    return {"adjustments_outgoings_result": persisted}

            financial_result = state.get("financial_terms_result")
            settlement_result = state.get("settlement_logistics_result")
            if not financial_result or not settlement_result:
                return {
                    "processing_errors": [
                        "Adjustments calculation requires financial and settlement results"
                    ]
                }

            result = {
                "analyzer": "adjustments_outgoings",
                "status": "placeholder",
                "message": "Implementation pending Story S9",
                "dependencies_satisfied": True,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            if content_hash and repo:
                try:
                    await repo.update_section_analysis_key(
                        content_hash,
                        "adjustments_outgoings",
                        result,
                        updated_by="step2_adjustments_outgoings",
                    )
                except Exception as pe:
                    self.logger.warning(
                        f"Failed to persist adjustments_outgoings: {pe}"
                    )

            await self.emit_progress(
                state,
                self.progress_range[1],
                "Adjustments and outgoings calculation completed",
            )
            return {"adjustments_outgoings_result": result}

        except Exception as e:
            error_msg = f"Adjustments and outgoings calculation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {"processing_errors": [error_msg]}
