# Scripts

This directory contains utility scripts for the Real2.AI backend.

## Available Scripts

### Prompt Validation

**`validate_prompt.py`** - Comprehensive prompt template validation CLI

A production-ready CLI tool for validating prompt templates with quality scoring, issue detection, and comprehensive reporting.

#### Usage

```bash
# Validate a single template
python scripts/validate_prompt.py validate app/prompts/user/analysis/contract_analysis.md

# Validate all templates in a directory
python scripts/validate_prompt.py validate-all app/prompts/user

# Show detailed information about a template
python scripts/validate_prompt.py info app/prompts/user/analysis/contract_analysis.md
```

#### Features

- **Quality Scoring**: 0.0-1.0 scale with detailed breakdown
- **Issue Detection**: Warnings, errors, and suggestions for improvement
- **Comprehensive Metrics**: Content length, variable usage, template structure
- **Batch Validation**: Validate entire directories of templates
- **Template Analysis**: Detailed information about template structure and metadata

#### Validation Checks

- Template syntax and structure
- Variable usage and consistency
- Content quality and readability
- Security pattern detection
- Performance optimization suggestions
- Best practice compliance

#### Example Output

```
🔍 Validating template: contract_analysis.md

📊 Validation Results for contract_analysis.md
----------------------------------------
✅ Template is VALID (Score: 0.95)
📏 Content Length: 2393
🔤 Variable Count: 2
🏷️  Tags Found: 5

⚠️  Issues Found (2):
  1. ⚠️ [WARNING] Found 4 sentences with >30 words
     💡 Suggestion: Break down complex sentences for better clarity
  2. ℹ️ [INFO] No model compatibility specified
     💡 Suggestion: Specify compatible AI models
```

### Database Management

**`migrate.py`** - Database migration utility

**`seed_database.py`** - Database seeding and test data creation

**`clear_data.py`** - Data cleanup and reset utilities

### Testing and Validation

**`run_comprehensive_tests.py`** - Comprehensive test suite runner

**`validate_repository_migration.py` - Repository migration validation

### Requirements Management

**`generate_requirements.sh`** - Generate requirements files for different environments

## Running Scripts

All scripts should be run from the `backend` directory with the virtual environment activated:

```bash
cd backend
source .venv/bin/activate

# Run any script
python scripts/validate_prompt.py --help
```

## Script Dependencies

Most scripts require:
- Python 3.8+
- Virtual environment with dependencies installed
- Proper environment variables configured
- Database connection (for database-related scripts)

## Contributing

When adding new scripts:
1. Follow the existing naming convention
2. Include proper error handling
3. Add help text and usage examples
4. Update this README with documentation
5. Ensure the script is executable (`chmod +x`)
6. Test thoroughly before committing