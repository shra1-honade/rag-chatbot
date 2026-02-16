#!/bin/bash
# Format all Python code with black

set -e

echo "🎨 Formatting code with black..."
uv run black backend/

echo "✅ Code formatting complete!"
