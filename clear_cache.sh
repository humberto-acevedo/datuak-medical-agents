#!/bin/bash
# Clear Python cache files that might cause import issues

echo "🧹 Clearing Python cache files..."

# Remove __pycache__ directories
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
echo "✅ Removed __pycache__ directories"

# Remove .pyc files
find . -name "*.pyc" -delete 2>/dev/null
echo "✅ Removed .pyc files"

# Remove .pyo files
find . -name "*.pyo" -delete 2>/dev/null
echo "✅ Removed .pyo files"

echo ""
echo "🎉 Cache cleared successfully!"
echo ""
echo "Now try running:"
echo "  python launch_prototype.py --help"
echo "  python launch_prototype.py --bedrock"
