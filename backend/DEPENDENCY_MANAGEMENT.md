# Dependency Management

This project uses `uv` for Python dependency management with `pyproject.toml` as the source of truth.

## Installation

### Development Setup
```bash
# Install all dependencies including dev/test
uv sync

# Install specific optional dependencies
uv sync --extra test
uv sync --extra docs
```

### Production Setup  
```bash
# Install only production dependencies
uv sync --no-dev
```

## Dependency Groups

### Core Dependencies (`[project.dependencies]`)
Production dependencies required for the application to run:
- FastAPI, Uvicorn for web framework
- Supabase, AsyncPG for database  
- OpenAI, Google GenAI, LangChain for AI/ML
- Redis, Celery for background processing
- And more...

### Development Dependencies (`[project.optional-dependencies.dev]`)
Development tools and utilities:
- pytest, pytest-asyncio for testing
- black, isort, flake8, mypy for code quality
- pre-commit for git hooks

### Test Dependencies (`[project.optional-dependencies.test]`)
Testing-specific dependencies:
- pytest with plugins (cov, mock, xdist)
- httpx, requests-mock for HTTP testing
- factory-boy, faker for test data
- freezegun for time mocking

### Documentation Dependencies (`[project.optional-dependencies.docs]`)  
Documentation generation tools:
- mkdocs with material theme
- mkdocstrings for API documentation

## Key Files

- `pyproject.toml` - Source of truth for all dependencies and metadata
- `uv.lock` - Lockfile with exact versions for reproducible installs  
- ~~`requirements.txt`~~ - **REMOVED** - Legacy, use pyproject.toml instead
- ~~`requirements-test.txt`~~ - **REMOVED** - Legacy, use `[test]` extra instead

## Adding Dependencies

```bash
# Add a production dependency
uv add package-name

# Add a development dependency  
uv add --group dev package-name

# Add a test dependency
uv add --optional test package-name
```

## Generating Requirements Files (if needed for deployment)

If deployment targets require requirements.txt format:

```bash
# Generate requirements.txt from lockfile
uv export --format requirements-txt --output requirements.txt

# Generate with dev dependencies
uv export --format requirements-txt --extra dev --output requirements-dev.txt
```

Or use the helper script:

```bash
bash scripts/generate_requirements.sh
```

## Migration Notes

- **2025-01-16**: Removed legacy `requirements.txt` and `requirements-test.txt` files
- All dependencies now managed via `pyproject.toml` + `uv.lock`
- Use `uv sync` instead of `pip install -r requirements.txt`