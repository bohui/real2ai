"""
Evaluation Storage Module

Provides storage capabilities for LangSmith evaluation data and pipeline configurations.
"""

import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class EvaluationStorage(ABC):
    """Abstract base class for evaluation data storage operations."""

    @abstractmethod
    async def save_pipeline_config(
        self, pipeline_id: str, config: Dict[str, Any]
    ) -> None:
        """Save pipeline configuration."""
        pass

    @abstractmethod
    async def get_pipeline_config(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve pipeline configuration."""
        pass

    @abstractmethod
    async def save_evaluation_result(
        self, evaluation_id: str, result: Dict[str, Any]
    ) -> None:
        """Save evaluation result."""
        pass

    @abstractmethod
    async def get_evaluation_results(
        self, pipeline_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve evaluation results for a pipeline."""
        pass

    @abstractmethod
    async def delete_pipeline(self, pipeline_id: str) -> None:
        """Delete pipeline and associated data."""
        pass


class InMemoryEvaluationStorage(EvaluationStorage):
    """In-memory implementation of EvaluationStorage for testing and development."""

    def __init__(self):
        self._pipeline_configs: Dict[str, Dict[str, Any]] = {}
        self._evaluation_results: Dict[str, List[Dict[str, Any]]] = {}

    async def save_pipeline_config(
        self, pipeline_id: str, config: Dict[str, Any]
    ) -> None:
        """Save pipeline configuration to memory."""
        self._pipeline_configs[pipeline_id] = config
        logger.debug(f"Saved pipeline config for {pipeline_id}")

    async def get_pipeline_config(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve pipeline configuration from memory."""
        config = self._pipeline_configs.get(pipeline_id)
        logger.debug(f"Retrieved pipeline config for {pipeline_id}: {config is not None}")
        return config

    async def save_evaluation_result(
        self, evaluation_id: str, result: Dict[str, Any]
    ) -> None:
        """Save evaluation result to memory."""
        pipeline_id = result.get("pipeline_id", "default")
        if pipeline_id not in self._evaluation_results:
            self._evaluation_results[pipeline_id] = []
        
        self._evaluation_results[pipeline_id].append({
            "evaluation_id": evaluation_id,
            **result
        })
        logger.debug(f"Saved evaluation result {evaluation_id} for pipeline {pipeline_id}")

    async def get_evaluation_results(
        self, pipeline_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve evaluation results for a pipeline from memory."""
        results = self._evaluation_results.get(pipeline_id, [])
        limited_results = results[-limit:] if len(results) > limit else results
        logger.debug(f"Retrieved {len(limited_results)} results for pipeline {pipeline_id}")
        return limited_results

    async def delete_pipeline(self, pipeline_id: str) -> None:
        """Delete pipeline and associated data from memory."""
        self._pipeline_configs.pop(pipeline_id, None)
        self._evaluation_results.pop(pipeline_id, None)
        logger.debug(f"Deleted pipeline {pipeline_id}")


class NullEvaluationStorage(EvaluationStorage):
    """No-op implementation of EvaluationStorage that does nothing."""

    async def save_pipeline_config(
        self, pipeline_id: str, config: Dict[str, Any]
    ) -> None:
        """No-op save pipeline configuration."""
        logger.debug(f"NullStorage: Ignoring save_pipeline_config for {pipeline_id}")

    async def get_pipeline_config(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """No-op retrieve pipeline configuration."""
        logger.debug(f"NullStorage: No config available for {pipeline_id}")
        return None

    async def save_evaluation_result(
        self, evaluation_id: str, result: Dict[str, Any]
    ) -> None:
        """No-op save evaluation result."""
        logger.debug(f"NullStorage: Ignoring save_evaluation_result for {evaluation_id}")

    async def get_evaluation_results(
        self, pipeline_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """No-op retrieve evaluation results."""
        logger.debug(f"NullStorage: No results available for {pipeline_id}")
        return []

    async def delete_pipeline(self, pipeline_id: str) -> None:
        """No-op delete pipeline."""
        logger.debug(f"NullStorage: Ignoring delete_pipeline for {pipeline_id}")


# Default storage instance for testing/development
def get_default_storage() -> EvaluationStorage:
    """Get default storage implementation for development/testing."""
    return InMemoryEvaluationStorage()


def get_null_storage() -> EvaluationStorage:
    """Get null storage implementation that does nothing."""
    return NullEvaluationStorage()