# Course Materials RAG System

A Retrieval-Augmented Generation (RAG) system designed to answer questions about course materials using semantic search and AI-powered responses.

## Overview

This application is a full-stack web application that enables users to query course materials and receive intelligent, context-aware responses. It uses ChromaDB for vector storage, Anthropic's Claude for AI generation, and provides a web interface for interaction.


## Architecture

```mermaid
graph TB
    subgraph FRONTEND["Frontend (Static HTML/CSS/JS)"]
        UI["Chat Interface<br/><i>index.html + style.css + script.js</i>"]
    end

    subgraph SERVER["FastAPI Server — app.py (port 8000)"]
        API_Q["POST /api/query"]
        API_C["GET /api/courses"]
        STATIC["/ → static files"]
    end

    subgraph BACKEND["Backend Components"]
        RAG["RAGSystem<br/><i>rag_system.py</i>"]
        DP["DocumentProcessor<br/><i>document_processor.py</i>"]
        VS["VectorStore<br/><i>vector_store.py</i>"]
        AI["AIGenerator<br/><i>ai_generator.py</i>"]
        SM["SessionManager<br/><i>session_manager.py</i>"]
        TM["ToolManager + CourseSearchTool<br/><i>search_tools.py</i>"]
    end

    subgraph EXTERNAL["External Services & Storage"]
        CLAUDE["Claude API<br/><i>claude-sonnet-4-20250514</i>"]
        CHROMA[("ChromaDB<br/><i>course_catalog<br/>course_content</i>")]
        DOCS["docs/<br/><i>course1-4_script.txt</i>"]
    end

    UI -- "HTTP requests" --> API_Q
    UI -- "HTTP requests" --> API_C
    API_Q --> RAG
    API_C --> RAG
    STATIC -. "serves" .-> UI

    RAG --> DP
    RAG --> VS
    RAG --> AI
    RAG --> SM
    RAG --> TM

    AI -- "API calls" --> CLAUDE
    VS -- "read/write" --> CHROMA
    DP -- "reads" --> DOCS
    TM -- "delegates search" --> VS
```

For detailed query flow and document ingestion diagrams, see [Architecture Diagram](https://htmlpreview.github.io/?https://github.com/webdevonshra1/starting-ragchatbot-codebase/blob/main/architecture-diagram.html).

## Prerequisites

- Python 3.13 or higher
- uv (Python package manager)
- An Anthropic API key (for Claude AI)
- **For Windows**: Use Git Bash to run the application commands - [Download Git for Windows](https://git-scm.com/downloads/win)

## Installation

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Python dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

## Running the Application

### Quick Start

Use the provided shell script:
```bash
chmod +x run.sh
./run.sh
```

### Manual Start

```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

The application will be available at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

