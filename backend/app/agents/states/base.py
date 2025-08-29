from typing import TypedDict, Optional, Callable, Annotated
from typing_extensions import Awaitable


class LangGraphBaseState(TypedDict):
    # Progress notification callback
    notify_progress: Annotated[
        Optional[Callable[[str, int, str], Awaitable[None]]],
        lambda x, y: y,
    ]
    # Content identification fields - must be annotated for concurrent updates
    content_hash: Annotated[
        str, lambda x, y: y
    ]  # Last value wins for concurrent updates
    content_hmac: Annotated[
        Optional[str], lambda x, y: y
    ]  # Last value wins for concurrent updates
