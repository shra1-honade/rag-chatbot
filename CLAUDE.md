# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A full-stack RAG (Retrieval-Augmented Generation) chatbot that lets users query course materials using semantic search and Claude AI. Built with FastAPI + vanilla JS frontend + ChromaDB vector store.

## Development Commands

```bash
# Install dependencies (requires uv package manager)
uv sync --extra dev --extra test

# Run the dev server (FastAPI with hot reload on port 8000)
./run.sh
# or directly:
cd backend && uv run uvicorn app:app --reload --port 8000

# Code quality tools
./format.sh        # Format code with black
./lint.sh          # Run ruff linter
./fix.sh           # Auto-format and fix linting issues
./check.sh         # Run all checks (format check, lint, tests)

# Run tests
cd backend && uv run pytest
```

## Code Quality

The project uses:
- **black** for code formatting (line length: 100)
- **ruff** for fast linting (includes import sorting, pyflakes, bugbear, etc.)
- **pytest** for testing

All code is automatically formatted and linted. Run `./check.sh` before committing to ensure all checks pass.

## Environment Setup

Requires a `.env` file (see `.env.example`) with `ANTHROPIC_API_KEY`. Python 3.13+.

## Architecture

### RAG Pipeline

This is a **tool-based RAG system** — Claude decides when to search rather than automatically retrieving on every query. The flow:

1. **Ingestion** (`document_processor.py` → `vector_store.py`): On server startup, course files from `docs/` are parsed (expecting specific format: title/link/instructor header lines, then "Lesson N:" markers), chunked at sentence boundaries (800 chars, 100 overlap), and embedded into ChromaDB.

2. **Query** (`app.py` → `rag_system.py` → `ai_generator.py`): User queries go through the session manager for conversation history, then to Claude with available tools. Claude chooses whether to call `search_course_content`.

3. **Tool execution** (`search_tools.py` → `vector_store.py`): When Claude calls the search tool, it performs vector similarity search in ChromaDB with optional course/lesson filters. Results are sent back to Claude for final answer synthesis.

### Key Components

- **`rag_system.py`** — Main orchestrator; ties together document ingestion, session management, and query pipeline
- **`vector_store.py`** — Manages two ChromaDB collections: `course_catalog` (metadata) and `course_content` (text chunks). Uses `all-MiniLM-L6-v2` embeddings. Has fuzzy course name resolution via vector search.
- **`ai_generator.py`** — Claude API wrapper using Anthropic tool calling. Multi-turn: initial request → tool execution → follow-up with results → final response. Temperature 0, max 800 tokens.
- **`search_tools.py`** — Abstract `Tool` base class + `CourseSearchTool` implementation + `ToolManager` registry. Tool schema uses Anthropic's tool calling format.
- **`session_manager.py`** — In-memory session tracking with auto-incrementing IDs. History capped at 2 messages.
- **`config.py`** — Centralized settings dataclass (model names, chunk sizes, collection names, etc.)

### Frontend

Vanilla JS/HTML/CSS in `frontend/`. The FastAPI app serves static files from this directory. Uses `marked.js` for markdown rendering. Communicates via `POST /api/query` and `GET /api/courses`.

### API Endpoints

- `POST /api/query` — Process user query through RAG pipeline (body: `{message, session_id?}`)
- `GET /api/courses` — Course catalog statistics
- `GET /` — Serves frontend

### Course Document Format

Files in `docs/` must follow this structure:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [name]

Lesson 1: [title]
[content...]

Lesson 2: [title]
[content...]
```

## Important Design Decisions

- Sessions are in-memory only (lost on server restart)
- ChromaDB persists to `backend/chroma_db/` on disk
- Document deduplication: existing course titles are checked before re-ingestion on startup
- The Claude model used is `claude-sonnet-4-20250514` (configured in `config.py`)
