# Development Automation

This document describes the automation tools and quality checks implemented to maintain code quality and prevent regressions.

## Quality Assurance Tools

### 1. Pre-commit Hooks (`.pre-commit-config.yaml`)

Automated checks that run before each commit:

**Installation:**
```bash
cd backend
uv run pre-commit install
```

**What it checks:**
- **Code Formatting**: Black, isort for Python
- **Linting**: Flake8 for Python, Prettier for frontend
- **Security**: Bandit security scanning, private key detection
- **Quality**: No debug statements, no console.log in production
- **File Quality**: Trailing whitespace, large files, YAML/JSON syntax

**Running manually:**
```bash
# Run on all files
uv run pre-commit run --all-files

# Run on specific files
uv run pre-commit run --files app/services/document_service.py
```

### 2. Quality Check Script (`scripts/quality-check.sh`)

Comprehensive quality validation that runs:

**What it checks:**
- Python code formatting (Black, isort, Flake8)
- Type checking (MyPy)
- Security scanning (Bandit)
- Test collection (pytest)
- Debug statement detection
- TODO/FIXME detection
- Dependency management validation
- Frontend TypeScript checking
- Console.log detection in production code
- Large file detection
- Sensitive file detection

**Usage:**
```bash
# Run from project root
./scripts/quality-check.sh

# Or from backend directory
cd backend && ../scripts/quality-check.sh
```

### 3. Cleanup Validation Script (`scripts/cleanup-check.sh`)

Validates adherence to cleanup guidelines:

**What it validates:**
- No deprecated code markers
- No legacy dependency files
- Proper test configuration
- Logging best practices
- Debug statement removal
- Examples organization
- Documentation archiving
- Dependency management consolidation
- Security practices
- Automation setup

**Usage:**
```bash
# Run from project root
./scripts/cleanup-check.sh
```

## Automation Integration

### GitHub Actions (Recommended)

Create `.github/workflows/quality.yml`:

```yaml
name: Quality Checks
on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    - name: Install uv
      run: curl -LsSf https://astral.sh/uv/install.sh | sh
    - name: Run quality checks
      run: ./scripts/quality-check.sh
    - name: Run cleanup validation
      run: ./scripts/cleanup-check.sh
```

### Local Development Workflow

1. **Initial Setup:**
   ```bash
   cd backend
   uv sync
   uv run pre-commit install
   ```

2. **Before Committing:**
   ```bash
   # Pre-commit hooks run automatically
   git commit -m "Your changes"
   
   # Or run manually first
   uv run pre-commit run
   ```

3. **Before Pushing:**
   ```bash
   # Run comprehensive quality checks
   ./scripts/quality-check.sh
   
   # Validate cleanup compliance
   ./scripts/cleanup-check.sh
   ```

## Preventing Common Issues

### Debug Statements
- **Blocked by**: Pre-commit hooks, quality checks
- **Alternative**: Use structured logging with `logger.debug()`

### Console.log in Production
- **Blocked by**: Pre-commit hooks, quality checks
- **Alternative**: Use `frontend/src/utils/logger.ts`

### Large Files
- **Blocked by**: Pre-commit hooks
- **Guideline**: Max 1000 lines per file, break into smaller modules

### Legacy Dependencies
- **Blocked by**: Cleanup validation
- **Guideline**: Use only `pyproject.toml` + `uv.lock`

### Deprecated Code
- **Detected by**: Cleanup validation
- **Action**: Remove deprecated markers and old code

### Scattered Examples
- **Detected by**: Cleanup validation
- **Guideline**: All examples in `backend/examples/`

## Configuration Files

### `pyproject.toml`
- Contains all Python dependencies
- Pytest configuration
- Tool configurations (Black, isort, etc.)

### `.pre-commit-config.yaml`  
- Pre-commit hook definitions
- Security and quality checks
- Custom hooks for project-specific rules

### `frontend/src/utils/logger.ts`
- Centralized logging utility
- Development/production log handling
- Replaces console.log statements

## Troubleshooting

### Pre-commit Issues
```bash
# Update hook versions
uv run pre-commit autoupdate

# Skip hooks temporarily (not recommended)
git commit --no-verify
```

### Quality Check Failures
```bash
# Fix formatting issues
cd backend
uv run black .
uv run isort .

# Fix linting issues
uv run flake8 . --show-source
```

### Performance
- **Pre-commit**: Runs only on changed files (fast)
- **Quality checks**: Runs on entire codebase (~2-5 minutes)
- **Cleanup validation**: Lightweight scanning (~30 seconds)

## Maintenance

### Regular Updates
1. Update pre-commit hooks: `uv run pre-commit autoupdate`
2. Update tool versions in automation scripts
3. Review and update quality thresholds as needed

### Adding New Checks
1. Add to `.pre-commit-config.yaml` for commit-time checks
2. Add to `quality-check.sh` for comprehensive validation  
3. Add to `cleanup-check.sh` for maintenance guidelines
4. Document in this file

---
Created during deep cleanup: 2025-01-16