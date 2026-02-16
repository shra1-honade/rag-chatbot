#!/bin/bash
# Run ruff linter on all Python code

set -e

echo "🔍 Running ruff linter..."
uv run ruff check backend/

echo "✅ Linting complete!"
