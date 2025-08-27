from typing import Any, Dict, List
import asyncio

from app.agents.nodes.contract_llm_base import ContractLLMNode
from app.agents.nodes.diagram_analysis_subflow.diagram_semantics_node import (
    DiagramSemanticsNode,
)


class DiagramSemanticsFanoutNode(ContractLLMNode):
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
            contract_attribute="image_semantics",
            result_model=dict,
            progress_range=progress_range,
        )
        self.concurrency_limit = concurrency_limit

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[override]
        uploaded = state.get("uploaded_diagrams") or {}
        if not isinstance(uploaded, dict) or not uploaded:
            return {}

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
            return {}

        aggregate = {
            "images": per_type_results,
            "metadata": {
                "diagram_count": len(per_type_results),
                "diagram_types": [r.get("diagram_type") for r in per_type_results],
                "uris": [r.get("uri") for r in per_type_results],
            },
        }
        state["image_semantics"] = aggregate
        return {"image_semantics": aggregate}
