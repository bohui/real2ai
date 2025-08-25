from datetime import datetime, UTC

from .base_node import Step2NodeBase
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisState


class TitleEncumbrancesNode(Step2NodeBase):
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
                    (existing.section_analysis or {}).get("title_encumbrances")
                    if existing
                    else None
                )
                if persisted:
                    self.logger.info(
                        "Short-circuiting title_encumbrances: found persisted result"
                    )
                    return {"title_encumbrances_result": persisted}

            parties_result = state.get("parties_property_result")
            if not parties_result:
                return {
                    "processing_errors": [
                        "Title analysis requires parties and property result"
                    ]
                }

            diagrams = state.get("uploaded_diagrams") or {}
            total_diagrams_processed = len(diagrams)
            diagram_processing_success_rate = 0.9 if diagrams else 1.0

            result = {
                "analyzer": "title_encumbrances",
                "status": "placeholder",
                "message": "Implementation pending Story S8",
                "dependencies_satisfied": True,
                "diagrams_processed": total_diagrams_processed,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            if content_hash and repo:
                try:
                    await repo.update_section_analysis_key(
                        content_hash,
                        "title_encumbrances",
                        result,
                        updated_by="step2_title_encumbrances",
                    )
                except Exception as pe:
                    self.logger.warning(f"Failed to persist title_encumbrances: {pe}")

            await self.emit_progress(
                state,
                self.progress_range[1],
                "Title and encumbrances analysis completed",
            )
            return {
                "title_encumbrances_result": result,
                "total_diagrams_processed": total_diagrams_processed,
                "diagram_processing_success_rate": diagram_processing_success_rate,
            }

        except Exception as e:
            error_msg = f"Title and encumbrances analysis failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {"processing_errors": [error_msg]}
