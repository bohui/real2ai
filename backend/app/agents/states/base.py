from typing import TypedDict, Optional, Callable, Annotated
from typing_extensions import Awaitable


class LangGraphBaseState(TypedDict):
    # Progress notification callback
    notify_progress: Annotated[
        Optional[Callable[[str, int, str], Awaitable[None]]],
        lambda x, y: y,
    ]
    content_hash: str
    content_hmac: Optional[str]
