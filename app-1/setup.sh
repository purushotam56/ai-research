#!/bin/bash

# RAG Document Manager - Quick Start Script
# This script sets up and runs the application

set -e  # Exit on error

echo "🚀 RAG Document Manager - Quick Start"
echo "======================================"

# Check if Python 3 is installed
if ! command -v python &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✓ Python 3 found"

# Check if in correct directory
if [ ! -f "app.py" ]; then
    echo "❌ app.py not found. Please run this script from the app-1 directory."
    exit 1
fi

# Step 1: Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    python -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Step 2: Activate virtual environment
echo ""
echo "🔌 Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"

# Step 3: Upgrade pip
echo ""
echo "📦 Upgrading pip..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
echo "✓ pip upgraded"

# Step 4: Install dependencies
echo ""
echo "📦 Installing dependencies..."
echo "   This may take a few minutes on first run..."
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Step 5: Initialize database
echo ""
echo "💾 Initializing database..."
python << 'EOF'
from app import app, db

with app.app_context():
    db.create_all()
    print("✓ Database initialized successfully")
EOF

# Step 6: Display startup info
echo ""
echo "======================================"
echo "✅ Setup completed successfully!"
echo ""
echo "🎯 Next steps:"
echo ""
echo "1. Start the application:"
echo "   python app.py"
echo ""
echo "2. Open in browser:"
echo "   - Gradio UI: http://127.0.0.1:7860"
echo "   - Flask API: http://127.0.0.1:5000"
echo ""
echo "3. Register a new user and start adding documents!"
echo ""
echo "======================================"
