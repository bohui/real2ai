# Testing Guide

## Single Entry Point

Use the unified test runner script:

```bash
./run-tests.sh [OPTIONS]
```

## Quick Examples

```bash
# Run all tests (frontend + backend unit tests)
./run-tests.sh

# Frontend only
./run-tests.sh --frontend-only

# Backend only with coverage
./run-tests.sh --backend-only --coverage

# All backend test types with high coverage threshold
./run-tests.sh --backend-only --test-type all --coverage --coverage-threshold 90

# Comprehensive backend testing (includes linting, type checking, security)
./run-tests.sh --backend-only --comprehensive

# Parallel execution with verbose output
./run-tests.sh --parallel --verbose
```

## Available Options

| Option | Description |
|--------|-------------|
| `--frontend-only` | Run only frontend tests |
| `--backend-only` | Run only backend tests |
| `--coverage` | Generate coverage reports |
| `--parallel` | Run tests in parallel |
| `--verbose` | Enable verbose output |
| `--comprehensive` | Run comprehensive backend suite (linting, type checking, security) |
| `--test-type TYPE` | Backend test type: `unit`, `integration`, `all` (default: `unit`) |
| `--coverage-threshold N` | Coverage threshold percentage (default: 80) |

## Test Types

- **unit**: Fast unit tests
- **integration**: Integration tests (require database connection)
- **all**: All tests including unit and integration

## Comprehensive Testing

The `--comprehensive` flag runs the full backend test suite including:
- Code linting (Flake8)
- Type checking (MyPy)
- Security vulnerability scanning
- Dependency checks
- All test types with detailed reporting

## Coverage Reports

When using `--coverage`:
- Terminal output shows coverage summary
- HTML reports generated in `backend/htmlcov/`
- XML reports for CI/CD integration

## Legacy Scripts

The following scripts have been consolidated into `run-tests.sh`:
- ~~`backend/scripts/test.sh`~~ (removed)
- `backend/scripts/run_comprehensive_tests.py` (still available for `--comprehensive` option)