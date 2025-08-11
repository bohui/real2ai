#!/bin/bash
# Cleanup Check Script  
# Validates that codebase cleanup guidelines are followed

set -e

echo "🧹 Running Real2AI Cleanup Validation..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

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
    ((WARNINGS++))
}

# Navigate to project root
cd "$(dirname "$0")/.."

echo "🔍 Validating cleanup guidelines..."

# 1. Check for deprecated code markers
echo -e "\n🗑️  Checking for deprecated code..."
DEPRECATED_COUNT=$(grep -r "DEPRECATED\|@deprecated" backend/app --exclude-dir=tests | wc -l || echo 0)
if [ "$DEPRECATED_COUNT" -gt 0 ]; then
    print_warning "Found $DEPRECATED_COUNT deprecated markers - review for removal"
    grep -r "DEPRECATED\|@deprecated" backend/app --exclude-dir=tests | head -5
else
    print_status 0 "No deprecated code markers found"
fi

# 2. Check for legacy files
echo -e "\n📜 Checking for legacy files..."
LEGACY_FILES=""
if [ -f "backend/requirements.txt" ]; then
    LEGACY_FILES="$LEGACY_FILES backend/requirements.txt"
fi
if [ -f "backend/requirements-test.txt" ]; then
    LEGACY_FILES="$LEGACY_FILES backend/requirements-test.txt"
fi
if [ -f "backend/pytest.ini" ]; then
    LEGACY_FILES="$LEGACY_FILES backend/pytest.ini"
fi
if [ -f "backend/pytest-ci.ini" ]; then
    LEGACY_FILES="$LEGACY_FILES backend/pytest-ci.ini"
fi

if [ -n "$LEGACY_FILES" ]; then
    print_status 1 "Legacy dependency files should be removed: $LEGACY_FILES"
else
    print_status 0 "No legacy dependency files found"
fi

# 3. Check test configuration
echo -e "\n🧪 Checking test configuration..."
if grep -q "testpaths.*tests.*\." backend/pyproject.toml; then
    print_status 0 "Pytest configured to collect tests from multiple paths"
else
    print_warning "Pytest may not be configured to collect all tests"
fi

# 4. Check for proper logging usage
echo -e "\n📊 Checking logging practices..."

# Backend logging
PRINT_COUNT=$(grep -r "print(" backend/app --exclude-dir=tests | wc -l || echo 0)
if [ "$PRINT_COUNT" -gt 0 ]; then
    print_warning "Found $PRINT_COUNT print() statements in backend - consider using structured logging"
else
    print_status 0 "No print() statements in backend production code"
fi

# Frontend logging  
if [ -d "frontend/src" ]; then
    CONSOLE_COUNT=$(grep -r "console\.log" frontend/src --exclude-dir=__tests__ --exclude="*.test.*" --exclude="logger.ts" | wc -l || echo 0)
    if [ "$CONSOLE_COUNT" -gt 0 ]; then
        print_warning "Found $CONSOLE_COUNT console.log statements in frontend production code"
    else
        print_status 0 "No console.log in frontend production code"
    fi

    # Check if logger utility exists
    if [ -f "frontend/src/utils/logger.ts" ]; then
        print_status 0 "Frontend logger utility exists"
    else
        print_warning "Frontend logger utility not found"
    fi
fi

# 5. Check for debug statements
echo -e "\n🐛 Checking for debug statements..."
DEBUG_COUNT=$(grep -r "pdb\.set_trace\|ipdb\.set_trace\|breakpoint(" backend/app --exclude-dir=tests | wc -l || echo 0)
if [ "$DEBUG_COUNT" -gt 0 ]; then
    print_status 1 "Found debug statements in production code"
else
    print_status 0 "No debug statements in production code"
fi

# 6. Check examples organization
echo -e "\n📚 Checking examples organization..."
if [ -d "backend/examples" ]; then
    print_status 0 "Examples directory exists"
    
    # Check for README in examples
    if [ -f "backend/examples/README.md" ]; then
        print_status 0 "Examples README exists"
    else
        print_warning "Examples README missing"
    fi
else
    print_warning "Examples directory not found"
fi

# Check for scattered example files
SCATTERED_EXAMPLES=$(find backend -name "*example*.py" -o -name "*demo*.py" | grep -v "backend/examples" | grep -v ".venv" | wc -l || echo 0)
if [ "$SCATTERED_EXAMPLES" -gt 0 ]; then
    print_warning "Found $SCATTERED_EXAMPLES example/demo files outside examples directory"
else
    print_status 0 "All examples properly organized"
fi

# 7. Check documentation organization
echo -e "\n📖 Checking documentation organization..."
if [ -d "docs/archive" ]; then
    print_status 0 "Documentation archive exists"
else
    print_warning "Documentation archive directory missing"
fi

# Check for audit files in root
AUDIT_FILES=$(find . -maxdepth 1 -name "*AUDIT*" -o -name "*REPORT*" | grep -v "CODEBASE_DEEP_CLEAN_REPORT.md" | wc -l || echo 0)
if [ "$AUDIT_FILES" -gt 0 ]; then
    print_warning "Found audit/report files in root - consider archiving"
else
    print_status 0 "Audit files properly archived"
fi

# 8. Check dependency management
echo -e "\n📦 Checking dependency management..."
if [ -f "backend/pyproject.toml" ]; then
    print_status 0 "Using pyproject.toml for dependencies"
    
    # Check if uv.lock exists
    if [ -f "backend/uv.lock" ]; then
        print_status 0 "UV lock file exists"
    else
        print_warning "UV lock file missing"
    fi
else
    print_status 1 "pyproject.toml missing"
fi

# 9. Check security practices
echo -e "\n🔒 Checking security practices..."
if [ -f "SECURITY_CHECKLIST.md" ]; then
    print_status 0 "Security checklist exists"
else
    print_warning "Security checklist missing"
fi

# Check for exposed secrets
if git log --all --full-history --grep="password\|secret\|key\|token" --oneline | head -1 > /dev/null 2>&1; then
    print_warning "Git history may contain sensitive information references"
else
    print_status 0 "No obvious sensitive information in git history"
fi

# 10. Check automation setup
echo -e "\n⚙️  Checking automation setup..."
if [ -f "backend/.pre-commit-config.yaml" ]; then
    print_status 0 "Pre-commit hooks configured"
else
    print_warning "Pre-commit hooks not configured"
fi

if [ -f "scripts/quality-check.sh" ] && [ -x "scripts/quality-check.sh" ]; then
    print_status 0 "Quality check script exists and is executable"
else
    print_warning "Quality check script missing or not executable"
fi

# Summary
echo -e "\n📊 Cleanup Validation Summary"
echo "============================="

echo "Total files checked: $(find backend frontend -name "*.py" -o -name "*.ts" -o -name "*.tsx" | wc -l 2>/dev/null || echo "N/A")"
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"

if [ $ERRORS -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}✅ Cleanup validation passed with no issues!${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠️  Cleanup validation passed with $WARNINGS warnings.${NC}"
        exit 0
    fi
else
    echo -e "${RED}❌ Cleanup validation failed with $ERRORS errors and $WARNINGS warnings.${NC}"
    exit 1
fi