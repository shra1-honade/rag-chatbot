"""Shared pytest fixtures for testing the RAG system"""
import sys
from pathlib import Path

# Add parent directory to path so tests can import backend modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from unittest.mock import MagicMock, patch
import tempfile


@pytest.fixture
def mock_config():
    """Mock configuration object"""
    config = MagicMock()
    config.ANTHROPIC_API_KEY = "test-api-key"
    config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_RESULTS = 5
    config.MAX_HISTORY = 2

    # Use a temporary directory for test database
    with tempfile.TemporaryDirectory() as tmpdir:
        config.CHROMA_PATH = str(Path(tmpdir) / "test_chroma_db")
        yield config


@pytest.fixture
def mock_rag_system():
    """Mock RAGSystem with commonly used methods"""
    rag = MagicMock()

    # Mock session_manager
    rag.session_manager.create_session.return_value = "test-session-123"
    rag.session_manager.get_conversation_history.return_value = None

    # Mock query method to return response with sources
    rag.query.return_value = (
        "This is a test answer about the course content.",
        [
            {"title": "Introduction to Python - Lesson 1", "url": "https://example.com/python"},
            {"title": "Python Basics - Lesson 2", "url": "https://example.com/basics"}
        ]
    )

    # Mock course analytics
    rag.get_course_analytics.return_value = {
        "total_courses": 3,
        "course_titles": ["Python Course", "JavaScript Course", "Data Science Course"]
    }

    # Mock vector store methods
    rag.vector_store.get_course_count.return_value = 3
    rag.vector_store.get_existing_course_titles.return_value = [
        "Python Course",
        "JavaScript Course",
        "Data Science Course"
    ]

    return rag


@pytest.fixture
def sample_query_request():
    """Sample query request data"""
    return {
        "query": "What is Python?",
        "session_id": "test-session-123"
    }


@pytest.fixture
def sample_query_request_no_session():
    """Sample query request without session ID"""
    return {
        "query": "Explain variables in JavaScript"
    }


@pytest.fixture
def sample_sources():
    """Sample source citations"""
    return [
        {"title": "Python Fundamentals - Lesson 1", "url": "https://example.com/python/lesson1"},
        {"title": "Python Data Types - Lesson 2", "url": "https://example.com/python/lesson2"},
        {"title": "Python Functions - Lesson 3", "url": None}  # Source without URL
    ]


@pytest.fixture
def ai_generator_mock():
    """Mock AIGenerator for unit tests"""
    with patch("ai_generator.anthropic.Anthropic") as MockClient:
        from ai_generator import AIGenerator
        gen = AIGenerator(api_key="test-key", model="test-model")
        gen.client = MockClient()
        yield gen


@pytest.fixture
def tool_manager_mock():
    """Mock ToolManager for testing tool execution"""
    mgr = MagicMock()
    mgr.execute_tool = MagicMock(return_value="Mock tool result")
    mgr.get_tool_definitions.return_value = [
        {
            "name": "search_course_content",
            "description": "Search course materials",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                }
            }
        }
    ]
    mgr.get_last_sources.return_value = []
    mgr.reset_sources.return_value = None
    return mgr


@pytest.fixture
def sample_tools():
    """Sample tool definitions for Claude API"""
    return [
        {
            "name": "search_course_content",
            "description": "Search for information in course materials",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "course_title": {"type": "string", "description": "Optional course filter"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_course_outline",
            "description": "Get the outline of a specific course",
            "input_schema": {
                "type": "object",
                "properties": {
                    "course_title": {"type": "string", "description": "Course title"}
                },
                "required": ["course_title"]
            }
        }
    ]
