"""
Phase 1 PromptManager System Examples
Demonstrates usage of the enhanced PromptManager with service integration and workflows
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any

from .factory import PromptManagerFactory, create_prompt_manager_for_app
from .service_mixin import PromptEnabledService
from .context import PromptContext, ContextType
from .exceptions import PromptServiceError, PromptCompositionError

logger = logging.getLogger(__name__)


# Example Service Implementation
class ContractAnalysisService(PromptEnabledService):
    """Example service using the enhanced PromptManager"""
    
    def __init__(self):
        super().__init__()
        self.analysis_cache = {}
    
    async def analyze_contract(
        self,
        extracted_text: str,
        australian_state: str = "NSW",
        contract_type: str = "purchase_agreement",
        user_type: str = "buyer",
        user_experience_level: str = "novice"
    ) -> Dict[str, Any]:
        """Perform complete contract analysis using workflow execution"""
        
        # Create context for analysis
        context = self.create_context(
            context_type=ContextType.USER,
            extracted_text=extracted_text,
            australian_state=australian_state,
            contract_type=contract_type,
            user_type=user_type,
            user_experience_level=user_experience_level,
            document_type="contract"
        )
        
        try:
            # Execute complete contract analysis workflow
            workflow_result = await self.execute_workflow(
                composition_name="complete_contract_analysis",
                context=context,
                workflow_id=f"contract_analysis_{hash(extracted_text[:100])}"
            )
            
            # Cache the result
            cache_key = self._generate_cache_key("contract_analysis", context)
            self.analysis_cache[cache_key] = workflow_result
            
            return {
                "analysis": workflow_result,
                "service_stats": self.get_render_stats(),
                "workflow_id": workflow_result.get("workflow_id")
            }
            
        except Exception as e:
            logger.error(f"Contract analysis failed: {e}")
            raise PromptServiceError(
                f"Contract analysis failed: {str(e)}",
                service_name=self._service_name,
                details={"extracted_text_length": len(extracted_text)}
            )
    
    async def quick_risk_assessment(
        self,
        extracted_text: str,
        australian_state: str = "NSW",
        contract_type: str = "purchase_agreement"
    ) -> Dict[str, Any]:
        """Perform quick risk assessment using simplified workflow"""
        
        context = self.create_context(
            context_type=ContextType.USER,
            extracted_text=extracted_text,
            australian_state=australian_state,
            contract_type=contract_type,
            analysis_priority="high_risk_only"
        )
        
        try:
            # Execute quick review workflow
            workflow_result = await self.execute_workflow(
                composition_name="quick_contract_review",
                context=context
            )
            
            return {
                "risk_assessment": workflow_result,
                "execution_time": workflow_result.get("execution_time_seconds", 0),
                "critical_risks": workflow_result.get("results", {}).get("critical_risks", [])
            }
            
        except Exception as e:
            logger.error(f"Quick risk assessment failed: {e}")
            raise
    
    async def get_analysis_templates(self) -> Dict[str, Any]:
        """Get available templates and workflows for contract analysis"""
        
        return {
            "templates": self.get_available_templates(category="analysis"),
            "compositions": self.get_available_compositions(),
            "workflows": self.get_available_workflows(),
            "performance_targets": self.get_service_performance_targets()
        }


# Example OCR Service Implementation
class OCRService(PromptEnabledService):
    """Example OCR service using enhanced PromptManager"""
    
    async def extract_and_structure(
        self,
        image_data: bytes,
        document_type: str = "contract",
        australian_state: str = "NSW"
    ) -> Dict[str, Any]:
        """Extract text from image and structure it"""
        
        # Simulate OCR extraction (in real implementation, this would use actual OCR)
        raw_text = "Simulated OCR extraction result..."
        
        context = self.create_context(
            context_type=ContextType.USER,
            raw_text=raw_text,
            document_type=document_type,
            australian_state=australian_state,
            quality_requirements="high"
        )
        
        try:
            # Execute OCR to structured data workflow
            workflow_result = await self.execute_workflow(
                composition_name="ocr_to_structured_data",
                context=context
            )
            
            return {
                "extracted_text": raw_text,
                "structured_data": workflow_result.get("results", {}),
                "quality_metrics": {
                    "confidence": 0.95,
                    "processing_time": workflow_result.get("execution_time_seconds", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"OCR extraction and structuring failed: {e}")
            raise


# Example WebSocket Service Implementation  
class WebSocketService(PromptEnabledService):
    """Example WebSocket service for progress updates"""
    
    async def send_progress_update(
        self,
        workflow_id: str,
        progress: float,
        current_step: str,
        message: str = None
    ) -> str:
        """Send progress update message"""
        
        context = self.create_context(
            context_type=ContextType.SYSTEM,
            workflow_id=workflow_id,
            progress=progress,
            current_step=current_step,
            message=message or f"Processing step: {current_step}",
            message_type="progress_update"
        )
        
        # Render progress update template
        progress_message = await self.render_prompt(
            template_name="progress_update",
            context=context,
            use_cache=True
        )
        
        # In real implementation, this would send via WebSocket
        logger.info(f"Progress update: {progress_message}")
        
        return progress_message
    
    async def send_completion_summary(
        self,
        workflow_id: str,
        results: Dict[str, Any],
        execution_time: float
    ) -> str:
        """Send workflow completion summary"""
        
        context = self.create_context(
            context_type=ContextType.SYSTEM,
            workflow_id=workflow_id,
            results=results,
            execution_time=execution_time,
            completed_steps=results.get("completed_steps", []),
            message_type="completion_summary"
        )
        
        # Render completion summary template
        summary_message = await self.render_prompt(
            template_name="completion_summary",
            context=context
        )
        
        logger.info(f"Completion summary: {summary_message}")
        
        return summary_message


# Example Usage Functions

async def example_basic_usage():
    """Example of basic PromptManager usage"""
    
    # Create PromptManager for development
    app_root = Path(__file__).parent.parent.parent.parent
    templates_dir = app_root / "prompts"
    config_dir = templates_dir / "config"
    
    manager = PromptManagerFactory.create_development(
        templates_dir=templates_dir,
        config_dir=config_dir
    )
    
    # Initialize async components
    await manager.initialize()
    
    # Basic template rendering
    context = PromptContext(
        context_type=ContextType.USER,
        variables={
            "extracted_text": "Sample contract text...",
            "australian_state": "NSW",
            "contract_type": "purchase_agreement"
        }
    )
    
    try:
        # Render a single template
        result = await manager.render(
            template_name="contract_structure_analysis",
            context=context,
            service_name="contract_analysis"
        )
        
        print(f"Rendered template result: {result[:100]}...")
        
        # Get manager metrics
        metrics = manager.get_metrics()
        print(f"Manager metrics: {metrics}")
        
    except Exception as e:
        print(f"Error in basic usage: {e}")


async def example_service_integration():
    """Example of service integration with PromptManager"""
    
    # Create services
    contract_service = ContractAnalysisService()
    ocr_service = OCRService()
    websocket_service = WebSocketService()
    
    # Simulate document processing workflow
    try:
        # Step 1: OCR extraction
        ocr_result = await ocr_service.extract_and_structure(
            image_data=b"fake_image_data",
            document_type="contract",
            australian_state="VIC"
        )
        
        print(f"OCR completed: {ocr_result['quality_metrics']}")
        
        # Step 2: Contract analysis
        analysis_result = await contract_service.analyze_contract(
            extracted_text=ocr_result["extracted_text"],
            australian_state="VIC",
            contract_type="purchase_agreement",
            user_type="buyer",
            user_experience_level="intermediate"
        )
        
        print(f"Analysis completed: {analysis_result['workflow_id']}")
        
        # Step 3: Send completion notification
        completion_message = await websocket_service.send_completion_summary(
            workflow_id=analysis_result["workflow_id"],
            results=analysis_result["analysis"],
            execution_time=analysis_result["analysis"].get("execution_time_seconds", 0)
        )
        
        print(f"Notification sent: {completion_message[:100]}...")
        
        # Get service statistics
        print(f"Contract Service Stats: {contract_service.get_render_stats()}")
        print(f"OCR Service Stats: {ocr_service.get_render_stats()}")
        print(f"WebSocket Service Stats: {websocket_service.get_render_stats()}")
        
    except Exception as e:
        print(f"Error in service integration: {e}")


async def example_workflow_execution():
    """Example of direct workflow execution"""
    
    app_root = Path(__file__).parent.parent.parent.parent
    manager = await create_prompt_manager_for_app(
        app_root=app_root,
        environment="development"
    )
    
    # Create workflow context
    context = PromptContext(
        context_type=ContextType.USER,
        variables={
            "extracted_text": "This is a sample contract for property purchase...",
            "australian_state": "QLD",
            "contract_type": "purchase_agreement",
            "user_type": "buyer",
            "user_experience_level": "expert",
            "document_type": "contract"
        }
    )
    
    try:
        # Execute complete contract analysis workflow
        workflow_result = await manager.execute_workflow(
            composition_name="complete_contract_analysis",
            context=context,
            variables={"priority": "high"},
            workflow_id="example_workflow_001"
        )
        
        print(f"Workflow Status: {workflow_result['status']}")
        print(f"Execution Time: {workflow_result['execution_time_seconds']:.2f}s")
        print(f"Completed Steps: {workflow_result['completed_steps']}")
        
        # Monitor workflow progress (if still running)
        workflow_status = manager.get_workflow_status("example_workflow_001")
        if workflow_status:
            print(f"Workflow Progress: {workflow_status['progress']:.2%}")
        
        # List all active workflows
        active_workflows = manager.list_active_workflows()
        print(f"Active Workflows: {len(active_workflows)}")
        
    except Exception as e:
        print(f"Error in workflow execution: {e}")


async def example_configuration_management():
    """Example of configuration management features"""
    
    app_root = Path(__file__).parent.parent.parent.parent
    manager = await create_prompt_manager_for_app(
        app_root=app_root,
        environment="development"
    )
    
    try:
        # Get service-specific information
        service_templates = manager.get_service_templates(
            service_name="contract_analysis",
            include_fallbacks=True
        )
        print(f"Contract Analysis Templates: {len(service_templates)}")
        
        service_compositions = manager.get_service_compositions("contract_analysis")
        print(f"Contract Analysis Compositions: {len(service_compositions)}")
        
        performance_targets = manager.get_service_performance_targets("contract_analysis")
        print(f"Performance Targets: {performance_targets}")
        
        # Get available workflows
        available_workflows = manager.get_available_workflows("contract_analysis")
        print(f"Available Workflows: {len(available_workflows)}")
        
        # Validate service context
        context_validation = await manager.validate_service_context(
            service_name="contract_analysis",
            context={
                "extracted_text": "Sample text",
                "australian_state": "NSW",
                "contract_type": "purchase_agreement",
                "user_type": "buyer"
            }
        )
        print(f"Context Validation: {context_validation}")
        
        # Get comprehensive metrics
        metrics = manager.get_metrics()
        print(f"System Metrics: {metrics}")
        
    except Exception as e:
        print(f"Error in configuration management: {e}")


async def example_health_check():
    """Example of system health monitoring"""
    
    app_root = Path(__file__).parent.parent.parent.parent
    manager = await create_prompt_manager_for_app(
        app_root=app_root,
        environment="production"
    )
    
    try:
        # Perform comprehensive health check
        health_status = await manager.health_check()
        
        print(f"System Status: {health_status['status']}")
        print(f"Timestamp: {health_status['timestamp']}")
        
        for component, status in health_status['components'].items():
            print(f"{component}: {status['status']}")
            if 'error' in status:
                print(f"  Error: {status['error']}")
        
        # Test template rendering if healthy
        if health_status['status'] == 'healthy':
            test_context = PromptContext(
                context_type=ContextType.SYSTEM,
                variables={"test": "health_check"}
            )
            
            # This would fail if no test template exists, but demonstrates the pattern
            print("System is healthy and ready for operation")
        
    except Exception as e:
        print(f"Health check failed: {e}")


# Main example runner
async def run_all_examples():
    """Run all examples"""
    
    examples = [
        ("Basic Usage", example_basic_usage),
        ("Service Integration", example_service_integration),
        ("Workflow Execution", example_workflow_execution),
        ("Configuration Management", example_configuration_management),
        ("Health Check", example_health_check)
    ]
    
    for name, example_func in examples:
        print(f"\n{'='*50}")
        print(f"Running Example: {name}")
        print(f"{'='*50}")
        
        try:
            await example_func()
            print(f"✅ {name} completed successfully")
        except Exception as e:
            print(f"❌ {name} failed: {e}")
        
        print(f"{'='*50}")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run all examples
    asyncio.run(run_all_examples())