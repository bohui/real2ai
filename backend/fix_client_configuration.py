#!/usr/bin/env python3
"""
Fix for client configuration authentication issue.

The root cause is that the system is trying to use OpenRouter with an OpenAI API key.
This script provides several solutions to fix the authentication issue.
"""

import os
import sys

def main():
    print("🔍 Client Configuration Diagnosis")
    print("=" * 50)
    
    # Check current environment
    openai_key = os.getenv('OPENAI_API_KEY', '')
    openrouter_key = os.getenv('OPENROUTER_API_KEY', '')
    
    print(f"OPENAI_API_KEY: {'✅ Set' if openai_key else '❌ Not set'}")
    print(f"OPENROUTER_API_KEY: {'✅ Set' if openrouter_key else '❌ Not set'}")
    
    if openai_key and openai_key.startswith('sk-test-'):
        print("⚠️  OpenAI key appears to be a test key")
    elif openai_key and openai_key.startswith('sk-'):
        print("✅ OpenAI key format looks valid")
    
    print("\n🔧 Solutions")
    print("=" * 50)
    
    if openai_key and not openrouter_key:
        print("SOLUTION 1: Configure OpenAI directly (recommended)")
        print("Add to your .env file:")
        print("OPENAI_API_BASE=https://api.openai.com/v1")
        print("# This will force the client to use OpenAI instead of OpenRouter")
        print()
        
        print("SOLUTION 2: Get an OpenRouter API key")
        print("1. Go to https://openrouter.ai/")
        print("2. Sign up and get an API key")
        print("3. Add to your .env file:")
        print("OPENROUTER_API_KEY=sk-or-v1-your-key-here")
        print()
        
        print("SOLUTION 3: Disable OpenAI client temporarily")
        print("Set in your .env file:")
        print("OPENAI_API_KEY=")
        print("# This will make the system use only Gemini")
        
    elif openrouter_key:
        print("✅ OpenRouter key is configured - should work")
        
    elif not openai_key and not openrouter_key:
        print("❌ No API keys configured")
        print("Please set either OPENAI_API_KEY or OPENROUTER_API_KEY")
    
    print("\n🎯 Quick Fix")
    print("=" * 50)
    print("To fix the immediate issue, run:")
    print("export OPENAI_API_BASE=https://api.openai.com/v1")
    print("# This forces direct OpenAI usage")

if __name__ == '__main__':
    main()