"""
LangChain client implementation for workflow operations.
"""

import logging
from typing import Any, Dict, Optional, List
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from ..base.exceptions import ClientError
from .config import OpenAIClientConfig

logger = logging.getLogger(__name__)


class LangChainClient:
    """LangChain operations client."""
    
    def __init__(self, openai_client: OpenAI, config: OpenAIClientConfig):
        self.openai_client = openai_client
        self.config = config
        self.client_name = "LangChainClient"
        self.logger = logging.getLogger(f"{__name__}.{self.client_name}")
        self._chat_llm: Optional[ChatOpenAI] = None
        self._initialized = False
    
    @property
    def chat_llm(self) -> ChatOpenAI:
        """Get the ChatOpenAI instance."""
        if not self._chat_llm:
            raise ClientError("LangChain ChatOpenAI not initialized", self.client_name)
        return self._chat_llm
    
    async def initialize(self) -> None:
        """Initialize LangChain client."""
        try:
            self.logger.info("Initializing LangChain client...")
            
            # Create ChatOpenAI instance
            chat_kwargs = {
                "openai_api_key": self.config.api_key,
                "model_name": self.config.model_name,
                "temperature": self.config.temperature,
                "request_timeout": self.config.request_timeout,
                "max_retries": self.config.max_retries,
            }
            
            if self.config.api_base:
                chat_kwargs["openai_api_base"] = self.config.api_base
            
            if self.config.organization:
                chat_kwargs["openai_organization"] = self.config.organization
            
            if self.config.max_tokens:
                chat_kwargs["max_tokens"] = self.config.max_tokens
            
            self._chat_llm = ChatOpenAI(**chat_kwargs)
            
            # Test the LangChain integration
            await self._test_langchain_integration()
            
            self._initialized = True
            self.logger.info("LangChain client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize LangChain client: {e}")
            raise ClientError(
                f"Failed to initialize LangChain client: {str(e)}",
                client_name=self.client_name,
                original_error=e
            )
    
    async def _test_langchain_integration(self) -> None:
        """Test LangChain integration."""
        try:
            # Simple test with LangChain
            messages = [HumanMessage(content="Test LangChain integration. Respond with 'OK'.")]
            
            # Execute in thread pool to avoid blocking
            import asyncio
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._chat_llm(messages)
            )
            
            if not response.content:
                raise ClientError("LangChain integration test failed: No response received")
            
            self.logger.debug("LangChain integration test successful")
            
        except Exception as e:
            raise ClientError(
                f"LangChain integration test failed: {str(e)}",
                client_name=self.client_name,
                original_error=e
            )
    
    async def create_workflow(self, workflow_type: str = "contract_analysis", **kwargs) -> Any:
        """Create a workflow instance."""
        try:
            self.logger.debug(f"Creating workflow of type: {workflow_type}")
            
            if workflow_type == "contract_analysis":
                # Import and create contract analysis workflow
                from app.agents.contract_workflow import EnhancedContractAnalysisWorkflow as ContractAnalysisWorkflow
                
                workflow = ContractAnalysisWorkflow(
                    openai_api_key=self.config.api_key,
                    model_name=self.config.model_name,
                    openai_api_base=self.config.api_base
                )
                
                self.logger.debug("Contract analysis workflow created successfully")
                return workflow
            else:
                raise ClientError(
                    f"Unsupported workflow type: {workflow_type}",
                    client_name=self.client_name
                )
                
        except Exception as e:
            self.logger.error(f"Workflow creation failed: {e}")
            raise ClientError(
                f"Workflow creation failed: {str(e)}",
                client_name=self.client_name,
                original_error=e
            )
    
    async def execute_chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Execute a chat completion using LangChain."""
        try:
            self.logger.debug(f"Executing chat completion with {len(messages)} messages")
            
            # Convert dict messages to LangChain message objects
            langchain_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    langchain_messages.append(SystemMessage(content=content))
                else:  # user, assistant, etc.
                    langchain_messages.append(HumanMessage(content=content))
            
            # Execute chat completion
            import asyncio
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.chat_llm(langchain_messages)
            )
            
            if not response.content:
                raise ClientError("Chat completion returned no content")
            
            self.logger.debug(f"Chat completion successful: {len(response.content)} characters")
            return response.content
            
        except Exception as e:
            self.logger.error(f"Chat completion failed: {e}")
            raise ClientError(
                f"Chat completion failed: {str(e)}",
                client_name=self.client_name,
                original_error=e
            )
    
    async def analyze_contract_workflow(self, document_content: str, state_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute contract analysis workflow."""
        try:
            self.logger.debug("Starting contract analysis workflow")
            
            # Create workflow
            workflow = await self.create_workflow("contract_analysis")
            
            # Prepare initial state
            from app.models.contract_state import RealEstateAgentState
            
            initial_state = RealEstateAgentState(
                document_content=document_content,
                current_step="validate_input",
                processing_status="pending",
                **state_config or {}
            )
            
            # Execute workflow
            import asyncio
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: workflow.workflow.invoke(initial_state)
            )
            
            self.logger.debug("Contract analysis workflow completed successfully")
            
            # Convert result to dict for JSON serialization
            if hasattr(result, '__dict__'):
                result_dict = result.__dict__
            else:
                result_dict = dict(result) if isinstance(result, dict) else {"result": str(result)}
            
            return {
                "workflow_result": result_dict,
                "status": "completed",
                "workflow_type": "contract_analysis"
            }
            
        except Exception as e:
            self.logger.error(f"Contract analysis workflow failed: {e}")
            raise ClientError(
                f"Contract analysis workflow failed: {str(e)}",
                client_name=self.client_name,
                original_error=e
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check LangChain client health."""
        try:
            await self._test_langchain_integration()
            return {
                "status": "healthy",
                "client_name": self.client_name,
                "initialized": self._initialized,
                "chat_llm_available": self._chat_llm is not None,
                "model_name": self.config.model_name,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "client_name": self.client_name,
                "error": str(e),
                "initialized": self._initialized,
            }
    
    async def close(self) -> None:
        """Close LangChain client."""
        if self._chat_llm:
            # LangChain ChatOpenAI doesn't require explicit closing
            self._chat_llm = None
        
        self._initialized = False
        self.logger.info("LangChain client closed successfully")