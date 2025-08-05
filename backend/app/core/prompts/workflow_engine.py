"""
Workflow Execution Engine for Complex Prompt Compositions
Orchestrates multi-step prompt workflows with dependency management and parallel execution
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union, Set
from datetime import datetime, UTC
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager

from .context import PromptContext, ContextType
from .exceptions import PromptCompositionError, PromptServiceError
from .template import PromptTemplate

logger = logging.getLogger(__name__)


class WorkflowStepStatus(Enum):
    """Status of workflow step execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow"""
    name: str
    description: str
    template: str
    required_context: List[str] = field(default_factory=list)
    optional_context: List[str] = field(default_factory=list)
    input_variables: List[str] = field(default_factory=list)
    output_variable: str = None
    dependencies: List[str] = field(default_factory=list)
    parallel_with: List[str] = field(default_factory=list)
    timeout_seconds: int = 30
    critical: bool = True
    retry_count: int = 0
    max_retries: int = 2
    
    # Runtime state
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    

@dataclass
class WorkflowConfiguration:
    """Configuration for workflow execution"""
    name: str
    description: str
    version: str
    steps: List[WorkflowStep]
    system_prompts: List[Dict[str, Any]] = field(default_factory=list)
    output_template: Optional[str] = None
    validation_template: Optional[str] = None
    max_parallel_steps: int = 3
    step_timeout_seconds: int = 30
    max_tokens_total: int = 50000
    estimated_duration_seconds: int = 60
    enable_step_caching: bool = True
    cache_ttl_seconds: int = 1800
    save_partial_results: bool = True
    continue_on_non_critical_failure: bool = True
    

@dataclass
class WorkflowExecutionContext:
    """Context for workflow execution"""
    workflow_id: str
    configuration: WorkflowConfiguration
    base_context: PromptContext
    variables: Dict[str, Any] = field(default_factory=dict)
    step_results: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str = "initialized"
    error: Optional[str] = None
    completed_steps: Set[str] = field(default_factory=set)
    failed_steps: Set[str] = field(default_factory=set)
    skipped_steps: Set[str] = field(default_factory=set)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


class WorkflowExecutionEngine:
    """Executes complex prompt workflows with dependency management"""
    
    def __init__(self, prompt_manager):
        """Initialize workflow engine with prompt manager"""
        self.prompt_manager = prompt_manager
        self._active_workflows: Dict[str, WorkflowExecutionContext] = {}
        self._execution_metrics = {
            'total_workflows': 0,
            'successful_workflows': 0,
            'failed_workflows': 0,
            'avg_execution_time': 0.0,
            'step_success_rate': 0.0
        }
        
        logger.info("WorkflowExecutionEngine initialized")
    
    async def execute_workflow(
        self,
        workflow_config: WorkflowConfiguration,
        context: PromptContext,
        variables: Dict[str, Any] = None,
        workflow_id: str = None
    ) -> Dict[str, Any]:
        """Execute a complete workflow
        
        Args:
            workflow_config: Workflow configuration
            context: Base context for all steps
            variables: Additional variables
            workflow_id: Optional workflow ID for tracking
            
        Returns:
            Workflow execution results
            
        Raises:
            PromptCompositionError: If workflow execution fails
        """
        workflow_id = workflow_id or f"{workflow_config.name}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        
        execution_context = WorkflowExecutionContext(
            workflow_id=workflow_id,
            configuration=workflow_config,
            base_context=context,
            variables=variables or {},
            start_time=datetime.now(UTC)
        )
        
        self._active_workflows[workflow_id] = execution_context
        
        try:
            logger.info(f"Starting workflow execution: {workflow_id}")
            execution_context.status = "running"
            
            # Validate workflow configuration
            await self._validate_workflow(workflow_config)
            
            # Build execution plan
            execution_plan = self._build_execution_plan(workflow_config.steps)
            
            # Execute workflow steps
            await self._execute_workflow_steps(execution_context, execution_plan)
            
            # Generate final output if template specified
            final_result = await self._generate_final_output(execution_context)
            
            # Update metrics and finalize
            execution_context.end_time = datetime.now(UTC)
            execution_context.status = "completed"
            
            self._update_execution_metrics(execution_context, success=True)
            
            logger.info(f"Workflow completed successfully: {workflow_id}")
            
            return {
                'workflow_id': workflow_id,
                'status': 'success',
                'results': execution_context.step_results,
                'final_output': final_result,
                'execution_time_seconds': (
                    execution_context.end_time - execution_context.start_time
                ).total_seconds(),
                'completed_steps': list(execution_context.completed_steps),
                'performance_metrics': execution_context.performance_metrics
            }
            
        except Exception as e:
            execution_context.status = "failed"
            execution_context.error = str(e)
            execution_context.end_time = datetime.now(UTC)
            
            self._update_execution_metrics(execution_context, success=False)
            
            logger.error(f"Workflow execution failed: {workflow_id} - {e}")
            
            if workflow_config.save_partial_results and execution_context.step_results:
                return {
                    'workflow_id': workflow_id,
                    'status': 'partial_failure',
                    'error': str(e),
                    'partial_results': execution_context.step_results,
                    'completed_steps': list(execution_context.completed_steps),
                    'failed_steps': list(execution_context.failed_steps)
                }
            
            raise PromptCompositionError(
                f"Workflow execution failed: {str(e)}",
                composition_name=workflow_config.name,
                failed_templates=[step.template for step in workflow_config.steps 
                                if step.name in execution_context.failed_steps],
                details={
                    'workflow_id': workflow_id,
                    'completed_steps': list(execution_context.completed_steps),
                    'failed_steps': list(execution_context.failed_steps)
                }
            )
        
        finally:
            # Cleanup active workflow tracking
            if workflow_id in self._active_workflows:
                del self._active_workflows[workflow_id]
    
    async def _validate_workflow(self, config: WorkflowConfiguration):
        """Validate workflow configuration"""
        step_names = {step.name for step in config.steps}
        
        # Check for duplicate step names
        if len(step_names) != len(config.steps):
            raise PromptCompositionError(
                f"Duplicate step names in workflow: {config.name}",
                composition_name=config.name
            )
        
        # Validate dependencies
        for step in config.steps:
            for dep in step.dependencies:
                if dep not in step_names:
                    raise PromptCompositionError(
                        f"Step '{step.name}' has unknown dependency: {dep}",
                        composition_name=config.name
                    )
            
            # Validate parallel execution constraints
            for parallel_step in step.parallel_with:
                if parallel_step not in step_names:
                    raise PromptCompositionError(
                        f"Step '{step.name}' has unknown parallel constraint: {parallel_step}",
                        composition_name=config.name
                    )
        
        # Check for circular dependencies
        if self._has_circular_dependencies(config.steps):
            raise PromptCompositionError(
                f"Circular dependencies detected in workflow: {config.name}",
                composition_name=config.name
            )
    
    def _has_circular_dependencies(self, steps: List[WorkflowStep]) -> bool:
        """Check for circular dependencies using DFS"""
        step_map = {step.name: step for step in steps}
        visited = set()
        rec_stack = set()
        
        def dfs(step_name: str) -> bool:
            if step_name in rec_stack:
                return True  # Circular dependency found
            if step_name in visited:
                return False
            
            visited.add(step_name)
            rec_stack.add(step_name)
            
            step = step_map.get(step_name)
            if step:
                for dep in step.dependencies:
                    if dfs(dep):
                        return True
            
            rec_stack.remove(step_name)
            return False
        
        for step in steps:
            if step.name not in visited:
                if dfs(step.name):
                    return True
        
        return False
    
    def _build_execution_plan(self, steps: List[WorkflowStep]) -> List[List[str]]:
        """Build execution plan with parallel execution groups"""
        step_map = {step.name: step for step in steps}
        remaining_steps = set(step.name for step in steps)
        execution_plan = []
        
        while remaining_steps:
            # Find steps with satisfied dependencies
            ready_steps = []
            for step_name in remaining_steps:
                step = step_map[step_name]
                if all(dep not in remaining_steps for dep in step.dependencies):
                    ready_steps.append(step_name)
            
            if not ready_steps:
                raise PromptCompositionError(
                    "Unable to resolve step dependencies - possible circular dependency"
                )
            
            # Group steps that can run in parallel
            parallel_groups = self._group_parallel_steps(ready_steps, step_map)
            
            for group in parallel_groups:
                execution_plan.append(group)
                for step_name in group:
                    remaining_steps.remove(step_name)
        
        return execution_plan
    
    def _group_parallel_steps(
        self, 
        ready_steps: List[str], 
        step_map: Dict[str, WorkflowStep]
    ) -> List[List[str]]:
        """Group steps that can execute in parallel"""
        groups = []
        remaining = set(ready_steps)
        
        while remaining:
            current_group = []
            for step_name in list(remaining):
                step = step_map[step_name]
                
                # Check if this step can run in parallel with current group
                can_parallel = True
                for group_step in current_group:
                    group_step_obj = step_map[group_step]
                    if (step_name in group_step_obj.parallel_with or 
                        group_step in step.parallel_with):
                        continue
                    else:
                        can_parallel = False
                        break
                
                if can_parallel and len(current_group) < 3:  # Max parallel limit
                    current_group.append(step_name)
                    remaining.remove(step_name)
            
            if current_group:
                groups.append(current_group)
            else:
                # Fallback: take first remaining step
                step_name = remaining.pop()
                groups.append([step_name])
        
        return groups
    
    async def _execute_workflow_steps(
        self, 
        context: WorkflowExecutionContext, 
        execution_plan: List[List[str]]
    ):
        """Execute workflow steps according to execution plan"""
        step_map = {step.name: step for step in context.configuration.steps}
        
        for step_group in execution_plan:
            # Execute steps in parallel within each group
            tasks = []
            for step_name in step_group:
                step = step_map[step_name]
                task = self._execute_single_step(context, step)
                tasks.append(task)
            
            # Wait for all steps in group to complete
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.error(f"Error executing step group {step_group}: {e}")
                # Individual step errors are handled in _execute_single_step
                continue
    
    async def _execute_single_step(
        self, 
        context: WorkflowExecutionContext, 
        step: WorkflowStep
    ):
        """Execute a single workflow step"""
        step.status = WorkflowStepStatus.RUNNING
        step.start_time = datetime.now(UTC)
        
        try:
            logger.debug(f"Executing step: {step.name}")
            
            # Prepare step context
            step_context = await self._prepare_step_context(context, step)
            
            # Execute step with timeout
            async with asyncio.timeout(step.timeout_seconds):
                result = await self.prompt_manager.render(
                    template_name=step.template,
                    context=step_context,
                    cache_key=f"{context.workflow_id}_{step.name}" if context.configuration.enable_step_caching else None
                )
            
            # Store result
            if step.output_variable:
                context.step_results[step.output_variable] = result
                context.variables[step.output_variable] = result
            
            step.result = result
            step.status = WorkflowStepStatus.COMPLETED
            context.completed_steps.add(step.name)
            
            logger.debug(f"Step completed successfully: {step.name}")
            
        except asyncio.TimeoutError:
            error_msg = f"Step '{step.name}' timed out after {step.timeout_seconds} seconds"
            await self._handle_step_error(context, step, error_msg)
            
        except Exception as e:
            error_msg = f"Step '{step.name}' failed: {str(e)}"
            await self._handle_step_error(context, step, error_msg)
        
        finally:
            step.end_time = datetime.now(UTC)
            if step.start_time:
                step.execution_time_ms = (
                    step.end_time - step.start_time
                ).total_seconds() * 1000
    
    async def _prepare_step_context(
        self, 
        context: WorkflowExecutionContext, 
        step: WorkflowStep
    ) -> PromptContext:
        """Prepare context for step execution"""
        # Start with base context variables
        step_variables = dict(context.base_context.variables)
        
        # Add workflow variables
        step_variables.update(context.variables)
        
        # Add step-specific input variables
        for var_name in step.input_variables:
            if var_name in context.step_results:
                step_variables[var_name] = context.step_results[var_name]
            elif var_name not in step_variables:
                logger.warning(f"Step '{step.name}' missing input variable: {var_name}")
        
        # Validate required context
        missing_context = []
        for required_var in step.required_context:
            if required_var not in step_variables:
                missing_context.append(required_var)
        
        if missing_context:
            raise PromptCompositionError(
                f"Step '{step.name}' missing required context: {', '.join(missing_context)}",
                composition_name=context.configuration.name
            )
        
        return PromptContext(
            context_type=context.base_context.context_type,
            variables=step_variables
        )
    
    async def _handle_step_error(
        self, 
        context: WorkflowExecutionContext, 
        step: WorkflowStep, 
        error_msg: str
    ):
        """Handle step execution error"""
        step.error = error_msg
        step.retry_count += 1
        
        # Try retry if within limits
        if step.retry_count <= step.max_retries:
            logger.warning(f"Retrying step '{step.name}' (attempt {step.retry_count}/{step.max_retries})")
            await asyncio.sleep(2 ** step.retry_count)  # Exponential backoff
            await self._execute_single_step(context, step)
            return
        
        # Handle failure
        if step.critical:
            step.status = WorkflowStepStatus.FAILED
            context.failed_steps.add(step.name)
            
            if not context.configuration.continue_on_non_critical_failure:
                raise PromptCompositionError(
                    f"Critical step '{step.name}' failed: {error_msg}",
                    composition_name=context.configuration.name
                )
        else:
            step.status = WorkflowStepStatus.SKIPPED
            context.skipped_steps.add(step.name)
            logger.warning(f"Non-critical step '{step.name}' failed, continuing: {error_msg}")
    
    async def _generate_final_output(
        self, 
        context: WorkflowExecutionContext
    ) -> Optional[str]:
        """Generate final workflow output"""
        if not context.configuration.output_template:
            return None
        
        try:
            output_context = PromptContext(
                context_type=context.base_context.context_type,
                variables={
                    **context.base_context.variables,
                    **context.variables,
                    **context.step_results,
                    'workflow_metadata': {
                        'workflow_id': context.workflow_id,
                        'completed_steps': list(context.completed_steps),
                        'execution_time': (
                            context.end_time - context.start_time
                        ).total_seconds() if context.end_time else None
                    }
                }
            )
            
            final_output = await self.prompt_manager.render(
                template_name=context.configuration.output_template,
                context=output_context
            )
            
            return final_output
            
        except Exception as e:
            logger.error(f"Failed to generate final output for workflow {context.workflow_id}: {e}")
            return None
    
    def _update_execution_metrics(
        self, 
        context: WorkflowExecutionContext, 
        success: bool
    ):
        """Update workflow execution metrics"""
        self._execution_metrics['total_workflows'] += 1
        
        if success:
            self._execution_metrics['successful_workflows'] += 1
        else:
            self._execution_metrics['failed_workflows'] += 1
        
        # Update average execution time
        if context.start_time and context.end_time:
            execution_time = (context.end_time - context.start_time).total_seconds()
            total_workflows = self._execution_metrics['total_workflows']
            current_avg = self._execution_metrics['avg_execution_time']
            
            self._execution_metrics['avg_execution_time'] = (
                (current_avg * (total_workflows - 1) + execution_time) / total_workflows
            )
        
        # Update step success rate
        total_steps = len(context.completed_steps) + len(context.failed_steps)
        if total_steps > 0:
            step_success_rate = len(context.completed_steps) / total_steps
            self._execution_metrics['step_success_rate'] = step_success_rate
        
        # Store performance metrics in context
        context.performance_metrics = {
            'total_steps': len(context.configuration.steps),
            'completed_steps': len(context.completed_steps),
            'failed_steps': len(context.failed_steps),
            'skipped_steps': len(context.skipped_steps),
            'success_rate': len(context.completed_steps) / len(context.configuration.steps),
            'execution_time_seconds': (
                context.end_time - context.start_time
            ).total_seconds() if context.end_time and context.start_time else 0
        }
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of active workflow"""
        context = self._active_workflows.get(workflow_id)
        if not context:
            return None
        
        return {
            'workflow_id': workflow_id,
            'name': context.configuration.name,
            'status': context.status,
            'completed_steps': list(context.completed_steps),
            'failed_steps': list(context.failed_steps),
            'progress': len(context.completed_steps) / len(context.configuration.steps),
            'start_time': context.start_time.isoformat() if context.start_time else None,
            'error': context.error
        }
    
    def get_execution_metrics(self) -> Dict[str, Any]:
        """Get workflow execution metrics"""
        return dict(self._execution_metrics)
    
    def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows"""
        return [
            self.get_workflow_status(workflow_id) 
            for workflow_id in self._active_workflows.keys()
        ]
    
    @asynccontextmanager
    async def workflow_execution_context(self, workflow_id: str):
        """Context manager for workflow execution"""
        start_time = datetime.now(UTC)
        
        try:
            logger.debug(f"Starting workflow execution context: {workflow_id}")
            yield self
            
        except Exception as e:
            logger.error(f"Error in workflow execution context {workflow_id}: {e}")
            raise
        
        finally:
            execution_time = (datetime.now(UTC) - start_time).total_seconds()
            logger.debug(f"Workflow execution context {workflow_id} completed in {execution_time:.3f}s")