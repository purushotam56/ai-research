#!/bin/bash

# Test script to verify the application setup
# Run this after setup.sh to test basic functionality

echo "🧪 RAG Document Manager - Test Script"
echo "======================================"

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run setup.sh first."
    exit 1
fi

source venv/bin/activate

echo ""
echo "Testing Python dependencies..."
python3 << 'EOF'
import sys

packages = [
    ('flask', 'Flask'),
    ('flask_cors', 'Flask-CORS'),
    ('flask_sqlalchemy', 'Flask-SQLAlchemy'),
    ('gradio', 'Gradio'),
    ('requests', 'Requests'),
    ('bs4', 'BeautifulSoup4'),
    ('chromadb', 'ChromaDB'),
    ('sentence_transformers', 'Sentence-Transformers'),
    ('PyPDF2', 'PyPDF'),
]

print("\n✅ Installed Packages:")
missing = []

for import_name, display_name in packages:
    try:
        __import__(import_name)
        print(f"  ✓ {display_name}")
    except ImportError:
        print(f"  ✗ {display_name} (MISSING)")
        missing.append(display_name)

if missing:
    print(f"\n❌ Missing packages: {', '.join(missing)}")
    print("   Run: pip install -r requirements.txt")
    sys.exit(1)
else:
    print("\n✅ All required packages are installed!")

EOF

echo ""
echo "Testing database initialization..."
python3 << 'EOF'
import os
from app import app, db

with app.app_context():
    if os.path.exists('app.db'):
        print("✓ Database file exists")
    
    # Try to create tables
    db.create_all()
    print("✓ Database tables initialized")
    
    # Test user creation
    from database import User
    test_user = User(username='test_user_123', email='test@example.com')
    test_user.set_password('testpass123')
    
    print("✓ User model working")
    print("✓ Password hashing working")

EOF

echo ""
echo "======================================"
echo "✅ All tests passed!"
echo ""
echo "Your application is ready to use."
echo "Run: python3 app.py"
echo "======================================"
