#!/bin/bash
# Auto-fix code quality issues

set -e

echo "🔧 Auto-fixing code quality issues..."
echo ""

# Format code
echo "🎨 Formatting with black..."
uv run black backend/
echo ""

# Auto-fix linting issues
echo "🔍 Fixing linting issues with ruff..."
uv run ruff check --fix backend/
echo ""

echo "✅ Auto-fixes complete! Run ./check.sh to verify."
