from datetime import datetime, UTC

from .base_node import Step2NodeBase
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState


class DisclosureComplianceNode(Step2NodeBase):
    def __init__(
        self,
        workflow,
        node_name: str = "check_disclosure_compliance",
        progress_range: tuple[int, int] = (83, 89),
    ):
        super().__init__(workflow, node_name, progress_range)

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
                    (existing.section_analysis or {}).get("disclosure_compliance")
                    if existing
                    else None
                )
                if persisted:
                    self.logger.info(
                        "Short-circuiting disclosure_compliance: found persisted result"
                    )
                    return {"disclosure_compliance_result": persisted}

            result = {
                "analyzer": "disclosure_compliance",
                "status": "placeholder",
                "message": "Implementation pending Story S10",
                "timestamp": datetime.now(UTC).isoformat(),
            }

            if content_hash and repo:
                try:
                    await repo.update_section_analysis_key(
                        content_hash,
                        "disclosure_compliance",
                        result,
                        updated_by="step2_disclosure_compliance",
                    )
                except Exception as pe:
                    self.logger.warning(
                        f"Failed to persist disclosure_compliance: {pe}"
                    )

            await self.emit_progress(
                state, self.progress_range[1], "Disclosure compliance check completed"
            )
            return {"disclosure_compliance_result": result}

        except Exception as e:
            error_msg = f"Disclosure compliance check failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {"processing_errors": [error_msg]}
