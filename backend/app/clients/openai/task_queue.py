"""
Async task queue for OpenAI calls with global pause on 429 rate limits.

This queue constrains concurrent LLM requests and, upon detecting a rate limit
error, pauses all queued tasks for an exponential backoff window with jitter.

Usage:

    queue = OpenAILLMQueueManager.get_queue(model_name)
    result = await queue.run_in_executor(lambda: client.chat.completions.create(...))

The queue is keyed by `model_name` so different models can have independent
concurrency and backoff behavior. A special key "__default__" is used if
`model_name` is not provided.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Awaitable, Callable, Dict, Optional

try:
    # Importing here to detect specific error types when available
    from openai import RateLimitError  # type: ignore
except Exception:  # pragma: no cover - optional import
    RateLimitError = None  # type: ignore


logger = logging.getLogger(__name__)


# Reasonable defaults; can be tuned via env/config if later exposed
MAX_CONCURRENT_TASKS = 4
RETRY_TIMES = 5
INITIAL_BACKOFF_SECONDS = 5


class OpenAILLMTaskQueue:
    """Queue with semaphore and global pause for OpenAI requests.

    This queue is safe to share across tasks. When a 429 is encountered,
    the queue pauses all tasks for a backoff duration with jitter and uses
    exponential backoff across retries.
    """

    def __init__(self, max_concurrent_tasks: int = MAX_CONCURRENT_TASKS):
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._lock = asyncio.Lock()
        self._paused = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially

    async def run_async(self, coro_factory: Callable[[], Awaitable[Any]]) -> Any:
        """Run an async operation within the queue with 429-aware retries.

        Args:
            coro_factory: A zero-arg callable returning an awaitable. The
                          operation will be retried on 429-like errors with
                          exponential backoff and jitter.
        """
        async with self.semaphore:
            retry_count = 0
            backoff_seconds = INITIAL_BACKOFF_SECONDS
            while retry_count <= RETRY_TIMES:
                await self._pause_event.wait()
                try:
                    return await coro_factory()
                except Exception as exc:  # noqa: BLE001 - we classify below
                    if self._is_rate_limit_error(exc):
                        logger.warning(
                            "429 rate limit hit, pausing all LLM tasks. Retry %s/%s",
                            retry_count + 1,
                            RETRY_TIMES,
                        )
                        jitter = random.uniform(0, 2.0 * INITIAL_BACKOFF_SECONDS)
                        await self._pause_all(backoff_seconds + jitter)
                        retry_count += 1
                        backoff_seconds *= 2
                    else:
                        # Non-429 error: still retry with backoff a few times
                        logger.warning(
                            "LLM call failed (non-429). Backing off and retrying. "
                            "Retry %s/%s: %s",
                            retry_count + 1,
                            RETRY_TIMES,
                            exc,
                        )
                        jitter = random.uniform(0, 2.0 * INITIAL_BACKOFF_SECONDS)
                        await asyncio.sleep(backoff_seconds + jitter)
                        retry_count += 1
                        backoff_seconds *= 2

            logger.error("Max retries exceeded for LLM operation")
            raise RuntimeError("Max retries exceeded for LLM operation")

    async def run_in_executor(self, func: Callable[[], Any]) -> Any:
        """Run a sync function in the default executor under queue control.

        This is useful for OpenAI's sync SDK methods executed via
        `run_in_executor` to avoid blocking the event loop, while still
        benefiting from queue concurrency and pause-on-429 behavior.
        """
        loop = asyncio.get_running_loop()
        return await self.run_async(lambda: loop.run_in_executor(None, func))

    def __call__(self, func: Callable[[], Any]) -> Any:
        """Synchronous call support when used outside async contexts.

        Prefer using `await run_async(...)` or `await run_in_executor(...)` in
        async contexts. This helper provides a fallback for sync callers.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            raise RuntimeError("Use 'await queue.run_async(...)' in async context")
        return asyncio.run(self.run_in_executor(func))

    async def _pause_all(self, seconds: float) -> None:
        async with self._lock:
            if not self._paused:
                self._paused = True
                self._pause_event.clear()
                logger.info(
                    "Pausing all OpenAI LLM tasks for %.1f seconds due to rate limit.",
                    seconds,
                )
                await asyncio.sleep(seconds)
                self._paused = False
                self._pause_event.set()
                logger.info("Resuming OpenAI LLM tasks after backoff.")

    def _is_rate_limit_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        if (
            "429" in message
            or "rate limit" in message
            or "too many requests" in message
        ):
            return True
        # Prefer SDK-specific error type when available
        if RateLimitError is not None and isinstance(exc, RateLimitError):
            return True
        return False


class OpenAILLMQueueManager:
    """Singleton-like manager for per-model task queues."""

    _queues: Dict[str, OpenAILLMTaskQueue] = {}

    @classmethod
    def get_queue(cls, model_name: Optional[str] = None) -> OpenAILLMTaskQueue:
        key = model_name or "__default__"
        if key not in cls._queues:
            cls._queues[key] = OpenAILLMTaskQueue()
        return cls._queues[key]
