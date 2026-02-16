#!/bin/bash
# Run all code quality checks

set -e

echo "🚀 Running code quality checks..."
echo ""

# Format check (don't modify files)
echo "📋 Checking code formatting..."
uv run black --check backend/
echo ""

# Lint
echo "🔍 Running linter..."
uv run ruff check backend/
echo ""

# Tests
echo "🧪 Running tests..."
cd backend && uv run pytest
cd ..
echo ""

echo "✅ All checks passed!"
