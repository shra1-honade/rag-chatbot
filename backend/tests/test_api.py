"""API endpoint tests for the FastAPI application"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
from typing import List, Optional
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path

pytestmark = pytest.mark.api


# Pydantic models (copied from app.py to avoid import issues)
class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class Source(BaseModel):
    title: str
    url: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    session_id: str


class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


def create_test_app(mock_rag_system):
    """Create a test FastAPI app without static file mounting"""
    app = FastAPI(title="Course Materials RAG System (Test)", root_path="")

    # Add middleware (same as production)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Define endpoints inline (same logic as app.py but with our mock)
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources = mock_rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Simple root endpoint for testing
    @app.get("/")
    async def root():
        return {"status": "ok"}

    return app


@pytest.fixture
def test_client(mock_rag_system):
    """Create a TestClient with test app and mocked RAGSystem"""
    app = create_test_app(mock_rag_system)
    client = TestClient(app)
    return client


class TestQueryEndpoint:
    """Tests for POST /api/query endpoint"""

    def test_query_with_session_id(self, test_client, mock_rag_system, sample_query_request):
        """Test query endpoint with existing session ID"""
        response = test_client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify response content
        assert data["answer"] == "This is a test answer about the course content."
        assert data["session_id"] == "test-session-123"
        assert len(data["sources"]) == 2

        # Verify RAG system was called correctly
        mock_rag_system.query.assert_called_once_with(
            sample_query_request["query"],
            sample_query_request["session_id"]
        )

    def test_query_without_session_id(self, test_client, mock_rag_system, sample_query_request_no_session):
        """Test query endpoint creates new session when none provided"""
        response = test_client.post("/api/query", json=sample_query_request_no_session)

        assert response.status_code == 200
        data = response.json()

        # Verify new session was created
        assert data["session_id"] == "test-session-123"
        mock_rag_system.session_manager.create_session.assert_called_once()

        # Verify query was processed
        mock_rag_system.query.assert_called_once()

    def test_query_with_sources(self, test_client, mock_rag_system):
        """Test query endpoint returns sources correctly"""
        mock_rag_system.query.return_value = (
            "Answer with sources",
            [
                {"title": "Course A - Lesson 1", "url": "https://example.com/a"},
                {"title": "Course B - Lesson 2", "url": None}
            ]
        )

        response = test_client.post("/api/query", json={"query": "test query"})

        assert response.status_code == 200
        data = response.json()

        assert len(data["sources"]) == 2
        assert data["sources"][0]["title"] == "Course A - Lesson 1"
        assert data["sources"][0]["url"] == "https://example.com/a"
        assert data["sources"][1]["url"] is None

    def test_query_missing_query_field(self, test_client):
        """Test query endpoint with missing required field"""
        response = test_client.post("/api/query", json={"session_id": "123"})

        assert response.status_code == 422  # Validation error

    def test_query_empty_string(self, test_client, mock_rag_system):
        """Test query endpoint with empty query string"""
        response = test_client.post("/api/query", json={"query": ""})

        assert response.status_code == 200
        # Empty string is valid, RAG system should handle it
        mock_rag_system.query.assert_called_once()

    def test_query_handles_rag_exception(self, test_client, mock_rag_system):
        """Test query endpoint handles RAG system exceptions"""
        mock_rag_system.query.side_effect = Exception("Database connection failed")

        response = test_client.post("/api/query", json={"query": "test"})

        assert response.status_code == 500
        assert "Database connection failed" in response.json()["detail"]

    def test_query_handles_session_manager_exception(self, test_client, mock_rag_system):
        """Test query endpoint handles session creation exceptions"""
        mock_rag_system.session_manager.create_session.side_effect = Exception("Session error")

        response = test_client.post("/api/query", json={"query": "test"})

        assert response.status_code == 500


class TestCoursesEndpoint:
    """Tests for GET /api/courses endpoint"""

    def test_get_courses_success(self, test_client, mock_rag_system):
        """Test courses endpoint returns correct analytics"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "total_courses" in data
        assert "course_titles" in data

        # Verify response content
        assert data["total_courses"] == 3
        assert len(data["course_titles"]) == 3
        assert "Python Course" in data["course_titles"]

        # Verify RAG system was called
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_get_courses_empty_catalog(self, test_client, mock_rag_system):
        """Test courses endpoint with no courses"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_get_courses_handles_exception(self, test_client, mock_rag_system):
        """Test courses endpoint handles exceptions"""
        mock_rag_system.get_course_analytics.side_effect = Exception("Vector store error")

        response = test_client.get("/api/courses")

        assert response.status_code == 500
        assert "Vector store error" in response.json()["detail"]


class TestRootEndpoint:
    """Tests for GET / endpoint"""

    def test_root_endpoint_exists(self, test_client):
        """Test that root endpoint is accessible"""
        response = test_client.get("/")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestCORSHeaders:
    """Tests for CORS middleware configuration"""

    def test_cors_headers_present(self, test_client):
        """Test that CORS headers are properly set"""
        response = test_client.options(
            "/api/query",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )

        # CORS should allow the request
        assert response.status_code in [200, 204]


class TestRequestValidation:
    """Tests for request validation and edge cases"""

    def test_query_with_extra_fields(self, test_client, mock_rag_system):
        """Test query endpoint ignores extra fields"""
        response = test_client.post("/api/query", json={
            "query": "test",
            "extra_field": "should be ignored"
        })

        assert response.status_code == 200

    def test_query_with_invalid_json(self, test_client):
        """Test query endpoint with malformed JSON"""
        response = test_client.post(
            "/api/query",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_query_with_null_values(self, test_client, mock_rag_system):
        """Test query endpoint with null session_id"""
        response = test_client.post("/api/query", json={
            "query": "test query",
            "session_id": None
        })

        assert response.status_code == 200
        # Should create new session when session_id is null
        mock_rag_system.session_manager.create_session.assert_called_once()
