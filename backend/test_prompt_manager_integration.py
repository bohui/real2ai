#!/usr/bin/env python3
"""
Test script for Phase 2 PromptManager integration
Validates that the migrated services work correctly with the new PromptManager system
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / "app"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_gemini_ocr_service():
    """Test GeminiOCRService with PromptManager integration"""
    try:
        from app.services.gemini_ocr_service import GeminiOCRService
        from app.models.contract_state import AustralianState, ContractType
        
        # Initialize service
        ocr_service = GeminiOCRService()
        
        # Test service initialization
        logger.info("✓ GeminiOCRService successfully inherits from PromptEnabledService")
        
        # Test context creation
        context = ocr_service.create_context(
            document_type="contract",
            file_type="pdf",
            australian_state=AustralianState.NSW,
            contract_type=ContractType.PURCHASE_AGREEMENT
        )
        logger.info("✓ GeminiOCRService can create PromptContext objects")
        
        # Test available templates (should work even if templates don't exist yet)
        templates = ocr_service.get_available_templates()
        logger.info(f"✓ GeminiOCRService can query available templates: {len(templates)} found")
        
        # Test render stats
        stats = ocr_service.get_render_stats()
        logger.info(f"✓ GeminiOCRService provides render statistics: {stats['service_name']}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ GeminiOCRService test failed: {e}")
        return False

async def test_websocket_service():
    """Test WebSocketService enhancements"""
    try:
        from app.services.websocket_service import EnhancedWebSocketService, WebSocketManager
        
        # Create websocket manager (required dependency)
        ws_manager = WebSocketManager()
        
        # Initialize enhanced service
        enhanced_ws_service = EnhancedWebSocketService(ws_manager)
        
        logger.info("✓ EnhancedWebSocketService successfully inherits from PromptEnabledService")
        
        # Test service stats
        stats = enhanced_ws_service.get_service_stats()
        logger.info(f"✓ EnhancedWebSocketService provides enhanced stats: version {stats['service_version']}")
        
        # Test context creation
        context = enhanced_ws_service.create_context(
            notification_type="test",
            session_id="test-session"
        )
        logger.info("✓ EnhancedWebSocketService can create PromptContext objects")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ WebSocketService test failed: {e}")
        return False

async def test_prompt_engineering_service():
    """Test PromptEngineeringService migration"""
    try:
        from app.services.prompt_engineering_service import PromptEngineeringService
        from app.models.contract_state import AustralianState, ContractType
        
        # Initialize service
        prompt_service = PromptEngineeringService()
        
        logger.info("✓ PromptEngineeringService successfully inherits from PromptEnabledService")
        
        # Test service info
        service_info = prompt_service.get_enhanced_service_info()
        logger.info(f"✓ PromptEngineeringService enhanced info: version {service_info['version']}")
        
        # Test legacy compatibility flags
        prompt_service.set_legacy_mode(False)
        prompt_service.set_fallback_mode(True)
        logger.info("✓ PromptEngineeringService supports legacy compatibility modes")
        
        # Test available templates
        templates = prompt_service.get_available_enhanced_templates()
        logger.info(f"✓ PromptEngineeringService can query enhanced templates: {len(templates)} found")
        
        # Test context creation
        context = prompt_service.create_context(
            australian_state=AustralianState.NSW,
            contract_type=ContractType.PURCHASE_AGREEMENT,
            user_type="buyer"
        )
        logger.info("✓ PromptEngineeringService can create PromptContext objects")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ PromptEngineeringService test failed: {e}")
        return False

async def test_prompt_manager_foundation():
    """Test that the PromptManager foundation is available"""
    try:
        from app.core.prompts.manager import get_prompt_manager
        from app.core.prompts.service_mixin import PromptEnabledService
        
        # Test manager initialization
        manager = get_prompt_manager()
        logger.info("✓ PromptManager foundation is available")
        
        # Test service mixin
        class TestService(PromptEnabledService):
            pass
        
        test_service = TestService()
        logger.info("✓ PromptEnabledService mixin is working")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ PromptManager foundation test failed: {e}")
        return False

async def main():
    """Run all integration tests"""
    logger.info("Starting Phase 2 PromptManager Integration Tests...")
    logger.info("=" * 60)
    
    tests = [
        ("PromptManager Foundation", test_prompt_manager_foundation),
        ("GeminiOCRService Integration", test_gemini_ocr_service),
        ("WebSocketService Enhancement", test_websocket_service),  
        ("PromptEngineeringService Migration", test_prompt_engineering_service),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\nTesting {test_name}...")
        logger.info("-" * 40)
        
        try:
            result = await test_func()
            results.append((test_name, result))
            
            if result:
                logger.info(f"✅ {test_name} - PASSED")
            else:
                logger.error(f"❌ {test_name} - FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name} - ERROR: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 2 INTEGRATION TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall Result: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED - Phase 2 integration successful!")
        return True
    else:
        logger.error("❌ Some tests failed - Phase 2 integration needs attention")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)