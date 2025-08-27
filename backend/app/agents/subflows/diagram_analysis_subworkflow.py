"""
Diagram Analysis Sub-Workflow

Performs three staged steps:
1) Preparation: download diagram artifacts and group by diagram_type
2) Semantics fan-out: analyze best page per diagram type using DIAGRAM_SEMANTICS_MAPPING
3) Risk assessment: aggregate semantic results into DiagramRiskAssessment

Updates Step2AnalysisState with:
- uploaded_diagrams (grouped by diagram_type)
- image_semantics (aggregate per-type results)
- diagram_risk_assessment (risk model output)
"""

from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Tuple
import traceback
import logging

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from app.agents.states.section_analysis_state import Step2AnalysisState
from app.agents.nodes.diagram_analysis_subflow.prepare_diagrams_node import (
    PrepareDiagramsNode,
)
from app.agents.nodes.diagram_analysis_subflow.diagram_semantics_fanout_node import (
    DiagramSemanticsFanoutNode,
)


logger = logging.getLogger(__name__)


class DiagramAnalysisSubWorkflow:
    def __init__(self, concurrency_limit: int = 5):
        self.graph: Optional[CompiledStateGraph] = None
        self.concurrency_limit = concurrency_limit
        self._build_graph()

    def _build_graph(self) -> None:
        graph = StateGraph(Step2AnalysisState)
        graph.add_node("prepare_diagrams", self.prepare_diagrams)
        graph.add_node("analyze_semantics", self.analyze_semantics)
        graph.add_node("assess_risks", self.assess_risks)

        graph.add_edge(START, "prepare_diagrams")
        graph.add_edge("prepare_diagrams", "analyze_semantics")
        graph.add_edge("analyze_semantics", "assess_risks")
        graph.add_edge("assess_risks", END)

        self.graph = graph.compile()

    async def run(self, state: Step2AnalysisState) -> Step2AnalysisState:
        assert self.graph is not None
        return await self.graph.ainvoke(state)

    async def prepare_diagrams(self, state: Step2AnalysisState) -> Step2AnalysisState:
        node = PrepareDiagramsNode(workflow=self)
        await node.execute(state)
        return state

    async def analyze_semantics(self, state: Step2AnalysisState) -> Step2AnalysisState:
        # Build context for downstream nodes (if needed later)
        await self._build_shared_context(state)
        fanout = DiagramSemanticsFanoutNode(
            workflow=self, concurrency_limit=self.concurrency_limit
        )
        await fanout.execute(state)
        return state

    async def assess_risks(self, state: Step2AnalysisState) -> Step2AnalysisState:
        aggregate = state.get("image_semantics") or {}
        if not aggregate:
            return state
        risk_value = await self._build_risk_assessment(state, aggregate)
        if risk_value is not None:
            state["diagram_risks"] = risk_value
        return state

    async def _prepare_uploaded_diagrams(self, state: Step2AnalysisState) -> None:
        try:
            if (state.get("uploaded_diagrams") or {}) and isinstance(
                state.get("uploaded_diagrams"), dict
            ):
                return

            content_hmac = state.get("content_hmac")
            if not content_hmac:
                try:
                    content_hash = state.get("content_hash")
                    if not content_hash:
                        return

                    from app.core.auth_context import AuthContext
                    from app.services.repositories.documents_repository import (
                        DocumentsRepository,
                    )
                    from app.clients.factory import get_service_supabase_client
                    from app.utils.content_utils import compute_content_hmac

                    user_id = AuthContext.get_user_id() or state.get("user_id")
                    docs_repo = DocumentsRepository(user_id=user_id)
                    docs = await docs_repo.get_documents_by_content_hash(
                        content_hash,
                        str(user_id) if user_id else "",
                        columns="storage_path",
                    )
                    if not docs:
                        return

                    storage_path = (
                        (docs[0] or {}).get("storage_path")
                        if isinstance(docs[0], dict)
                        else getattr(docs[0], "storage_path", None)
                    )
                    if not storage_path:
                        return

                    client = await get_service_supabase_client()
                    file_content = await client.download_file(
                        bucket="documents", path=storage_path
                    )
                    if not isinstance(file_content, (bytes, bytearray)):
                        file_content = (
                            bytes(file_content, "utf-8")
                            if isinstance(file_content, str)
                            else bytes(file_content)
                        )

                    content_hmac = compute_content_hmac(bytes(file_content))
                    state["content_hmac"] = content_hmac
                except Exception:
                    return

            from app.services.repositories.artifacts_repository import (
                ArtifactsRepository,
            )

            artifacts_repo = ArtifactsRepository()

            try:
                diagram_artifacts = (
                    await artifacts_repo.get_diagram_artifacts_by_content_hmac(
                        state.get("content_hmac")
                    )
                )
            except Exception as e:
                logger.warning(
                    f"Diagram artifacts fetch failed: {e}\n{traceback.format_exc()}"
                )
                return

            if not diagram_artifacts:
                return

            # Group by diagram_type
            result: Dict[str, List[Dict[str, Any]]] = {}
            for art in diagram_artifacts:
                try:
                    uri = getattr(art, "image_uri", None)
                    key = getattr(art, "diagram_key", None) or "diagram"
                    page = getattr(art, "page_number", None)
                    diagram_meta = getattr(art, "diagram_meta", {}) or {}
                    d_type = (
                        (diagram_meta.get("diagram_type") or "unknown").strip()
                        if isinstance(diagram_meta.get("diagram_type"), str)
                        else "unknown"
                    )
                    if uri:
                        if d_type not in result:
                            result[d_type] = []
                        result[d_type].append(
                            {
                                "uri": uri,
                                "confidence": diagram_meta.get("confidence", 0.5),
                                "page_number": page,
                                "diagram_key": key,
                            }
                        )
                except Exception:
                    continue

            if result:
                state["uploaded_diagrams"] = result
                state["total_diagrams_processed"] = len(result)
        except Exception:
            return

    async def _build_shared_context(
        self, state: Step2AnalysisState
    ) -> Tuple[Dict[str, Any], str]:
        entities = state.get("extracted_entity", {}) or {}
        meta: Dict[str, Any] = (entities or {}).get("metadata") or {}

        uploaded = state.get("uploaded_diagrams") or {}
        diagram_types = list(uploaded.keys()) if isinstance(uploaded, dict) else []
        diagram_uris: List[str] = []
        if isinstance(uploaded, dict):
            try:
                seen: set[str] = set()
                for _dtype, entries in uploaded.items():
                    if not isinstance(entries, list):
                        continue
                    for entry in entries:
                        if isinstance(entry, dict):
                            uri = entry.get("uri")
                            if isinstance(uri, str) and uri and uri not in seen:
                                seen.add(uri)
                                diagram_uris.append(uri)
            except Exception:
                pass

        context_vars: Dict[str, Any] = {
            "analysis_timestamp": datetime.now(UTC).isoformat(),
            "contract_text": state.get("contract_text", ""),
            "australian_state": state.get("australian_state")
            or meta.get("state")
            or "NSW",
            "contract_type": state.get("contract_type")
            or meta.get("contract_type")
            or "purchase_agreement",
            "use_category": state.get("use_category") or meta.get("use_category"),
            "purchase_method": state.get("purchase_method")
            or meta.get("purchase_method"),
            "property_condition": state.get("property_condition")
            or meta.get("property_condition"),
            "legal_requirements_matrix": state.get("legal_requirements_matrix", {}),
            "retrieval_index_id": state.get("retrieval_index_id"),
            "extracted_entity": entities,
            "diagram_uris": diagram_uris,
            "diagram_types": diagram_types,
            "analysis_focus": "comprehensive",
        }

        return context_vars, "step2_diagram_semantics"

    async def _analyze_all_types(
        self,
        uploaded: Dict[str, List[Dict[str, Any]]],
        context_vars: Dict[str, Any],
        composition_name: str,
    ) -> List[Dict[str, Any]]:
        import asyncio
        from app.agents.nodes.diagram_analysis_subflow.diagram_semantics_node import (
            DiagramSemanticsNode,
        )

        async def analyze_one(diagram_type: str, entries: List[Dict[str, Any]]):
            try:
                node = DiagramSemanticsNode(workflow=self, diagram_type=diagram_type)
                # Inject uploaded_diagrams into a minimal state view for the node
                node_state: Dict[str, Any] = {"uploaded_diagrams": uploaded}
                # The node's analyze returns a dict with uri, diagram_type, semantics
                return await node.analyze(node_state)
            except Exception:
                self._log_warning(
                    f"Failed to analyze diagram type {diagram_type}: {traceback.format_exc()}"
                )
                return None

        # Concurrency control with semaphore
        semaphore = asyncio.Semaphore(getattr(self, "concurrency_limit", 5))

        async def bounded(diagram_type: str, entries: List[Dict[str, Any]]):
            async with semaphore:
                return await analyze_one(diagram_type, entries)

        tasks = [bounded(dt, lst) for dt, lst in uploaded.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        per_type_results: List[Dict[str, Any]] = []
        for r in results:
            if isinstance(r, Exception) or r is None:
                continue
            per_type_results.append(r)
        return per_type_results

    async def _build_risk_assessment(
        self, state: Step2AnalysisState, aggregate: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        try:
            from app.agents.nodes.diagram_analysis_subflow.diagram_risk_node import (
                DiagramRiskNode,
            )

            node = DiagramRiskNode(workflow=self)
            return await node.assess(state, aggregate)
        except Exception:
            return None
