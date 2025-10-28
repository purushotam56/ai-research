#!/bin/bash
# Install script for IBM Watson optional dependencies

echo "=================================================="
echo "Installing IBM Watson LLM Provider Support"
echo "=================================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3 first."
    exit 1
fi

echo "📦 Python version:"
python3 --version
echo ""

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found. Please install pip first."
    exit 1
fi

echo "📦 Installing IBM Watson packages..."
echo ""

# Install IBM Watson packages
echo "Installing ibm-watsonx-ai..."
pip3 install "ibm-watsonx-ai>=0.1.0"

if [ $? -ne 0 ]; then
    echo "❌ Failed to install ibm-watsonx-ai"
    exit 1
fi

echo ""
echo "Installing langchain-ibm..."
pip3 install "langchain-ibm>=0.1.0"

if [ $? -ne 0 ]; then
    echo "❌ Failed to install langchain-ibm"
    exit 1
fi

echo ""
echo "✅ IBM Watson packages installed successfully!"
echo ""
echo "=================================================="
echo "Next Steps:"
echo "=================================================="
echo ""
echo "1. Update your .env file with IBM credentials:"
echo "   LLM_PROVIDER=ibm"
echo "   IBM_API_KEY=your-api-key"
echo "   IBM_PROJECT_ID=your-project-id"
echo ""
echo "2. Start the app:"
echo "   python3 app_new.py"
echo ""
echo "See LLM_SETUP.md for more details."
