#!/bin/bash

# Prompt Testing Matrix Script
# This script allows you to test individual prompts with different models
# using test_files/contract.pdf and test_files/contract.md (preferred) or contract.txt as input

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

# Prefer project venv python if available
PYTHON_BIN="python3"
if [[ -x "$SCRIPT_DIR/venv/bin/python" ]]; then
    PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"
fi

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

    # Ensure a default to silence non-production warning in tests
    if [[ -z "$SUPABASE_JWT_SECRET" ]]; then
        export SUPABASE_JWT_SECRET="test-secret"
    fi
}

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Test files
PDF_FILE="$TEST_FILES_DIR/contract.pdf"
CONTRACT_MD="$TEST_FILES_DIR/contract.md"
CONTRACT_TXT="$TEST_FILES_DIR/contract.txt"

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
    "process_entire_document": true,
    "is_multi_page": false,
    "use_quick_mode": false
}
EOF
            ;;
        "analysis")
            # Safely embed contract text for analysis prompts if available
            local CONTRACT_TEXT_JSON
            # Prefer Markdown contract text, fallback to TXT
            local CONTRACT_SOURCE=""
            if [[ -f "$CONTRACT_MD" ]]; then
                CONTRACT_SOURCE="$CONTRACT_MD"
            elif [[ -f "$CONTRACT_TXT" ]]; then
                CONTRACT_SOURCE="$CONTRACT_TXT"
            fi
            if [[ -n "$CONTRACT_SOURCE" && -f "$CONTRACT_SOURCE" ]]; then
                CONTRACT_TEXT_JSON=$(TXT_FILE="$CONTRACT_SOURCE" "$PYTHON_BIN" - << 'PY'
import json, os
path = os.environ.get("TXT_FILE")
try:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    # Trim excessively long test inputs to keep outputs manageable
    if len(content) > 50000:
        content = content[:50000]
    print(json.dumps(content))
except Exception:
    print(json.dumps("Sample contract text for testing."))
PY
                )
            else
                CONTRACT_TEXT_JSON="\"Sample contract text for testing.\""
            fi
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
    "file_type": "pdf",
    "australian_state": "NSW",
    "analysis_type": "comprehensive",
    "contract_text": $CONTRACT_TEXT_JSON,
    "transaction_value": null,
    "state_requirements": "Placeholder summary of NSW-specific legal requirements for residential property contracts.",
    "consumer_protection": "Placeholder consumer protection framework overview (cooling-off, misleading conduct, statutory warranties).",
    "contract_types": "Placeholder guidance for common contract types (purchase agreement, lease, option).",
    "user_experience": "novice",
    "analysis_depth": "comprehensive"
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
from datetime import datetime, timezone
import csv
import hashlib

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.prompts.manager import get_prompt_manager
from app.core.prompts.context import PromptContext, ContextType
from app.clients.openai.config import OpenAISettings
from app.clients.openai.client import OpenAIClient
from app.clients.gemini.config import GeminiSettings
from app.clients.gemini.client import GeminiClient

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
        result = None
        if "$test_type" == "composition":
            result = await prompt_manager.render_composed(
                composition_name="$prompt_name",
                context=context
            )
        else:
            rendered = await prompt_manager.render(
                template_name="$prompt_name",
                context=context,
                model="$model_name"
            )
            # Wrap legacy render into composition-like structure
            result = {
                "system_prompt": "",
                "user_prompt": rendered,
                "metadata": {
                    "composition": "$prompt_name",
                    "composition_version": "",
                    "user_prompts": ["$prompt_name"],
                    "user_prompt_versions": {},
                    "system_prompts": [],
                    "system_prompt_versions": {},
                    "composed_at": datetime.now(timezone.utc).isoformat(),
                }
            }
        
        # Prepare artifacts (deduplicated by content hash) and emit CSV row (only table output)
        try:
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            meta = result.get('metadata', {})
            composition_name = meta.get('composition', '$prompt_name')
            composition_version = meta.get('composition_version', '')
            system_prompts = meta.get('system_prompts', [])
            user_prompts = meta.get('user_prompts', [])
            system_versions = meta.get('system_prompt_versions', {})
            user_versions = meta.get('user_prompt_versions', {})
            system_names = "; ".join([p.get('name', str(p)) if isinstance(p, dict) else str(p) for p in system_prompts]) if isinstance(system_prompts, list) else str(system_prompts)
            user_names = "; ".join(user_prompts) if isinstance(user_prompts, list) else str(user_prompts)
            system_versions_str = "; ".join([f"{k}:{v}" for k,v in system_versions.items()])
            user_versions_str = "; ".join([f"{k}:{v}" for k,v in user_versions.items()])
            system_prompt = (result.get('system_prompt', '') or '')
            user_prompt = (result.get('user_prompt', '') or '')
            status = 'success'

            # Save artifacts with content hash to avoid duplicates
            artifacts_dir = Path('$OUTPUT_DIR') / 'artifacts'
            prompts_dir = artifacts_dir / 'prompts'
            outputs_dir = artifacts_dir / 'outputs'
            prompts_dir.mkdir(parents=True, exist_ok=True)
            outputs_dir.mkdir(parents=True, exist_ok=True)

            def sanitize(name: str) -> str:
                return (
                    name.replace('/', '_')
                    .replace(' ', '_')
                    .replace(':', '_')
                )

            comp_safe = sanitize(composition_name)
            model_safe = sanitize('$model_name')

            def save_text(content: str, kind: str, ext: str = 'md') -> str:
                if not content:
                    return ''
                h = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
                fname = f"{comp_safe}__{model_safe}__{kind}__{h}.{ext}"
                target_dir = prompts_dir if kind in ('system', 'user') else outputs_dir
                fpath = target_dir / fname
                if not fpath.exists():
                    # Write content
                    with open(fpath, 'w', encoding='utf-8') as fp:
                        fp.write(content)
                return str(fpath.resolve())

            system_prompt_path = save_text(system_prompt, 'system', 'md')
            user_prompt_path = save_text(user_prompt, 'user', 'md')
            # Execute model via existing clients and save output
            selected_model = "$model_name"
            output_path = ''
            # Disable tracing/instrumentation to avoid hanging if not configured
            os.environ.setdefault("LANGSMITH_TRACING", "0")
            os.environ.setdefault("LANGSMITH_API_KEY", "")
            os.environ.setdefault("OPENAI_INIT_CONNECTION_TEST", "false")

            # Credential preflight
            def missing(env):
                return not os.getenv(env)

            preflight_error = None
            if selected_model.lower().startswith('gemini'):
                if missing('GOOGLE_APPLICATION_CREDENTIALS') and missing('GEMINI_CREDENTIALS_PATH') and missing('GOOGLE_CLOUD_PROJECT'):
                    preflight_error = 'Missing Gemini credentials (GOOGLE_APPLICATION_CREDENTIALS or GEMINI_CREDENTIALS_PATH)'
            else:
                # Always use OPENAI_* for both OpenAI and OpenRouter-style models
                if missing('OPENAI_API_KEY'):
                    preflight_error = 'Missing OPENAI_API_KEY for OpenAI/OpenRouter model'

            if preflight_error:
                status = 'fail'
                output_path = save_text(f'preflight_error: {preflight_error}', 'output', 'txt')
            else:
                try:
                    response_text = ''
                    if selected_model.lower().startswith('gemini'):
                        g_settings = GeminiSettings()
                        g_config = g_settings.to_client_config()
                        g_config.model_name = selected_model
                        g_client = GeminiClient(g_config)
                        await g_client.initialize()
                        response_text = await asyncio.wait_for(
                            g_client.generate_content(
                                user_prompt,
                                system_prompt=system_prompt,
                                model=g_config.model_name,
                            ),
                            timeout=30,
                        )
                    else:
                        # Build OpenAI config directly from OPENAI_* envs (ignore OpenRouter envs)
                        from app.clients.openai.config import OpenAIClientConfig
                        api_key = os.getenv('OPENAI_API_KEY', '')
                        api_base = os.getenv('OPENAI_API_BASE')
                        organization = os.getenv('OPENAI_ORGANIZATION')
                        o_config = OpenAIClientConfig(
                            api_key=api_key,
                            api_base=api_base,
                            model_name=selected_model,
                            organization=organization,
                            extra_config={'init_connection_test': False},
                        )
                        o_client = OpenAIClient(o_config)
                        await o_client.initialize()
                        response_text = await asyncio.wait_for(
                            o_client.generate_content(
                                user_prompt,
                                system_prompt=system_prompt,
                                model=o_config.model_name,
                            ),
                            timeout=30,
                        )
                    # Save output; prefer JSON parse, else wrap in {text}
                    try:
                        parsed = json.loads(response_text)
                        output_json = json.dumps(parsed, ensure_ascii=False, indent=2)
                    except Exception:
                        output_json = json.dumps({'text': response_text}, ensure_ascii=False, indent=2)
                    output_path = save_text(output_json, 'output', 'json')
                except Exception as model_error:
                    status = 'fail'
                    output_path = save_text(f'model_error: {str(model_error)}', 'output', 'txt')
            # Prepare CSV header and row
            header = [
                'timestamp', 'model', 'composition_name', 'composition_version', 'result',
                'user_prompt_names', 'user_prompt_versions',
                'system_prompt_names', 'system_prompt_versions',
                'system_prompt_path', 'user_prompt_path', 'output_path'
            ]
            row = [
                now_str, '$model_name', composition_name, composition_version, status,
                user_names, user_versions_str,
                system_names, system_versions_str,
                system_prompt_path, user_prompt_path, output_path
            ]
            # Write to shared CSV file
            csv_path = str(Path('$OUTPUT_DIR') / 'metrics.csv')
            file_exists = Path(csv_path).exists() and Path(csv_path).stat().st_size > 0
            with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(header)
                writer.writerow(row)
            # Only CSV to stdout (use csv.writer for proper quoting)
            sw = csv.writer(sys.stdout)
            sw.writerow(header)
            sw.writerow(row)
        except Exception:
            pass
        
        return True
        
    except Exception as e:
        # Emit failure CSV table
        try:
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            header = [
                'timestamp', 'model', 'composition_name', 'composition_version', 'result',
                'user_prompt_names', 'user_prompt_versions',
                'system_prompt_names', 'system_prompt_versions',
                'system_prompt_path', 'user_prompt_path', 'output_path'
            ]
            row = [
                now_str, '$model_name', '$prompt_name', '', 'fail',
                '', '',
                '', '',
                '', '', str(e)
            ]
            csv_path = str(Path('$OUTPUT_DIR') / 'metrics.csv')
            file_exists = Path(csv_path).exists() and Path(csv_path).stat().st_size > 0
            with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(header)
                writer.writerow(row)
            sw = csv.writer(sys.stdout)
            sw.writerow(header)
            sw.writerow(row)
        except Exception:
            pass
        return False

if __name__ == "__main__":
    success = asyncio.run(test_prompt())
    sys.exit(0 if success else 1)
EOF
    
    # Make executable and run
    chmod +x "$test_script"
    
    # Run the test
    local result_file="$OUTPUT_DIR/result_${prompt_name//\//_}_${model_name//[^a-zA-Z0-9]/_}.txt"
    
    if "$PYTHON_BIN" "$test_script" > "$result_file" 2>&1; then
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
    
    # Normalize prompt name: allow callers to pass file paths like ".../name.md"
    if [[ "$prompt_name" == *.md ]]; then
        prompt_name="${prompt_name%.md}"
    fi

    # Determine test type
    local test_type="template"
    if [[ " ${COMPOSITIONS[@]} " =~ " ${prompt_name} " ]]; then
        test_type="composition"
    fi
    
    # Determine context type
    local context_type="ocr"
    # If explicitly in analysis list, or path indicates an analysis template, use analysis context
    if [[ " ${ANALYSIS_PROMPTS[@]} " =~ " ${prompt_name} " || "$prompt_name" == */analysis/* ]]; then
        context_type="analysis"
    elif [[ " ${COMPOSITIONS[@]} " =~ " ${prompt_name} " ]]; then
        context_type="composition"
    fi

    # Special-case mapping: deprecated template should use its composition
    if [[ "$prompt_name" == "user/ocr/whole_document_extraction" ]]; then
        test_type="composition"
        prompt_name="ocr_whole_document_extraction"
        # Keep OCR context for required variables
        context_type="ocr"
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

    if [[ ! -f "$CONTRACT_MD" && ! -f "$CONTRACT_TXT" ]]; then
        echo -e "${YELLOW}⚠  No contract.md or contract.txt found in $TEST_FILES_DIR${NC}"
        echo -e "${YELLOW}   Analysis prompts will fall back to sample text${NC}"
    else
        echo -e "${GREEN}✓ Contract text source found${NC}"
        if [[ -f "$CONTRACT_MD" ]]; then
            echo "  Contract (md): $CONTRACT_MD"
        fi
        if [[ -f "$CONTRACT_TXT" ]]; then
            echo "  Contract (txt): $CONTRACT_TXT"
        fi
    fi

    echo -e "${GREEN}✓ Test files found${NC}"
    echo "  PDF: $PDF_FILE"
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
