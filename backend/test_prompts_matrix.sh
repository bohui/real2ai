#!/bin/bash

# Prompt Testing Matrix Script
# This script allows you to test individual prompts with different models
# using test_files/contract.pdf and test_files/contract.txt as input

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_FILES_DIR="$SCRIPT_DIR/../test_files"
OUTPUT_DIR="$SCRIPT_DIR/test_results"
LOG_FILE="$OUTPUT_DIR/prompt_testing.log"

# Load environment variables from .env.local if it exists
load_environment() {
    local env_file="$SCRIPT_DIR/.env.local"
    if [[ -f "$env_file" ]]; then
        echo -e "${BLUE}Loading environment variables from .env.local${NC}"
        # Export variables, excluding comments and empty lines
        export $(cat "$env_file" | grep -v '^#' | grep -v '^$' | xargs)
        echo -e "${GREEN}✓ Environment variables loaded${NC}"
        
        # Verify key variables are loaded (show first few characters for security)
        if [[ -n "$OPENAI_API_KEY" ]]; then
            echo "  OpenAI API Key: ${OPENAI_API_KEY:0:10}..."
        else
            echo -e "${YELLOW}⚠  OpenAI API Key not found${NC}"
        fi
        
        if [[ -n "$GEMINI_API_KEY" ]]; then
            echo "  Gemini API Key: ${GEMINI_API_KEY:0:10}..."
        else
            echo -e "${YELLOW}⚠  Gemini API Key not found${NC}"
        fi
        
        if [[ -n "$SUPABASE_URL" ]]; then
            echo "  Supabase URL: ${SUPABASE_URL:0:20}..."
        else
            echo -e "${YELLOW}⚠  Supabase URL not found${NC}"
        fi
        
        echo ""
    else
        echo -e "${YELLOW}⚠  .env.local file not found at $env_file${NC}"
        echo -e "${YELLOW}  Make sure to set required environment variables manually${NC}"
        echo ""
    fi
}

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Test files
PDF_FILE="$TEST_FILES_DIR/contract.pdf"
TXT_FILE="$TEST_FILES_DIR/contract.txt"

# Available models
declare -a OPENAI_MODELS=(
    "deepseek/deepseek-chat-v3-0324:free"
    "deepseek/deepseek-r1-0528:free"
    "openai/gpt-oss-20b:free"
    "anthropic/claude-3.5-sonnet"
    "meta-llama/llama-3.1-405b-instruct"
    "meta-llama/llama-3.1-8b-instruct"
)

declare -a GEMINI_MODELS=(
    "gemini-2.5-flash"
    "gemini-2.0-flash-exp"
    "gemini-1.5-flash"
    "gemini-1.5-pro"
)

# Available prompts (based on your codebase)
declare -a OCR_PROMPTS=(
    "ocr/whole_document_extraction"
    "ocr/general_document_extraction"
    "ocr/ocr_extraction"
    "ocr/text_diagram_insight"
)

declare -a ANALYSIS_PROMPTS=(
    "analysis/compliance_check"
    "analysis/financial_analysis"
    "analysis/contract_structure"
    "analysis/risk_analysis_structured"
    "analysis/image_semantics"
    "analysis/semantic_risk_consolidation"
    "analysis/semantic_analysis"
)

declare -a COMPOSITIONS=(
    "ocr_whole_document_extraction"
    "image_semantics_only"
    "ocr_text_diagram_insight"
)

# Test contexts for different scenarios
create_test_context() {
    local prompt_type="$1"
    local context_file="$OUTPUT_DIR/test_context_${prompt_type}.json"
    
    case "$prompt_type" in
        "ocr")
            cat > "$context_file" << EOF
{
    "document_type": "contract",
    "australian_state": "NSW",
    "contract_type": "residential",
    "filename": "contract.pdf",
    "file_type": "pdf",
    "is_multi_page": false,
    "use_quick_mode": false
}
EOF
            ;;
        "analysis")
            cat > "$context_file" << EOF
{
    "image_type": "diagram",
    "contract_context": {
        "property_type": "residential",
        "state": "NSW",
        "contract_type": "residential"
    },
    "analysis_focus": "comprehensive",
    "risk_categories": ["boundary", "easement", "infrastructure"],
    "filename": "contract.pdf",
    "file_type": "pdf"
}
EOF
            ;;
        "composition")
            cat > "$context_file" << EOF
{
    "document_type": "contract",
    "australian_state": "NSW",
    "contract_type": "residential",
    "filename": "contract.pdf",
    "file_type": "pdf",
    "analysis_focus": "comprehensive",
    "risk_categories": ["boundary", "easement"]
}
EOF
            ;;
    esac
    
    echo "$context_file"
}

# Test a single prompt with a specific model
test_prompt() {
    local prompt_name="$1"
    local model_name="$2"
    local context_file="$3"
    local test_type="$4"
    
    echo -e "${BLUE}Testing: $prompt_name with $model_name${NC}"
    
    # Create Python test script
    local test_script="$OUTPUT_DIR/test_${prompt_name//\//_}_${model_name//[^a-zA-Z0-9]/_}.py"
    
    cat > "$test_script" << EOF
#!/usr/bin/env python3
"""
Test script for prompt: $prompt_name
Model: $model_name
Test type: $test_type
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.prompts.manager import get_prompt_manager
from app.core.prompts.context import PromptContext, ContextType

async def test_prompt():
    """Test the specific prompt with the given model"""
    try:
        # Initialize prompt manager
        prompt_manager = get_prompt_manager()
        await prompt_manager.initialize()
        
        # Load test context
        with open("$context_file", "r") as f:
            context_data = json.load(f)
        
        # Create context
        context = PromptContext(
            context_type=ContextType.USER,
            variables=context_data
        )
        
        # Test prompt rendering
        if "$test_type" == "composition":
            result = await prompt_manager.render_composed(
                composition_name="$prompt_name",
                context=context
            )
            print(f"✓ Composition rendered successfully")
            print(f"  System prompt length: {len(result.get('system_prompt', ''))}")
            print(f"  User prompt length: {len(result.get('user_prompt', ''))}")
        else:
            rendered = await prompt_manager.render(
                template_name="$prompt_name",
                context=context,
                model="$model_name"
            )
            print(f"✓ Prompt rendered successfully")
            print(f"  Length: {len(rendered)} characters")
            print(f"  Preview: {rendered[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing prompt: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_prompt())
    sys.exit(0 if success else 1)
EOF
    
    # Make executable and run
    chmod +x "$test_script"
    
    # Run the test
    local result_file="$OUTPUT_DIR/result_${prompt_name//\//_}_${model_name//[^a-zA-Z0-9]/_}.txt"
    
    if python3 "$test_script" > "$result_file" 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}"
        echo "  Results saved to: $result_file"
    else
        echo -e "${RED}✗ FAILED${NC}"
        echo "  Check: $result_file"
    fi
    
    echo ""
}

# Test all prompts with all models (matrix testing)
run_matrix_test() {
    echo -e "${YELLOW}Running Matrix Test - All Prompts with All Models${NC}"
    echo "=================================================="
    
    local total_tests=0
    local passed_tests=0
    
    # Test OCR prompts
    for prompt in "${OCR_PROMPTS[@]}"; do
        for model in "${OPENAI_MODELS[@]}" "${GEMINI_MODELS[@]}"; do
            total_tests=$((total_tests + 1))
            context_file=$(create_test_context "ocr")
            if test_prompt "$prompt" "$model" "$context_file" "template"; then
                passed_tests=$((passed_tests + 1))
            fi
        done
    done
    
    # Test analysis prompts
    for prompt in "${ANALYSIS_PROMPTS[@]}"; do
        for model in "${OPENAI_MODELS[@]}" "${GEMINI_MODELS[@]}"; do
            total_tests=$((total_tests + 1))
            context_file=$(create_test_context "analysis")
            if test_prompt "$prompt" "$model" "$context_file" "template"; then
                passed_tests=$((passed_tests + 1))
            fi
        done
    done
    
    # Test compositions
    for composition in "${COMPOSITIONS[@]}"; do
        for model in "${OPENAI_MODELS[@]}" "${GEMINI_MODELS[@]}"; do
            total_tests=$((total_tests + 1))
            context_file=$(create_test_context "composition")
            if test_prompt "$composition" "$model" "$context_file" "composition"; then
                passed_tests=$((passed_tests + 1))
            fi
        done
    done
    
    echo "=================================================="
    echo -e "${GREEN}Matrix Test Complete: $passed_tests/$total_tests tests passed${NC}"
}

# Test specific prompt with specific model
test_specific() {
    local prompt_name="$1"
    local model_name="$2"
    
    echo -e "${YELLOW}Testing Specific: $prompt_name with $model_name${NC}"
    
    # Determine test type
    local test_type="template"
    if [[ " ${COMPOSITIONS[@]} " =~ " ${prompt_name} " ]]; then
        test_type="composition"
    fi
    
    # Determine context type
    local context_type="ocr"
    if [[ " ${ANALYSIS_PROMPTS[@]} " =~ " ${prompt_name} " ]]; then
        context_type="analysis"
    elif [[ " ${COMPOSITIONS[@]} " =~ " ${prompt_name} " ]]; then
        context_type="composition"
    fi
    
    local context_file=$(create_test_context "$context_type")
    test_prompt "$prompt_name" "$model_name" "$context_file" "$test_type"
}

# Test specific prompt with all models
test_prompt_all_models() {
    local prompt_name="$1"
    
    echo -e "${YELLOW}Testing Prompt: $prompt_name with All Models${NC}"
    echo "=================================================="
    
    local total_tests=0
    local passed_tests=0
    
    for model in "${OPENAI_MODELS[@]}" "${GEMINI_MODELS[@]}"; do
        total_tests=$((total_tests + 1))
        if test_specific "$prompt_name" "$model"; then
            passed_tests=$((passed_tests + 1))
        fi
    done
    
    echo "=================================================="
    echo -e "${GREEN}Prompt Test Complete: $passed_tests/$total_tests tests passed${NC}"
}

# Test specific model with all prompts
test_model_all_prompts() {
    local model_name="$1"
    
    echo -e "${YELLOW}Testing Model: $model_name with All Prompts${NC}"
    echo "=================================================="
    
    local total_tests=0
    local passed_tests=0
    
    # Test all prompt types
    for prompt in "${OCR_PROMPTS[@]}" "${ANALYSIS_PROMPTS[@]}" "${COMPOSITIONS[@]}"; do
        total_tests=$((total_tests + 1))
        if test_specific "$prompt" "$model_name"; then
            passed_tests=$((passed_tests + 1))
        fi
    done
    
    echo "=================================================="
    echo -e "${GREEN}Model Test Complete: $passed_tests/$total_tests tests passed${NC}"
}

# Show available options
show_help() {
    echo -e "${BLUE}Prompt Testing Matrix Script${NC}"
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  matrix                    Run all prompts with all models (matrix test)"
    echo "  prompt <prompt_name>      Test specific prompt with all models"
    echo "  model <model_name>        Test specific model with all prompts"
    echo "  specific <prompt> <model> Test specific prompt with specific model"
    echo "  list                      List all available prompts and models"
    echo "  help                      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 matrix                                    # Run full matrix test"
    echo "  $0 prompt \"ocr/whole_document_extraction\"   # Test OCR prompt with all models"
    echo "  $0 model \"gemini-2.5-flash\"                # Test Gemini model with all prompts"
    echo "  $0 specific \"ocr/whole_document_extraction\" \"gemini-2.5-flash\""
    echo ""
    echo "Available Prompts:"
    echo "  OCR: ${OCR_PROMPTS[*]}"
    echo "  Analysis: ${ANALYSIS_PROMPTS[*]}"
    echo "  Compositions: ${COMPOSITIONS[*]}"
    echo ""
    echo "Available Models:"
    echo "  OpenAI: ${OPENAI_MODELS[*]}"
    echo "  Gemini: ${GEMINI_MODELS[*]}"
}

# List all available options
list_options() {
    echo -e "${BLUE}Available Prompts:${NC}"
    echo "  OCR Prompts:"
    for prompt in "${OCR_PROMPTS[@]}"; do
        echo "    - $prompt"
    done
    
    echo "  Analysis Prompts:"
    for prompt in "${ANALYSIS_PROMPTS[@]}"; do
        echo "    - $prompt"
    done
    
    echo "  Compositions:"
    for composition in "${COMPOSITIONS[@]}"; do
        echo "    - $composition"
    done
    
    echo ""
    echo -e "${BLUE}Available Models:${NC}"
    echo "  OpenAI Models:"
    for model in "${OPENAI_MODELS[@]}"; do
        echo "    - $model"
    done
    
    echo "  Gemini Models:"
    for model in "${GEMINI_MODELS[@]}"; do
        echo "    - $model"
    done
}

# Check if test files exist
check_test_files() {
    if [[ ! -f "$PDF_FILE" ]]; then
        echo -e "${RED}Error: PDF test file not found: $PDF_FILE${NC}"
        exit 1
    fi
    
    if [[ ! -f "$TXT_FILE" ]]; then
        echo -e "${RED}Error: TXT test file not found: $TXT_FILE${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Test files found${NC}"
    echo "  PDF: $PDF_FILE"
    echo "  TXT: $TXT_FILE"
    echo ""
}

# Main execution
main() {
    echo -e "${BLUE}Prompt Testing Matrix Script${NC}"
    echo "=================================================="
    
    # Load environment variables first
    load_environment
    
    # Check test files
    check_test_files
    
    case "${1:-help}" in
        "matrix")
            run_matrix_test
            ;;
        "prompt")
            if [[ -z "$2" ]]; then
                echo -e "${RED}Error: Please specify a prompt name${NC}"
                show_help
                exit 1
            fi
            test_prompt_all_models "$2"
            ;;
        "model")
            if [[ -z "$2" ]]; then
                echo -e "${RED}Error: Please specify a model name${NC}"
                show_help
                exit 1
            fi
            test_model_all_prompts "$2"
            ;;
        "specific")
            if [[ -z "$2" || -z "$3" ]]; then
                echo -e "${RED}Error: Please specify both prompt and model names${NC}"
                show_help
                exit 1
            fi
            test_specific "$2" "$3"
            ;;
        "list")
            list_options
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Run main function with all arguments
main "$@"
