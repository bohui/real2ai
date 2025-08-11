#!/usr/bin/env python3
"""
Integration Example: Phase 2 PromptManager Enhancement
Demonstrates how the migrated services use the new PromptManager system
"""

import asyncio
from typing import Dict, Any
from datetime import datetime

# Example usage of the enhanced services
async def example_gemini_ocr_integration():
    """Example: Enhanced GeminiOCRService with PromptManager"""
    
    # Simulated service initialization
    print("=== GeminiOCRService with PromptManager Integration ===")
    
    # Example context creation (in real usage, this would be a full service)
    example_context = {
        "document_type": "contract",
        "file_type": "pdf",
        "australian_state": "NSW",
        "contract_type": "PURCHASE_AGREEMENT",
        "quality_requirements": "high",
        "processing_profile": "quality"
    }
    
    print("1. Enhanced Context Preparation:")
    print(f"   • Document Type: {example_context['document_type']}")
    print(f"   • Quality Level: {example_context['quality_requirements']}")
    print(f"   • State: {example_context['australian_state']}")
    print(f"   • Template Enhanced: True")
    
    print("\n2. OCR Processing Flow:")
    print("   • Legacy Method: Basic OCR with hardcoded prompts")
    print("   • Enhanced Method: Template-driven OCR with context awareness")
    print("   • Fallback: Automatic fallback to legacy on template failure")
    
    print("\n3. Expected Improvements:")
    print("   • More accurate extraction due to context-aware prompts")
    print("   • State-specific legal term recognition")
    print("   • Consistent output formatting via templates")
    print("   • Better error handling and recovery")

async def example_websocket_integration():
    """Example: Enhanced WebSocket notifications"""
    
    print("\n=== Enhanced WebSocketService with PromptManager ===")
    
    # Example notification scenarios
    notifications = [
        {
            "type": "analysis_progress",
            "data": {
                "contract_id": "CONTRACT_001",
                "step": "ocr_extraction",
                "progress": 25,
                "description": "Extracting text from document pages"
            }
        },
        {
            "type": "analysis_complete",
            "data": {
                "contract_id": "CONTRACT_001",
                "status": "completed",
                "summary": {
                    "risk_level": "medium",
                    "key_findings": ["Cooling-off period: 5 days", "Settlement: 42 days"]
                }
            }
        }
    ]
    
    for i, notification in enumerate(notifications, 1):
        print(f"\n{i}. {notification['type'].title()} Notification:")
        print("   Legacy: Basic JSON message with static template")
        print("   Enhanced: Dynamic message generation using PromptManager")
        print(f"   Context: {notification['data']}")
        print("   • Template-driven content generation")
        print("   • Personalized messaging based on user context")
        print("   • Rich error recovery suggestions")

async def example_prompt_engineering_integration():
    """Example: Migrated PromptEngineeringService"""
    
    print("\n=== PromptEngineeringService Migration ===")
    
    # Example workflow
    workflow_steps = [
        "OCR Extraction",
        "Structure Analysis", 
        "Risk Assessment",
        "Compliance Check",
        "Financial Analysis",
        "Recommendations"
    ]
    
    print("1. Legacy vs Enhanced Comparison:")
    print("   Legacy Mode:")
    print("   • Hardcoded prompt strings")
    print("   • Static templates with limited context")
    print("   • Manual prompt optimization")
    
    print("\n   Enhanced Mode:")
    print("   • Dynamic template-driven prompts")
    print("   • Rich context awareness (state, contract type, user level)")
    print("   • Automatic prompt optimization for target models")
    print("   • Workflow orchestration via PromptManager")
    
    print(f"\n2. Workflow Processing ({len(workflow_steps)} steps):")
    for i, step in enumerate(workflow_steps, 1):
        print(f"   Step {i}: {step}")
        print(f"   • Template: {step.lower().replace(' ', '_')}_base")
        print(f"   • Enhanced: Context-aware prompt generation")
        print(f"   • Fallback: Legacy prompt if template fails")
    
    print("\n3. Backward Compatibility:")
    print("   • All existing methods preserved")
    print("   • set_legacy_mode(True) forces old behavior")
    print("   • set_fallback_mode(True) enables automatic fallbacks")
    print("   • Zero changes required for existing code")

async def example_integration_benefits():
    """Example: Overall integration benefits"""
    
    print("\n=== Integration Benefits Summary ===")
    
    benefits = {
        "Performance": [
            "Template caching reduces rendering time",
            "Batch processing for multiple prompts",
            "Smart context reuse across requests"
        ],
        "Quality": [
            "Consistent prompt formatting via templates",
            "Context-aware content generation", 
            "Validation and error checking built-in"
        ],
        "Maintainability": [
            "Centralized prompt management",
            "Template versioning and rollback",
            "Unified API across all services"
        ],
        "Reliability": [
            "Multiple fallback layers",
            "Graceful degradation on failures",
            "Comprehensive error handling"
        ]
    }
    
    for category, items in benefits.items():
        print(f"\n{category} Improvements:")
        for item in items:
            print(f"   ✓ {item}")

async def main():
    """Run all integration examples"""
    print("Phase 2 PromptManager Integration Examples")
    print("=" * 50)
    
    await example_gemini_ocr_integration()
    await example_websocket_integration()
    await example_prompt_engineering_integration()
    await example_integration_benefits()
    
    print("\n" + "=" * 50)
    print("🎉 Phase 2 Integration Complete!")
    print("\nNext Steps:")
    print("• Develop comprehensive template library")
    print("• Define complex workflow compositions")
    print("• Implement performance monitoring")
    print("• Create advanced template features")

if __name__ == "__main__":
    asyncio.run(main())