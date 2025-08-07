#!/bin/bash
# Unified test runner for Real2.AI - Frontend and Backend
set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
FRONTEND_ONLY=false
BACKEND_ONLY=false
COVERAGE=false
PARALLEL=false
VERBOSE=false
COMPREHENSIVE=false
TEST_TYPE="unit"
COVERAGE_THRESHOLD=80

# Function to print colored output
print_header() {
    echo -e "${CYAN}===================================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}===================================================${NC}"
}

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

# Function to check if directory exists
check_directory() {
    if [[ ! -d "$1" ]]; then
        print_error "Directory $1 not found!"
        return 1
    fi
}

# Function to run frontend tests
run_frontend_tests() {
    print_header "Running Frontend Tests"
    
    check_directory "frontend" || return 1
    
    cd frontend
    
    # Check if node_modules exists
    if [[ ! -d "node_modules" ]]; then
        print_status "Installing frontend dependencies..."
        npm install
    fi
    
    # Build test command
    local test_cmd="npm run test"
    
    if [[ "$COVERAGE" == true ]]; then
        test_cmd="npm run test:coverage"
    fi
    
    if [[ "$VERBOSE" == true ]]; then
        test_cmd="$test_cmd -- --reporter=verbose"
    fi
    
    print_status "Executing: $test_cmd"
    
    if eval "$test_cmd"; then
        print_success "Frontend tests passed!"
        cd ..
        return 0
    else
        print_error "Frontend tests failed!"
        cd ..
        return 1
    fi
}

# Function to run backend tests
run_backend_tests() {
    print_header "Running Backend Tests"
    
    check_directory "backend" || return 1
    
    cd backend
    
    # Check for virtual environment
    if [[ -f ".venv/bin/activate" ]]; then
        print_status "Activating virtual environment (.venv)..."
        source .venv/bin/activate
    elif [[ -f "venv/bin/activate" ]]; then
        print_status "Activating virtual environment (venv)..."
        source venv/bin/activate
    else
        print_warning "No virtual environment found. Using system Python."
    fi
    
    # Use comprehensive test runner if requested
    if [[ "$COMPREHENSIVE" == true ]]; then
        print_status "Running comprehensive test suite..."
        
        if [[ -f "scripts/run_comprehensive_tests.py" ]]; then
            chmod +x scripts/run_comprehensive_tests.py
            if python scripts/run_comprehensive_tests.py; then
                print_success "Comprehensive backend tests passed!"
                cd ..
                return 0
            else
                print_error "Comprehensive backend tests failed!"
                cd ..
                return 1
            fi
        else
            print_warning "Comprehensive test script not found, falling back to regular tests."
        fi
    fi
    
    # Build pytest command directly
    local test_cmd="pytest"
    
    # Add test type filter
    case $TEST_TYPE in
        unit)
            test_cmd="$test_cmd -m 'unit'"
            ;;
        integration)
            test_cmd="$test_cmd -m 'integration'"
            ;;
        all)
            # Run all tests - no marker filter
            ;;
    esac
    
    # Add coverage
    if [[ "$COVERAGE" == true ]]; then
        test_cmd="$test_cmd --cov=app --cov-fail-under=$COVERAGE_THRESHOLD --cov-report=term-missing --cov-report=xml"
        test_cmd="$test_cmd --cov-report=html:htmlcov"
    fi
    
    # Add parallel execution
    if [[ "$PARALLEL" == true ]]; then
        test_cmd="$test_cmd -n auto"
    fi
    
    # Add verbosity
    if [[ "$VERBOSE" == true ]]; then
        test_cmd="$test_cmd -v"
    fi
    
    print_status "Executing: $test_cmd"
    
    if eval "$test_cmd"; then
        print_success "Backend tests passed!"
        cd ..
        return 0
    else
        print_error "Backend tests failed!"
        cd ..
        return 1
    fi
}

# Function to show help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "A unified test runner for Real2.AI frontend and backend"
    echo ""
    echo "Options:"
    echo "  --frontend-only        Run only frontend tests"
    echo "  --backend-only         Run only backend tests"
    echo "  --coverage             Generate coverage reports"
    echo "  --parallel             Run tests in parallel"
    echo "  --verbose              Enable verbose output"
    echo "  --comprehensive        Run comprehensive backend test suite (linting, type checking, security)"
    echo "  --test-type TYPE       Backend test type: unit, integration, all (default: unit)"
    echo "  --coverage-threshold N Coverage threshold percentage (default: 80)"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run both frontend and backend unit tests"
    echo "  $0 --frontend-only                   # Run only frontend tests"
    echo "  $0 --backend-only --test-type all    # Run all backend tests"
    echo "  $0 --coverage --coverage-threshold 90 # Run with 90% coverage requirement"
    echo "  $0 --comprehensive                   # Run comprehensive backend suite"
    echo "  $0 --parallel --verbose              # Run tests in parallel with verbose output"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --frontend-only)
            FRONTEND_ONLY=true
            shift
            ;;
        --backend-only)
            BACKEND_ONLY=true
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --comprehensive)
            COMPREHENSIVE=true
            shift
            ;;
        --test-type)
            TEST_TYPE="$2"
            shift 2
            ;;
        --coverage-threshold)
            COVERAGE_THRESHOLD="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate mutually exclusive options
if [[ "$FRONTEND_ONLY" == true && "$BACKEND_ONLY" == true ]]; then
    print_error "Cannot specify both --frontend-only and --backend-only"
    exit 1
fi

# Validate test type
if [[ ! "$TEST_TYPE" =~ ^(unit|integration|all)$ ]]; then
    print_error "Invalid test type: $TEST_TYPE. Valid types: unit, integration, all"
    exit 1
fi

# Validate coverage threshold
if ! [[ "$COVERAGE_THRESHOLD" =~ ^[0-9]+$ ]] || [[ "$COVERAGE_THRESHOLD" -lt 0 ]] || [[ "$COVERAGE_THRESHOLD" -gt 100 ]]; then
    print_error "Invalid coverage threshold: $COVERAGE_THRESHOLD. Must be a number between 0-100"
    exit 1
fi

# Main execution
print_header "Real2.AI Test Runner"
print_status "Starting test execution..."

# Initialize result tracking
FRONTEND_RESULT=0
BACKEND_RESULT=0
TESTS_RUN=0

# Run tests based on options
if [[ "$BACKEND_ONLY" == true ]]; then
    run_backend_tests
    BACKEND_RESULT=$?
    TESTS_RUN=1
elif [[ "$FRONTEND_ONLY" == true ]]; then
    run_frontend_tests
    FRONTEND_RESULT=$?
    TESTS_RUN=1
else
    # Run both frontend and backend tests
    print_status "Running both frontend and backend tests..."
    
    run_frontend_tests
    FRONTEND_RESULT=$?
    
    run_backend_tests
    BACKEND_RESULT=$?
    
    TESTS_RUN=2
fi

# Final results
print_header "Test Results Summary"

if [[ "$TESTS_RUN" -eq 2 ]]; then
    if [[ "$FRONTEND_RESULT" -eq 0 ]]; then
        print_success "✅ Frontend tests: PASSED"
    else
        print_error "❌ Frontend tests: FAILED"
    fi
    
    if [[ "$BACKEND_RESULT" -eq 0 ]]; then
        print_success "✅ Backend tests: PASSED"
    else
        print_error "❌ Backend tests: FAILED"
    fi
    
    # Overall result
    if [[ "$FRONTEND_RESULT" -eq 0 && "$BACKEND_RESULT" -eq 0 ]]; then
        print_success "🎉 ALL TESTS PASSED!"
        exit 0
    else
        print_error "💥 SOME TESTS FAILED!"
        exit 1
    fi
elif [[ "$FRONTEND_ONLY" == true ]]; then
    if [[ "$FRONTEND_RESULT" -eq 0 ]]; then
        print_success "🎉 FRONTEND TESTS PASSED!"
        exit 0
    else
        print_error "💥 FRONTEND TESTS FAILED!"
        exit 1
    fi
elif [[ "$BACKEND_ONLY" == true ]]; then
    if [[ "$BACKEND_RESULT" -eq 0 ]]; then
        print_success "🎉 BACKEND TESTS PASSED!"
        exit 0
    else
        print_error "💥 BACKEND TESTS FAILED!"
        exit 1
    fi
fi