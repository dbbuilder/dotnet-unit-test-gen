#!/bin/bash
# Setup script for .NET Unit Test Generator

set -e

echo "🚀 Setting up .NET Unit Test Generator..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Found Python $PYTHON_VERSION"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Copy .env.template to .env:"
echo "     cp .env.template .env"
echo ""
echo "  2. Edit .env and add your OPENAI_API_KEY"
echo ""
echo "  3. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  4. Run the generator:"
echo "     python generate_tests.py /path/to/your/project --dry-run"
echo ""
