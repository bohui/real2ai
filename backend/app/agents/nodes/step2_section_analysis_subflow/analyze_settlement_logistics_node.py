from datetime import datetime, UTC

from .base_node import Step2NodeBase
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState


class SettlementLogisticsNode(Step2NodeBase):
    def __init__(self, progress_range: tuple[int, int] = (50, 60)):
        super().__init__("analyze_settlement_logistics", progress_range)

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
                    (existing.section_analysis or {}).get("settlement_logistics")
                    if existing
                    else None
                )
                if persisted:
                    self.logger.info(
                        "Short-circuiting settlement_logistics: found persisted result"
                    )
                    return {"settlement_logistics_result": persisted}

            # Check dependencies
            conditions_result = state.get("conditions_result")
            financial_result = state.get("financial_terms_result")
            if not conditions_result or not financial_result:
                return {
                    "processing_errors": [
                        "Settlement analysis requires conditions and financial results"
                    ]
                }

            result = {
                "analyzer": "settlement_logistics",
                "status": "placeholder",
                "message": "Implementation pending Story S7",
                "dependencies_satisfied": True,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            if content_hash and repo:
                try:
                    await repo.update_section_analysis_key(
                        content_hash,
                        "settlement_logistics",
                        result,
                        updated_by="step2_settlement_logistics",
                    )
                except Exception as pe:
                    self.logger.warning(f"Failed to persist settlement_logistics: {pe}")

            await self.emit_progress(
                state, self.progress_range[1], "Settlement logistics analysis completed"
            )
            return {"settlement_logistics_result": result}

        except Exception as e:
            error_msg = f"Settlement logistics analysis failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {"processing_errors": [error_msg]}
