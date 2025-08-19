# LangGraph Contract Analysis Workflow

## Overview

This document describes the LangGraph-based contract analysis workflow that processes real estate contracts using AI models.

## Architecture

The workflow uses a node-based architecture where each processing step is encapsulated in a dedicated node class.

## Concurrent Update Protection

### Problem: InvalidUpdateError

The workflow was experiencing `InvalidUpdateError: At key 'user_id': Can receive only one value per step. Use an Annotated key to handle multiple values.` errors due to LangGraph's concurrent update requirements.

### Root Cause

1. **Missing Annotated Types**: Fields in the state model were not properly annotated for concurrent updates
2. **Concurrent Node Execution**: Multiple workflow nodes could update the state simultaneously
3. **LangGraph Requirements**: LangGraph requires all fields that can be updated concurrently to use `Annotated` types with reducer functions

### Solution

All state fields are now properly annotated with appropriate reducer functions:

```python
class RealEstateAgentState(TypedDict):
    # Session Management
    user_id: Annotated[str, lambda x, y: y]  # Last value wins
    session_id: Annotated[str, lambda x, y: y]  # Last value wins
    
    # Lists use add reducer for concatenation
    current_step: Annotated[List[str], add]
    
    # Dictionaries use merge reducer
    analysis_results: Annotated[
        Dict[str, Any],
        lambda existing, incoming: {**(existing or {}), **(incoming or {})},
    ]
```

### Reducer Functions

- **`lambda x, y: y`**: Last value wins (for simple fields)
- **`add`**: List concatenation (for list fields)
- **`lambda existing, incoming: {**(existing or {}), **(incoming or {})}`**: Dictionary merging

### Testing

The fix is covered by `test_concurrent_updates.py` which tests:
- Concurrent field updates
- State model annotation validation
- Workflow initialization with proper state model
- Error handling during concurrent updates

## Node Architecture
