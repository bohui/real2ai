from datetime import datetime, UTC
from typing import Dict, Any

from .base_node import Step2NodeBase
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState


class DefaultTerminationNode(Step2NodeBase):
    def __init__(self, progress_range: tuple[int, int] = (40, 48)):
        super().__init__("analyze_default_termination", progress_range)

    async def execute(self, state: Step2AnalysisState) -> Step2AnalysisState:
        self.logger.info("Starting default and termination analysis")
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
                persisted = (existing.default_termination or {}) if existing else None
                if persisted:
                    self.logger.info(
                        "Short-circuiting default_termination: found persisted result"
                    )
                    return {"default_termination_result": persisted}

            result = {
                "analyzer": "default_termination",
                "status": "placeholder",
                "message": "Implementation pending Story S6",
                "timestamp": datetime.now(UTC).isoformat(),
            }

            if content_hash and repo:
                try:
                    await repo.update_section_analysis_key(
                        content_hash,
                        "default_termination",
                        result,
                        updated_by="step2_default_termination",
                    )
                except Exception as pe:
                    self.logger.warning(f"Failed to persist default_termination: {pe}")

            await self.emit_progress(
                state,
                self.progress_range[1],
                "Default and termination analysis completed",
            )
            return {"default_termination_result": result}

        except Exception as e:
            error_msg = f"Default and termination analysis failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {"processing_errors": [error_msg]}
