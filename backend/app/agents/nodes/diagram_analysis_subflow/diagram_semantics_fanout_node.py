from typing import Any, Dict, List
import asyncio

from app.agents.nodes.base import BaseNode
from app.agents.nodes.diagram_analysis_subflow.diagram_semantics_node import (
    DiagramSemanticsNode,
)


class DiagramSemanticsFanoutNode(BaseNode):
    def __init__(
        self,
        workflow,
        *,
        progress_range: tuple[int, int] = (0, 100),
        concurrency_limit: int = 5,
    ):
        super().__init__(
            workflow=workflow,
            node_name="diagram_semantics_fanout",
            progress_range=progress_range,
        )
        self.concurrency_limit = concurrency_limit

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            self._log_step_debug("Starting diagram semantics fanout", state)

            uploaded = state.get("uploaded_diagrams") or {}
            if not isinstance(uploaded, dict) or not uploaded:
                self._log_step_debug("No uploaded diagrams found, skipping", state)
                return self.update_state_step(
                    state,
                    "diagram_semantics_fanout_skipped",
                    data={"reason": "no_uploaded_diagrams"},
                )

            semaphore = asyncio.Semaphore(self.concurrency_limit)

            async def bounded(diagram_type: str, entries: List[Dict[str, Any]]):
                async with semaphore:
                    node = DiagramSemanticsNode(
                        workflow=self.workflow, diagram_type=diagram_type
                    )
                    node_state: Dict[str, Any] = {"uploaded_diagrams": uploaded}
                    return await node.execute(node_state)

            tasks = [bounded(dt, lst) for dt, lst in uploaded.items()]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            per_type_results: List[Dict[str, Any]] = []
            for r in results:
                if isinstance(r, Exception) or r is None:
                    continue
                per_type_results.append(r)

            if not per_type_results:
                self._log_step_debug("No valid results from diagram analysis", state)
                return self.update_state_step(
                    state,
                    "diagram_semantics_fanout_no_results",
                    data={"reason": "no_valid_results"},
                )

            aggregate = {
                "images": per_type_results,
                "metadata": {
                    "diagram_count": len(per_type_results),
                    "diagram_types": [r.get("diagram_type") for r in per_type_results],
                    "uris": [r.get("uri") for r in per_type_results],
                },
            }
            state["image_semantics"] = aggregate

            self._log_step_debug(
                "Diagram semantics fanout completed",
                state,
                {
                    "diagram_count": len(per_type_results),
                    "diagram_types": aggregate["metadata"]["diagram_types"],
                },
            )

            return self.update_state_step(
                state,
                "diagram_semantics_fanout_complete",
                data={"diagram_count": len(per_type_results), "aggregate": aggregate},
            )

        except Exception as e:
            return self._handle_node_error(state, e, "Diagram semantics fanout failed")
