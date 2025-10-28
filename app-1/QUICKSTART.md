# 🚀 QUICK START - 5 MINUTES TO RUNNING

## The Absolute Fastest Way to Get Started

### Copy & Paste These Commands (One at a Time)

```bash
# 1. Go to the app directory
cd /Users/pc/dev/techbubble/ai-bot/app-1

# 2. Run the automated setup (this does everything)
chmod +x setup.sh
./setup.sh

# 3. When setup completes, start the app
python3 app.py
```

**That's it! ✓**

The app will be ready at:
- **Web Interface**: http://127.0.0.1:7860
- **API**: http://127.0.0.1:5000

---

## What to Do Next

### 1. Open the Web Interface
Go to: http://127.0.0.1:7860

### 2. Register
In the **🔐 Authentication** tab:
- Choose a username
- Enter email
- Create password
- Click "Register"

### 3. Login
- Enter username and password
- Click "Login"
- **Copy the User ID** shown in the result

### 4. Add Your First Document

#### Option A: From a URL
1. Go to **📤 Add Data** tab
2. Paste your User ID
3. Enter a URL (e.g., https://example.com)
4. Click "Scrape & Add"
5. Wait for completion ✓

#### Option B: Upload a File
1. Go to **📤 Add Data** tab
2. Paste your User ID
3. Upload a PDF, TXT, or Markdown file
4. Click "Upload & Process"
5. Wait for completion ✓

### 5. Search Your Documents
1. Go to **🔍 Search** tab
2. Paste your User ID
3. Enter a search query
4. Click "Search"
5. See semantic results!

---

## If Something Goes Wrong

### Virtual Environment Issues
```bash
# Activate it manually
source venv/bin/activate

# Run app
python3 app.py
```

### Port Already in Use
```bash
# Kill the process on port 7860
lsof -ti:7860 | xargs kill -9

# Then run app again
python3 app.py
```

### Start Completely Fresh
```bash
# From app-1 directory
rm -rf venv app.db vector_db uploads
./setup.sh
python3 app.py
```

### Missing Packages
```bash
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

---

## Test with API (Optional)

```bash
# Register
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","email":"demo@test.com","password":"demo123"}'

# Login
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo123"}'

# Search (use user_id from login response)
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"your search","user_id":1}'
```

---

## Key Files to Know About

| File | Purpose |
|------|---------|
| `app.py` | Main application - runs everything |
| `database.py` | User & document storage |
| `processor.py` | URL scraping & file extraction |
| `vector_store.py` | Semantic search engine |
| `auth.py` | Login/registration |
| `README.md` | Full documentation |
| `COMMANDS.md` | All commands reference |
| `ARCHITECTURE.md` | Technical deep dive |

---

## Features You Have Now

✅ User registration & login  
✅ URL scraping (automatic content extraction)  
✅ File upload (PDF, TXT, Markdown)  
✅ Vector database (ChromaDB)  
✅ Semantic search across documents  
✅ REST API endpoints  
✅ Interactive Gradio interface  

---

## Next Phase (Not Implemented Yet)

- RAG queries using LLM (GPT-3.5, Claude, etc.)
- Chat interface
- Document collaboration
- Advanced analytics

---

## 🆘 Need Help?

1. Check `README.md` for detailed docs
2. Check `COMMANDS.md` for all commands
3. Check `ARCHITECTURE.md` for technical details
4. Check error messages in terminal
5. Make sure virtual environment is activated

---

## ⚡ One-Command Summary

```bash
cd /Users/pc/dev/techbubble/ai-bot/app-1 && chmod +x setup.sh && ./setup.sh && python3 app.py
```

Then open: http://127.0.0.1:7860

**Enjoy! 🎉**
