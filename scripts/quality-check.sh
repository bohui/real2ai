#!/bin/bash
# Quality Check Script
# Runs comprehensive code quality checks for Real2AI

set -e  # Exit on any error

echo "🔍 Running Real2AI Quality Checks..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Error counter
ERRORS=0

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        ((ERRORS++))
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Navigate to project root
cd "$(dirname "$0")/.."

echo "📂 Project root: $(pwd)"

# Backend checks
echo -e "\n🐍 Backend Checks"
echo "=================="

cd backend

# Check if uv is available
if ! command -v uv &> /dev/null; then
    print_warning "uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
uv sync --quiet
print_status $? "Dependencies installed"

# Python linting
echo "🧹 Running Python linting..."
uv run black --check --quiet .
print_status $? "Black formatting check"

uv run isort --check-only --quiet .
print_status $? "Import sorting check"

uv run flake8 --quiet .
print_status $? "Flake8 linting"

# Type checking
echo "🔍 Running type checking..."
uv run mypy app/ --ignore-missing-imports --quiet
print_status $? "MyPy type checking"

# Security scan
echo "🔒 Running security scan..."
uv run bandit -r app/ -f json -o bandit-report.json --quiet || true
if [ -f bandit-report.json ]; then
    BANDIT_ISSUES=$(cat bandit-report.json | python -c "import sys, json; print(len(json.load(sys.stdin)['results']))")
    if [ "$BANDIT_ISSUES" -gt 0 ]; then
        echo "Found $BANDIT_ISSUES security issues"
        print_status 1 "Bandit security scan"
    else
        print_status 0 "Bandit security scan"
    fi
    rm -f bandit-report.json
else
    print_status 0 "Bandit security scan"
fi

# Test collection
echo "🧪 Testing pytest collection..."
uv run pytest --collect-only --quiet -q > /dev/null
print_status $? "Pytest collection"

# Look for debug statements
echo "🐛 Checking for debug statements..."
if grep -r "pdb\.set_trace\|ipdb\.set_trace\|breakpoint(" app/ --exclude-dir=tests > /dev/null 2>&1; then
    print_status 1 "No debug statements in production code"
else
    print_status 0 "No debug statements in production code"
fi

# Look for TODO/FIXME
echo "📝 Checking for TODO/FIXME..."
TODO_COUNT=$(grep -r "TODO\|FIXME" app/ --exclude-dir=tests | wc -l || echo 0)
if [ "$TODO_COUNT" -gt 0 ]; then
    print_warning "Found $TODO_COUNT TODO/FIXME items in production code"
else
    print_status 0 "No TODO/FIXME in production code"
fi

# Check dependency management
echo "📋 Checking dependency management..."
if [ -f requirements.txt ] || [ -f requirements-test.txt ]; then
    print_status 1 "Legacy requirements files found (should use pyproject.toml)"
else
    print_status 0 "Using pyproject.toml for dependencies"
fi

cd ..

# Frontend checks
echo -e "\n🌐 Frontend Checks"
echo "=================="

cd frontend

# Check if pnpm is available
if ! command -v pnpm &> /dev/null; then
    print_warning "pnpm not found. Install with: npm install -g pnpm"
else
    # Install dependencies
    echo "📦 Installing frontend dependencies..."
    pnpm install --silent
    print_status $? "Frontend dependencies installed"

    # TypeScript checking
    echo "🔍 Running TypeScript checking..."
    pnpm tsc --noEmit --quiet
    print_status $? "TypeScript checking"

    # Look for console.log in production code
    echo "🖥️  Checking for console.log in production code..."
    if grep -r "console\.log" src --exclude-dir=__tests__ --exclude="*.test.*" --exclude="logger.ts" > /dev/null 2>&1; then
        print_status 1 "No console.log in production code (use logger instead)"
    else
        print_status 0 "No console.log in production code"
    fi

    # Check if logger is used instead
    echo "📊 Checking logger usage..."
    if grep -r "logger\." src > /dev/null 2>&1; then
        print_status 0 "Using logger for debugging"
    else
        print_warning "No logger usage detected"
    fi
fi

cd ..

# Git checks
echo -e "\n📋 Git Repository Checks"
echo "========================"

# Check for large files
echo "📦 Checking for large files..."
LARGE_FILES=$(find . -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" | xargs wc -l 2>/dev/null | awk '$1 > 1000 {print $2}' | grep -v total || echo "")
if [ -n "$LARGE_FILES" ]; then
    print_warning "Files over 1000 lines found:\n$LARGE_FILES"
else
    print_status 0 "No overly large files (>1000 lines)"
fi

# Check for sensitive files
echo "🔐 Checking for sensitive files..."
if find . -name "*.key" -o -name "*.pem" -o -name "*secret*" -o -name "*password*" | grep -v ".gitignore" > /dev/null 2>&1; then
    SENSITIVE_FILES=$(find . -name "*.key" -o -name "*.pem" -o -name "*secret*" -o -name "*password*" | grep -v ".gitignore")
    print_warning "Potential sensitive files found:\n$SENSITIVE_FILES"
else
    print_status 0 "No obvious sensitive files in repository"
fi

# Final summary
echo -e "\n📊 Quality Check Summary"
echo "========================"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Code quality looks good.${NC}"
    exit 0
else
    echo -e "${RED}❌ $ERRORS checks failed. Please address the issues above.${NC}"
    exit 1
fi