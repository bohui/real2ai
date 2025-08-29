"""
Base node for Step 2 Section Analysis subflow

Provides consistent logging, error handling, and progress emission utilities
mirroring the document processing subflow's base node, adapted to Step 2 state.
"""

from app.agents.nodes.base import BaseNode


class Step2NodeBase(BaseNode):
    pass
    # def __init__(self, node_name: str, progress_range: tuple[int, int] | None = None):
    #     self.node_name = node_name
    #     self.logger = logging.getLogger(f"{__name__}.{node_name}")
    #     self.progress_range = progress_range or (0, 100)
    #     self.progress_callback: Optional[Callable[[str, int, str], Awaitable[None]]] = (
    #         None
    #     )

    # def set_progress_callback(self, callback):
    #     self.progress_callback = callback

    # async def emit_progress(self, state: Step2AnalysisState, percent: int, desc: str):
    #     try:
    #         notify = (state or {}).get("notify_progress")
    #         if notify and callable(notify):
    #             await notify(self.node_name, percent, desc)
    #     except Exception as e:
    #         self.logger.debug(f"Progress emit failed: {e}")

    # def _now_iso(self) -> str:
    #     return datetime.now(UTC).isoformat()

    # def _error_update(self, message: str) -> Dict[str, Any]:
    #     return {"processing_errors": [message]}

    # @abstractmethod
    # async def execute(self, state: Step2AnalysisState) -> Step2AnalysisState:
    #     raise NotImplementedError
