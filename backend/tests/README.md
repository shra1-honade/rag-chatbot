# RAG System Testing Framework

## Overview

Comprehensive testing framework for the RAG chatbot with **28 tests** covering:
- **13 unit tests** for AI generator sequential tool calling
- **15 API tests** for FastAPI endpoints

## Running Tests

### Install dependencies
```bash
uv sync --extra test
```

### Run all tests
```bash
uv run pytest
```

### Run with verbose output
```bash
uv run pytest -v
```

### Run specific test categories
```bash
# Unit tests only
uv run pytest -m unit

# API tests only
uv run pytest -m api
```

### Run specific test file
```bash
uv run pytest backend/tests/test_ai_generator.py
uv run pytest backend/tests/test_api.py
```

### Run specific test
```bash
uv run pytest backend/tests/test_api.py::TestQueryEndpoint::test_query_with_session_id
```

## Test Structure

### `conftest.py` - Shared Fixtures
- `mock_config` - Mock configuration with test settings
- `mock_rag_system` - Mock RAG system with predefined responses
- `sample_query_request` - Sample API request data
- `ai_generator_mock` - Mock AI generator for unit tests
- `tool_manager_mock` - Mock tool manager
- `sample_tools` - Sample tool definitions

### `test_ai_generator.py` - Unit Tests
Tests for the AIGenerator component covering:
- Direct text responses
- Single-round tool calling
- Two-round sequential tool calling
- Error handling
- Conversation history
- Mixed content blocks

### `test_api.py` - API Endpoint Tests
Tests for FastAPI endpoints covering:
- `POST /api/query` - Query processing with/without sessions
- `GET /api/courses` - Course catalog statistics
- `GET /` - Root endpoint
- CORS headers
- Request validation
- Error handling

## Key Design Decisions

### Test App Factory
The API tests use a `create_test_app()` factory instead of importing the production app directly. This avoids issues with the production app mounting static files at import time, which would fail in the test environment.

### Mocking Strategy
- RAGSystem is mocked at the fixture level for consistent test data
- Tests verify correct method calls rather than actual RAG functionality
- Separation between unit tests (components) and API tests (endpoints)

### Pytest Configuration
Defined in `pyproject.toml`:
- Test discovery: `backend/tests/test_*.py`
- Markers: `unit`, `api`, `integration`
- Verbose output and shorter tracebacks by default

## Test Coverage

### Query Endpoint (`POST /api/query`)
✓ Query with existing session ID
✓ Query without session (creates new session)
✓ Query with multiple sources
✓ Missing required fields (validation)
✓ Empty query string
✓ RAG system exceptions
✓ Session manager exceptions
✓ Extra fields in request
✓ Invalid JSON
✓ Null session_id

### Courses Endpoint (`GET /api/courses`)
✓ Successful course listing
✓ Empty course catalog
✓ Vector store exceptions

### AI Generator (Unit Tests)
✓ Direct text responses (no tools)
✓ Single tool call then text
✓ Two sequential tool calls
✓ Tool result message accumulation
✓ Tool execution errors
✓ Conversation history handling
✓ Mixed content block extraction

## Adding New Tests

1. Add shared fixtures to `conftest.py`
2. Create new test file: `test_<component>.py`
3. Add appropriate marker: `pytestmark = pytest.mark.<marker>`
4. Use existing fixtures or create new ones
5. Follow naming convention: `test_<description>`

## Continuous Integration

To integrate with CI/CD:
```yaml
- name: Run tests
  run: |
    uv sync --extra test
    uv run pytest -v --tb=short
```
