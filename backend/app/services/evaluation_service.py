"""
Production-ready LLM Evaluation Service.

This service provides comprehensive LLM evaluation capabilities including:
- Prompt testing and comparison
- Model performance evaluation
- A/B testing framework
- Batch processing
- Real-time monitoring
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json

from app.clients.base.interfaces import AIOperations
from app.clients.factory import get_openai_client, get_gemini_client
from app.core.langsmith_config import langsmith_trace, langsmith_session, get_langsmith_config
from app.core.config import get_settings
from app.dependencies.supabase import get_supabase_client

logger = logging.getLogger(__name__)


class EvaluationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MetricType(str, Enum):
    TRADITIONAL = "traditional"
    AI_ASSISTED = "ai_assisted" 
    CUSTOM = "custom"
    PERFORMANCE = "performance"


@dataclass
class EvaluationConfig:
    """Configuration for evaluation jobs."""
    job_id: str
    prompt_template_id: str
    dataset_id: str
    model_configs: List[Dict[str, Any]]
    metrics_config: Dict[str, Any]
    batch_size: int = 10
    timeout_seconds: int = 300
    retry_attempts: int = 3
    parallel_workers: int = 5


@dataclass
class EvaluationResult:
    """Single evaluation result."""
    id: str
    job_id: str
    test_case_id: str
    model_name: str
    prompt_used: str
    generated_response: str
    response_time_ms: int
    token_usage: int
    metrics_scores: Dict[str, float]
    langsmith_run_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = None


class MetricsCalculator:
    """Production-ready metrics calculation engine."""
    
    def __init__(self, judge_client: AIOperations):
        self.judge_client = judge_client
        self.settings = get_settings()
        
    async def calculate_all_metrics(
        self,
        generated_response: str,
        expected_output: Optional[str],
        input_context: Dict[str, Any],
        metrics_config: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate all enabled metrics for a response."""
        scores = {}
        
        try:
            # Traditional metrics
            if metrics_config.get("bleu_enabled", False) and expected_output:
                scores["bleu"] = await self._calculate_bleu(generated_response, expected_output)
            
            if metrics_config.get("rouge_enabled", False) and expected_output:
                rouge_scores = await self._calculate_rouge(generated_response, expected_output)
                scores.update(rouge_scores)
            
            if metrics_config.get("semantic_similarity_enabled", True) and expected_output:
                scores["semantic_similarity"] = await self._calculate_semantic_similarity(
                    generated_response, expected_output
                )
            
            # AI-assisted metrics
            if metrics_config.get("faithfulness_enabled", True):
                scores["faithfulness"] = await self._calculate_faithfulness(
                    generated_response, input_context
                )
            
            if metrics_config.get("relevance_enabled", True):
                scores["relevance"] = await self._calculate_relevance(
                    generated_response, input_context
                )
            
            if metrics_config.get("coherence_enabled", True):
                scores["coherence"] = await self._calculate_coherence(generated_response)
            
            # Custom metrics
            for metric_name in metrics_config.get("custom_metrics", []):
                scores[metric_name] = await self._calculate_custom_metric(
                    metric_name, generated_response, input_context
                )
            
            # Calculate overall score
            scores["overall_score"] = self._calculate_overall_score(scores, metrics_config)
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            scores["error"] = str(e)
        
        return scores
    
    async def _calculate_bleu(self, generated: str, reference: str) -> float:
        """Calculate BLEU score."""
        try:
            from nltk.translate.bleu_score import sentence_bleu
            import nltk
            
            # Download required NLTK data if not present
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt')
            
            reference_tokens = [reference.lower().split()]
            candidate_tokens = generated.lower().split()
            
            if not candidate_tokens:
                return 0.0
            
            return sentence_bleu(reference_tokens, candidate_tokens)
        except Exception as e:
            logger.error(f"BLEU calculation error: {e}")
            return 0.0
    
    async def _calculate_rouge(self, generated: str, reference: str) -> Dict[str, float]:
        """Calculate ROUGE scores."""
        try:
            from rouge_score import rouge_scorer
            
            scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
            scores = scorer.score(reference, generated)
            
            return {
                "rouge1": scores['rouge1'].fmeasure,
                "rouge2": scores['rouge2'].fmeasure,
                "rougeL": scores['rougeL'].fmeasure
            }
        except Exception as e:
            logger.error(f"ROUGE calculation error: {e}")
            return {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}
    
    async def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity using embeddings."""
        try:
            from sentence_transformers import SentenceTransformer
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            
            # Use a lightweight model for production
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embeddings = model.encode([text1, text2])
            
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"Semantic similarity calculation error: {e}")
            return 0.0
    
    @langsmith_trace(name="faithfulness_evaluation", run_type="llm")
    async def _calculate_faithfulness(
        self, 
        generated_text: str, 
        input_context: Dict[str, Any]
    ) -> float:
        """Calculate faithfulness score using LLM-as-judge."""
        try:
            context_str = json.dumps(input_context, indent=2)
            
            prompt = f"""
            Evaluate if the generated text is factually consistent with the provided context.
            
            Context:
            {context_str}
            
            Generated Text:
            {generated_text}
            
            Rate faithfulness from 0.0 to 1.0 where:
            - 1.0: Completely faithful, no contradictions or hallucinations
            - 0.8: Mostly faithful with minor inconsistencies
            - 0.6: Generally faithful but some questionable claims
            - 0.4: Partially faithful with notable inconsistencies
            - 0.2: Largely unfaithful with major contradictions
            - 0.0: Completely unfaithful or contradictory
            
            Consider:
            - Factual accuracy against the context
            - Absence of hallucinated information
            - Consistency with provided data
            
            Respond with only a number between 0.0 and 1.0.
            """
            
            response = await self.judge_client.generate_content(prompt, temperature=0.1)
            score = float(response.strip())
            return max(0.0, min(1.0, score))  # Clamp to valid range
            
        except Exception as e:
            logger.error(f"Faithfulness calculation error: {e}")
            return 0.5  # Default neutral score on error
    
    @langsmith_trace(name="relevance_evaluation", run_type="llm")
    async def _calculate_relevance(
        self, 
        generated_text: str, 
        input_context: Dict[str, Any]
    ) -> float:
        """Calculate relevance score using LLM-as-judge."""
        try:
            context_str = json.dumps(input_context, indent=2)
            
            prompt = f"""
            Evaluate how relevant the generated text is to the input context and query.
            
            Context:
            {context_str}
            
            Generated Text:
            {generated_text}
            
            Rate relevance from 0.0 to 1.0 where:
            - 1.0: Perfectly relevant and directly addresses the context
            - 0.8: Highly relevant with minor tangential content
            - 0.6: Generally relevant but somewhat unfocused
            - 0.4: Partially relevant with significant off-topic content
            - 0.2: Minimally relevant, mostly off-topic
            - 0.0: Completely irrelevant
            
            Consider:
            - Direct relevance to the query or context
            - Completeness of addressing the topic
            - Lack of irrelevant information
            
            Respond with only a number between 0.0 and 1.0.
            """
            
            response = await self.judge_client.generate_content(prompt, temperature=0.1)
            score = float(response.strip())
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"Relevance calculation error: {e}")
            return 0.5
    
    @langsmith_trace(name="coherence_evaluation", run_type="llm")
    async def _calculate_coherence(self, generated_text: str) -> float:
        """Calculate coherence score using LLM-as-judge."""
        try:
            prompt = f"""
            Evaluate the coherence and logical flow of the following text.
            
            Text:
            {generated_text}
            
            Rate coherence from 0.0 to 1.0 where:
            - 1.0: Perfect logical flow, clear structure, well-organized
            - 0.8: Good coherence with minor flow issues
            - 0.6: Generally coherent but some unclear transitions
            - 0.4: Partially coherent with notable logical gaps
            - 0.2: Poor coherence, confusing structure
            - 0.0: Incoherent, no logical flow
            
            Consider:
            - Logical progression of ideas
            - Clear transitions between concepts
            - Overall structural organization
            - Consistency of tone and style
            
            Respond with only a number between 0.0 and 1.0.
            """
            
            response = await self.judge_client.generate_content(prompt, temperature=0.1)
            score = float(response.strip())
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"Coherence calculation error: {e}")
            return 0.5
    
    async def _calculate_custom_metric(
        self, 
        metric_name: str, 
        generated_text: str, 
        input_context: Dict[str, Any]
    ) -> float:
        """Calculate custom domain-specific metrics."""
        try:
            if metric_name == "real_estate_accuracy":
                return await self._calculate_real_estate_accuracy(generated_text, input_context)
            elif metric_name == "legal_compliance":
                return await self._calculate_legal_compliance(generated_text, input_context)
            else:
                logger.warning(f"Unknown custom metric: {metric_name}")
                return 0.5
        except Exception as e:
            logger.error(f"Custom metric {metric_name} calculation error: {e}")
            return 0.5
    
    @langsmith_trace(name="real_estate_accuracy_evaluation", run_type="llm")
    async def _calculate_real_estate_accuracy(
        self, 
        generated_text: str, 
        input_context: Dict[str, Any]
    ) -> float:
        """Calculate real estate domain accuracy."""
        try:
            context_str = json.dumps(input_context, indent=2)
            
            prompt = f"""
            Evaluate the accuracy of real estate information in the generated text.
            
            Context Data:
            {context_str}
            
            Generated Text:
            {generated_text}
            
            Rate real estate accuracy from 0.0 to 1.0 considering:
            - Property details (price, size, location)
            - Market data accuracy
            - Legal requirements and compliance
            - Industry terminology usage
            - Calculation correctness (yields, ratios, etc.)
            
            1.0 = All real estate information is accurate
            0.0 = Real estate information is incorrect or misleading
            
            Respond with only a number between 0.0 and 1.0.
            """
            
            response = await self.judge_client.generate_content(prompt, temperature=0.1)
            score = float(response.strip())
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"Real estate accuracy calculation error: {e}")
            return 0.5
    
    def _calculate_overall_score(
        self, 
        scores: Dict[str, float], 
        metrics_config: Dict[str, Any]
    ) -> float:
        """Calculate weighted overall score."""
        try:
            weights = metrics_config.get("metric_weights", {})
            total_weight = 0.0
            weighted_sum = 0.0
            
            for metric, score in scores.items():
                if metric in ["error", "overall_score"]:
                    continue
                    
                weight = weights.get(metric, 1.0)
                weighted_sum += score * weight
                total_weight += weight
            
            if total_weight == 0:
                return 0.0
                
            return weighted_sum / total_weight
            
        except Exception as e:
            logger.error(f"Overall score calculation error: {e}")
            return 0.5


class EvaluationOrchestrator:
    """Production-ready evaluation orchestrator with job queue."""
    
    def __init__(self):
        self.settings = get_settings()
        self.supabase_client = None
        self.ai_clients = {}
        self.active_jobs = {}  # Track active jobs
        self.job_semaphore = asyncio.Semaphore(5)  # Limit concurrent jobs
        
    async def initialize(self):
        """Initialize the orchestrator."""
        try:
            self.supabase_client = await get_supabase_client()
            
            # Initialize AI clients
            self.ai_clients = {
                "openai": await get_openai_client(),
                "gemini": await get_gemini_client()
            }
            
            # Initialize metrics calculator with default judge model
            judge_client = self.ai_clients.get("openai") or self.ai_clients.get("gemini")
            self.metrics_calculator = MetricsCalculator(judge_client)
            
            logger.info("Evaluation orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize evaluation orchestrator: {e}")
            raise
    
    @langsmith_trace(name="create_evaluation_job", run_type="chain")
    async def create_evaluation_job(
        self,
        name: str,
        prompt_template_id: str,
        dataset_id: str,
        model_configs: List[Dict[str, Any]],
        metrics_config: Dict[str, Any],
        user_id: str
    ) -> str:
        """Create and queue a new evaluation job."""
        try:
            job_id = str(uuid.uuid4())
            
            # Create job record
            job_data = {
                "id": job_id,
                "name": name,
                "prompt_template_id": prompt_template_id,
                "dataset_id": dataset_id,
                "model_configs": json.dumps(model_configs),
                "metrics_config": json.dumps(metrics_config),
                "status": EvaluationStatus.PENDING.value,
                "progress": 0.0,
                "created_by": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "estimated_duration": self._estimate_job_duration(model_configs, dataset_id)
            }
            
            result = await self.supabase_client.table("evaluation_jobs").insert(job_data).execute()
            
            if not result.data:
                raise Exception("Failed to create evaluation job")
            
            # Queue job for execution
            asyncio.create_task(self._execute_job_with_semaphore(job_id))
            
            logger.info(f"Created evaluation job {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to create evaluation job: {e}")
            raise
    
    async def _execute_job_with_semaphore(self, job_id: str):
        """Execute job with concurrency limiting."""
        async with self.job_semaphore:
            await self._execute_evaluation_job(job_id)
    
    @langsmith_trace(name="execute_evaluation_job", run_type="chain")
    async def _execute_evaluation_job(self, job_id: str):
        """Execute a single evaluation job."""
        try:
            # Mark job as active
            self.active_jobs[job_id] = datetime.utcnow()
            
            # Update job status
            await self._update_job_status(job_id, EvaluationStatus.RUNNING)
            
            # Load job configuration
            job_data = await self._get_job_data(job_id)
            config = EvaluationConfig(
                job_id=job_id,
                prompt_template_id=job_data["prompt_template_id"],
                dataset_id=job_data["dataset_id"],
                model_configs=json.loads(job_data["model_configs"]),
                metrics_config=json.loads(job_data["metrics_config"])
            )
            
            # Load dataset
            test_cases = await self._load_test_dataset(config.dataset_id)
            prompt_template = await self._load_prompt_template(config.prompt_template_id)
            
            total_tasks = len(test_cases) * len(config.model_configs)
            completed_tasks = 0
            
            logger.info(f"Starting evaluation job {job_id} with {total_tasks} tasks")
            
            # Process in batches for better resource management
            for i in range(0, len(test_cases), config.batch_size):
                batch_cases = test_cases[i:i + config.batch_size]
                
                # Create tasks for this batch
                batch_tasks = []
                for test_case in batch_cases:
                    for model_config in config.model_configs:
                        task = self._evaluate_single_case(
                            config, prompt_template, test_case, model_config
                        )
                        batch_tasks.append(task)
                
                # Execute batch with timeout
                batch_results = await asyncio.wait_for(
                    asyncio.gather(*batch_tasks, return_exceptions=True),
                    timeout=config.timeout_seconds
                )
                
                # Store results and update progress
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Batch task failed: {result}")
                        continue
                    
                    if result:  # Skip None results
                        await self._store_evaluation_result(result)
                        completed_tasks += 1
                
                # Update progress
                progress = (completed_tasks / total_tasks) * 100
                await self._update_job_progress(job_id, progress)
                
                # Small delay between batches to prevent overwhelming
                await asyncio.sleep(0.1)
            
            # Mark job as completed
            await self._update_job_status(job_id, EvaluationStatus.COMPLETED)
            
            # Generate summary analytics
            await self._generate_job_summary(job_id)
            
            logger.info(f"Completed evaluation job {job_id}")
            
        except Exception as e:
            logger.error(f"Evaluation job {job_id} failed: {e}")
            await self._update_job_status(
                job_id, 
                EvaluationStatus.FAILED, 
                error_message=str(e)
            )
        finally:
            # Remove from active jobs
            self.active_jobs.pop(job_id, None)
    
    async def _evaluate_single_case(
        self,
        config: EvaluationConfig,
        prompt_template: Dict[str, Any],
        test_case: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> Optional[EvaluationResult]:
        """Evaluate a single test case with retry logic."""
        for attempt in range(config.retry_attempts):
            try:
                # Get AI client
                client_name = model_config.get("provider", "openai")
                ai_client = self.ai_clients.get(client_name)
                
                if not ai_client:
                    raise Exception(f"AI client {client_name} not available")
                
                # Render prompt
                rendered_prompt = self._render_prompt(
                    prompt_template["template_content"], 
                    test_case["input_data"]
                )
                
                # Generate response with timing
                start_time = time.time()
                
                with langsmith_session(
                    f"evaluation_{config.job_id}_{test_case['id']}_{model_config['model_name']}"
                ) as session:
                    session.inputs = {
                        "prompt": rendered_prompt[:500],  # Truncate for readability
                        "model": model_config["model_name"],
                        "test_case_id": test_case["id"]
                    }
                    
                    generated_response = await ai_client.generate_content(
                        rendered_prompt,
                        **model_config.get("parameters", {})
                    )
                    
                    response_time_ms = int((time.time() - start_time) * 1000)
                    
                    # Calculate metrics
                    metrics_scores = await self.metrics_calculator.calculate_all_metrics(
                        generated_response=generated_response,
                        expected_output=test_case.get("expected_output"),
                        input_context=test_case["input_data"],
                        metrics_config=config.metrics_config
                    )
                    
                    session.outputs = {
                        "response_length": len(generated_response),
                        "response_time_ms": response_time_ms,
                        "metrics_scores": metrics_scores
                    }
                    
                    return EvaluationResult(
                        id=str(uuid.uuid4()),
                        job_id=config.job_id,
                        test_case_id=test_case["id"],
                        model_name=model_config["model_name"],
                        prompt_used=rendered_prompt,
                        generated_response=generated_response,
                        response_time_ms=response_time_ms,
                        token_usage=self._estimate_token_usage(rendered_prompt, generated_response),
                        metrics_scores=metrics_scores,
                        langsmith_run_id=getattr(session, 'run_id', None),
                        created_at=datetime.utcnow()
                    )
                    
            except Exception as e:
                logger.warning(f"Evaluation attempt {attempt + 1} failed: {e}")
                if attempt == config.retry_attempts - 1:
                    # Return error result on final failure
                    return EvaluationResult(
                        id=str(uuid.uuid4()),
                        job_id=config.job_id,
                        test_case_id=test_case["id"],
                        model_name=model_config["model_name"],
                        prompt_used="ERROR",
                        generated_response="",
                        response_time_ms=0,
                        token_usage=0,
                        metrics_scores={"error": 1.0},
                        error_message=str(e),
                        created_at=datetime.utcnow()
                    )
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
        
        return None
    
    def _render_prompt(self, template: str, variables: Dict[str, Any]) -> str:
        """Render prompt template with variables."""
        try:
            # Simple template rendering - can be enhanced with Jinja2
            rendered = template
            for key, value in variables.items():
                placeholder = f"{{{key}}}"
                rendered = rendered.replace(placeholder, str(value))
            return rendered
        except Exception as e:
            logger.error(f"Failed to render prompt template: {e}")
            return template
    
    def _estimate_token_usage(self, prompt: str, response: str) -> int:
        """Estimate token usage for cost tracking."""
        # Rough estimation: ~4 characters per token
        return (len(prompt) + len(response)) // 4
    
    async def _load_test_dataset(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Load test dataset from database."""
        try:
            result = await self.supabase_client.table("test_cases")\
                .select("*")\
                .eq("dataset_id", dataset_id)\
                .execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Failed to load test dataset {dataset_id}: {e}")
            return []
    
    async def _load_prompt_template(self, template_id: str) -> Dict[str, Any]:
        """Load prompt template from database."""
        try:
            result = await self.supabase_client.table("prompt_templates")\
                .select("*")\
                .eq("id", template_id)\
                .eq("is_active", True)\
                .single()\
                .execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Failed to load prompt template {template_id}: {e}")
            return {}
    
    async def _store_evaluation_result(self, result: EvaluationResult):
        """Store evaluation result in database."""
        try:
            result_data = {
                "id": result.id,
                "job_id": result.job_id,
                "test_case_id": result.test_case_id,
                "model_name": result.model_name,
                "prompt_used": result.prompt_used,
                "generated_response": result.generated_response,
                "response_time_ms": result.response_time_ms,
                "token_usage": result.token_usage,
                "metrics_scores": json.dumps(result.metrics_scores),
                "langsmith_run_id": result.langsmith_run_id,
                "error_message": result.error_message,
                "created_at": result.created_at.isoformat()
            }
            
            await self.supabase_client.table("evaluation_results").insert(result_data).execute()
            
        except Exception as e:
            logger.error(f"Failed to store evaluation result: {e}")
    
    async def _get_job_data(self, job_id: str) -> Dict[str, Any]:
        """Get job data from database."""
        result = await self.supabase_client.table("evaluation_jobs")\
            .select("*")\
            .eq("id", job_id)\
            .single()\
            .execute()
        
        return result.data
    
    async def _update_job_status(
        self, 
        job_id: str, 
        status: EvaluationStatus, 
        error_message: Optional[str] = None
    ):
        """Update job status in database."""
        update_data = {"status": status.value}
        
        if status == EvaluationStatus.RUNNING:
            update_data["started_at"] = datetime.utcnow().isoformat()
        elif status in [EvaluationStatus.COMPLETED, EvaluationStatus.FAILED]:
            update_data["completed_at"] = datetime.utcnow().isoformat()
        
        if error_message:
            update_data["error_message"] = error_message
        
        await self.supabase_client.table("evaluation_jobs")\
            .update(update_data)\
            .eq("id", job_id)\
            .execute()
    
    async def _update_job_progress(self, job_id: str, progress: float):
        """Update job progress in database."""
        await self.supabase_client.table("evaluation_jobs")\
            .update({"progress": progress})\
            .eq("id", job_id)\
            .execute()
    
    def _estimate_job_duration(
        self, 
        model_configs: List[Dict[str, Any]], 
        dataset_id: str
    ) -> int:
        """Estimate job duration in seconds."""
        # Simple estimation based on model count and average processing time
        num_models = len(model_configs)
        estimated_cases = 100  # Default estimate
        avg_time_per_case = 5  # seconds
        
        return num_models * estimated_cases * avg_time_per_case
    
    async def _generate_job_summary(self, job_id: str):
        """Generate summary analytics for completed job."""
        try:
            # Get all results for this job
            result = await self.supabase_client.table("evaluation_results")\
                .select("*")\
                .eq("job_id", job_id)\
                .execute()
            
            results = result.data or []
            if not results:
                return
            
            # Calculate summary statistics
            total_results = len(results)
            successful_results = [r for r in results if not r.get("error_message")]
            
            summary = {
                "job_id": job_id,
                "total_evaluations": total_results,
                "successful_evaluations": len(successful_results),
                "success_rate": len(successful_results) / total_results if total_results > 0 else 0,
                "avg_response_time": sum(r["response_time_ms"] for r in successful_results) / len(successful_results) if successful_results else 0,
                "total_tokens": sum(r["token_usage"] for r in results),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # Calculate metric averages
            if successful_results:
                for result in successful_results:
                    metrics = json.loads(result["metrics_scores"])
                    for metric_name, score in metrics.items():
                        if isinstance(score, (int, float)):
                            key = f"avg_{metric_name}"
                            if key not in summary:
                                summary[key] = 0
                            summary[key] += score
                
                # Average the metrics
                for key in list(summary.keys()):
                    if key.startswith("avg_"):
                        summary[key] /= len(successful_results)
            
            # Store summary
            await self.supabase_client.table("evaluation_job_summaries")\
                .insert(summary)\
                .execute()
            
        except Exception as e:
            logger.error(f"Failed to generate job summary: {e}")
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get current job status and progress."""
        try:
            result = await self.supabase_client.table("evaluation_jobs")\
                .select("*")\
                .eq("id", job_id)\
                .single()\
                .execute()
            
            job_data = result.data
            
            # Add runtime information
            if job_id in self.active_jobs:
                job_data["is_active"] = True
                job_data["runtime_seconds"] = (
                    datetime.utcnow() - self.active_jobs[job_id]
                ).total_seconds()
            else:
                job_data["is_active"] = False
            
            return job_data
            
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return {}
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running evaluation job."""
        try:
            # Remove from active jobs (this will cause graceful shutdown)
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
            
            # Update status in database
            await self._update_job_status(job_id, EvaluationStatus.CANCELLED)
            
            logger.info(f"Cancelled evaluation job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False


# Global orchestrator instance
_orchestrator: Optional["EvaluationOrchestrator"] = None

async def get_evaluation_orchestrator() -> EvaluationOrchestrator:
    """Get the global evaluation orchestrator instance."""
    global _orchestrator
    
    if _orchestrator is None:
        _orchestrator = EvaluationOrchestrator()
        await _orchestrator.initialize()
    
    return _orchestrator