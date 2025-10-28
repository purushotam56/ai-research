# Commands Guide - RAG Document Manager

Copy and run these commands in your terminal. Navigate to the `app-1` directory first.

## 1️⃣ Initial Setup

### Option A: Automated Setup (Recommended)
```bash
cd /Users/pc/dev/techbubble/ai-bot/app-1

# Make setup scripts executable
chmod +x setup.sh test_setup.sh

# Run automatic setup
./setup.sh
```

### Option B: Manual Setup
```bash
cd /Users/pc/dev/techbubble/ai-bot/app-1

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Initialize database
python3 -c "from app import app, db; app.app_context().push(); db.create_all(); print('✓ Database initialized')"
```

## 2️⃣ Verify Installation

```bash
# Test if everything is installed correctly
./test_setup.sh

# Or manually test
python3 << 'EOF'
import flask
import gradio
import chromadb
import bs4
print("✓ All packages imported successfully!")
EOF
```

## 3️⃣ Run the Application

```bash
# Make sure virtual environment is active
source venv/bin/activate

# Start the app
python3 app.py
```

The app will start at:
- **Gradio UI**: http://127.0.0.1:7860
- **Flask API**: http://127.0.0.1:5000

## 4️⃣ API Testing (in another terminal)

### Register a User
```bash
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

### Login
```bash
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123"
  }'
```

### Get User Info
```bash
curl http://localhost:5000/api/user/1
```

### Get User Documents
```bash
curl http://localhost:5000/api/documents/1
```

### Search Documents
```bash
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "your search query",
    "user_id": 1,
    "num_results": 5
  }'
```

## 5️⃣ Database Management

### Reset Everything (Start Fresh)
```bash
# Deactivate and remove virtual environment
deactivate
rm -rf venv/

# Remove databases
rm -rf app.db vector_db/

# Start fresh setup
./setup.sh
```

### Just Reset SQLite Database
```bash
rm app.db
python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### Just Reset Vector Database
```bash
rm -rf vector_db/
```

### View Database (SQLite)
```bash
# Install sqlite3 CLI if needed (usually pre-installed)
sqlite3 app.db

# Inside sqlite3:
# .tables                    (list all tables)
# SELECT * FROM users;      (view users)
# SELECT * FROM documents;  (view documents)
# .quit                      (exit)
```

## 6️⃣ Troubleshooting Commands

### Check Python Version
```bash
python3 --version
```

### Verify Pip Packages
```bash
pip list | grep -E "Flask|Gradio|chromadb|beautifulsoup|sentence"
```

### Check Virtual Environment
```bash
which python3
# Should show path with 'venv' in it
```

### Test Vector Store
```bash
python3 << 'EOF'
from vector_store import VectorStore
vs = VectorStore()
print("✓ Vector store initialized")
print(f"✓ Collection: {vs.collection.name}")
EOF
```

### Test Database
```bash
python3 << 'EOF'
from app import app, db
from database import User

with app.app_context():
    users = User.query.all()
    print(f"✓ Database connected")
    print(f"✓ Total users: {len(users)}")
EOF
```

## 7️⃣ Development/Debugging

### Run with Debug Output
```bash
# Edit app.py, change last lines to:
# if __name__ == '__main__':
#     app.run(debug=True, port=5000)
#     gradio_interface.launch(debug=True)
```

### Check Logs During Runtime
```bash
# Terminal 1: Run app
python3 app.py

# Terminal 2: Watch logs
tail -f output.log  # if you redirect output to a file
```

### Import and Test Modules Directly
```bash
python3 << 'EOF'
# Test auth module
from auth import register_user, login_user
result = register_user("testuser", "test@example.com", "password123")
print(result)

# Test processor
from processor import is_valid_url, scrape_url
print(is_valid_url("https://example.com"))

# Test vector store
from vector_store import VectorStore
vs = VectorStore()
result = vs.add_document(1, 1, "Test", "This is test content")
print(result)
EOF
```

## 8️⃣ Production Considerations

### Create .env File (copy from .env.example)
```bash
cp .env.example .env
# Edit .env with your production settings
```

### Use Production WSGI Server
```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Use PostgreSQL Instead of SQLite
```bash
# Install PostgreSQL driver
pip install psycopg2-binary

# Update database URL in app.py:
# SQLALCHEMY_DATABASE_URI = 'postgresql://user:password@localhost/dbname'
```

## 9️⃣ File Structure After Setup

```bash
ls -la
# You should see:
# app.py               (main application)
# database.py          (database models)
# auth.py              (authentication)
# processor.py         (file/URL processing)
# vector_store.py      (vector database)
# requirements.txt     (dependencies)
# README.md            (documentation)
# setup.sh             (automated setup)
# test_setup.sh        (test script)
# .env.example         (environment variables)
# venv/                (virtual environment)
# app.db               (SQLite database - created after first run)
# vector_db/           (ChromaDB storage - created after first run)
# uploads/             (temporary file storage)
```

## 🔟 Quick Reference

| Task | Command |
|------|---------|
| Setup | `./setup.sh` |
| Test Setup | `./test_setup.sh` |
| Start App | `source venv/bin/activate && python3 app.py` |
| Reset All | `rm -rf venv/ app.db vector_db/` |
| Test Auth | `curl -X POST http://localhost:5000/api/login -H "Content-Type: application/json" -d '{"username":"test","password":"pass"}'` |
| View Database | `sqlite3 app.db ".tables"` |
| Stop App | `Ctrl+C` in terminal |
| Deactivate Env | `deactivate` |

## ❓ Frequently Used Development Commands

```bash
# Activate environment (always first step)
source venv/bin/activate

# Install new package
pip install package_name

# Freeze current dependencies (backup)
pip freeze > requirements_backup.txt

# Run specific Python file
python3 filename.py

# Interactive Python shell
python3

# Check disk usage
du -sh *
du -sh vector_db/
du -sh app.db

# Remove temporary files
rm -rf __pycache__
rm -rf .pytest_cache

# Monitor running processes
ps aux | grep python3
```

---

**📌 Important**: Always activate the virtual environment (`source venv/bin/activate`) before running any commands!
