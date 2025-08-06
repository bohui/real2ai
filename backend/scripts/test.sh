#!/bin/bash
# Production-grade test runner for Real2.AI backend
set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="unit"
COVERAGE_THRESHOLD=80
PARALLEL=false
VERBOSE=false
HTML_REPORT=false

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --type)
            TEST_TYPE="$2"
            shift 2
            ;;
        --coverage)
            COVERAGE_THRESHOLD="$2"
            shift 2
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --html)
            HTML_REPORT=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --type TYPE          Test type: unit, integration, all (default: unit)"
            echo "  --coverage PERCENT   Coverage threshold (default: 80)"
            echo "  --parallel           Run tests in parallel"
            echo "  --verbose            Verbose output"
            echo "  --html               Generate HTML coverage report"
            echo "  -h, --help           Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Activate virtual environment if it exists
if [[ -f ".venv/bin/activate" ]]; then
    print_status "Activating virtual environment..."
    source .venv/bin/activate
elif [[ -f "venv/bin/activate" ]]; then
    print_status "Activating virtual environment..."
    source venv/bin/activate
fi

# Build pytest command
PYTEST_CMD="pytest"

# Add verbosity
if [[ "$VERBOSE" == true ]]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add parallel execution
if [[ "$PARALLEL" == true ]]; then
    PYTEST_CMD="$PYTEST_CMD -n auto"
fi

# Add coverage settings
PYTEST_CMD="$PYTEST_CMD --cov=app --cov-fail-under=$COVERAGE_THRESHOLD"

# Add coverage reports
if [[ "$HTML_REPORT" == true ]]; then
    PYTEST_CMD="$PYTEST_CMD --cov-report=html:htmlcov"
fi
PYTEST_CMD="$PYTEST_CMD --cov-report=term-missing:skip-covered --cov-report=xml"

# Add test type markers
case $TEST_TYPE in
    unit)
        PYTEST_CMD="$PYTEST_CMD -m 'unit'"
        ;;
    integration)
        PYTEST_CMD="$PYTEST_CMD -m 'integration'"
        ;;
    slow)
        PYTEST_CMD="$PYTEST_CMD -m 'slow'"
        ;;
    all)
        # Run all tests
        ;;
    *)
        print_error "Invalid test type: $TEST_TYPE"
        print_error "Valid types: unit, integration, slow, all"
        exit 1
        ;;
esac

# Run pre-test checks
print_status "Running pre-test validation..."

# Check if required packages are installed
python -c "import app" 2>/dev/null || {
    print_error "App module not found. Please install dependencies."
    exit 1
}

# Check database connection (if needed)
if [[ "$TEST_TYPE" == "integration" || "$TEST_TYPE" == "all" ]]; then
    print_status "Checking database connection..."
    python -c "import asyncio; from app.clients.factory import get_supabase_client; asyncio.run(get_supabase_client())" 2>/dev/null || {
        print_warning "Database connection failed. Integration tests may fail."
    }
fi

# Run the tests
print_status "Running $TEST_TYPE tests..."
print_status "Command: $PYTEST_CMD"

if eval "$PYTEST_CMD"; then
    print_success "All tests passed!"
    
    # Show coverage summary
    if [[ "$HTML_REPORT" == true ]]; then
        print_status "HTML coverage report generated: htmlcov/index.html"
    fi
    
    exit 0
else
    print_error "Tests failed!"
    exit 1
fi