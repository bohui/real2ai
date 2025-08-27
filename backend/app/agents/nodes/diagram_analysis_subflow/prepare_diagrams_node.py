from typing import Any, Dict, List, Optional
import traceback

from app.agents.nodes.base import BaseNode


class PrepareDiagramsNode(BaseNode):
    def __init__(self, workflow, *, progress_range: tuple[int, int] = (0, 100)):
        super().__init__(
            workflow=workflow,
            node_name="prepare_diagrams",
            progress_range=progress_range,
        )

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[override]
        try:
            if (state.get("uploaded_diagrams") or {}) and isinstance(
                state.get("uploaded_diagrams"), dict
            ):
                return {}

            content_hmac = state.get("content_hmac")
            if not content_hmac:
                try:
                    content_hash = state.get("content_hash")
                    if not content_hash:
                        return {}

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
                        return {}

                    storage_path = (
                        (docs[0] or {}).get("storage_path")
                        if isinstance(docs[0], dict)
                        else getattr(docs[0], "storage_path", None)
                    )
                    if not storage_path:
                        return {}

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
                    return {}

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
                self._log_warning(
                    f"Diagram artifacts fetch failed: {e}\n{traceback.format_exc()}"
                )
                return {}

            if not diagram_artifacts:
                return {}

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

            return {}
        except Exception:
            return {}
