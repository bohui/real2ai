from datetime import datetime, UTC

from .base_node import Step2NodeBase
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState


class SpecialRisksNode(Step2NodeBase):
    def __init__(self, progress_range: tuple[int, int] = (89, 94)):
        super().__init__("identify_special_risks", progress_range)

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
                    (existing.section_analysis or {}).get("special_risks")
                    if existing
                    else None
                )
                if persisted:
                    self.logger.info(
                        "Short-circuiting special_risks: found persisted result"
                    )
                    return {"special_risks_result": persisted}

            result = {
                "analyzer": "special_risks",
                "status": "placeholder",
                "message": "Implementation pending Story S11",
                "timestamp": datetime.now(UTC).isoformat(),
            }

            if content_hash and repo:
                try:
                    await repo.update_section_analysis_key(
                        content_hash,
                        "special_risks",
                        result,
                        updated_by="step2_special_risks",
                    )
                except Exception as pe:
                    self.logger.warning(f"Failed to persist special_risks: {pe}")

            await self.emit_progress(
                state, self.progress_range[1], "Special risks identification completed"
            )
            return {"special_risks_result": result}

        except Exception as e:
            error_msg = f"Special risks identification failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {"processing_errors": [error_msg]}
