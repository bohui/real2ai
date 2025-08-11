# Real2.AI Backend Examples

This directory contains example scripts and demos that demonstrate how to use various components of the Real2.AI backend system.

## Structure

### `/clients/` - External API Client Examples
Examples demonstrating how to use external service clients:
- `corelogic_example.py` - CoreLogic property data API usage
- `domain_example.py` - Domain.com property search API usage

### `/integrations/` - System Integration Examples  
Examples showing how to integrate with core system components:
- `example_semantic_analysis.py` - Semantic analysis integration
- `integration_example.py` - General system integration
- `workflow_integration_example.py` - LangGraph workflow integration
- `ocr_example.py` - OCR service integration

### `/demos/` - Demonstration Scripts
Standalone demo scripts for testing and learning:
- `security_demo.py` - Security features demonstration
- `simple_test.py` - Simple system test script

### `/prompts/` - Prompt System Examples
Examples for working with the prompt management system:
- `prompt_system_examples.py` - Prompt composition and management

## Usage Guidelines

### Prerequisites
Ensure you have the development environment set up:

```bash
# Install dependencies
uv sync

# Activate virtual environment (if needed)
source .venv/bin/activate
```

### Running Examples

Most examples can be run directly:

```bash
# Run from the backend directory
cd /path/to/backend
python examples/demos/simple_test.py

# Or with uv
uv run examples/demos/simple_test.py
```

### Environment Setup

Many examples require environment variables. Create a `.env` file in the backend directory:

```bash
# Required for most examples
OPENAI_API_KEY=your_openai_key
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key

# For external API examples
DOMAIN_API_KEY=your_domain_key
CORELOGIC_API_KEY=your_corelogic_key
```

### Integration with Main System

These examples demonstrate integration patterns but should not be used directly in production code. Instead:

1. **Study the patterns** - Understand how components interact
2. **Follow the architecture** - Use repository patterns and dependency injection
3. **Add proper error handling** - Examples may have simplified error handling
4. **Add proper logging** - Use structured logging in production
5. **Add proper testing** - Examples may not include comprehensive tests

## Development Notes

### Migrated Files
The following files were moved from the root backend directory during cleanup:
- `example_semantic_analysis.py` → `examples/integrations/`
- `integration_example.py` → `examples/integrations/`
- `workflow_integration_example.py` → `examples/integrations/`
- `security_demo.py` → `examples/demos/`
- `simple_test.py` → `examples/demos/`

### Client Examples
Client examples in this directory are copies of the original files which remain in their respective client directories for reference during development.

### Testing Examples

To test if examples are working:

```bash
# Run the simple test
uv run examples/demos/simple_test.py

# Check client connectivity (requires API keys)
uv run examples/clients/domain_example.py
```

## Contributing

When adding new examples:

1. Choose the appropriate subdirectory
2. Include clear docstrings and comments
3. Document any required environment variables
4. Add an entry to this README
5. Ensure the example is self-contained where possible

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the backend directory
2. **Missing Dependencies**: Run `uv sync` to install all dependencies  
3. **API Key Errors**: Check your `.env` file configuration
4. **Database Errors**: Ensure Supabase connection details are correct

### Getting Help

- Check the main documentation in `/docs/`
- Review the actual service implementations in `/app/`
- Run tests to ensure your environment is working: `uv run pytest`

---
Created during codebase cleanup: 2025-01-16