# 🚀 ChatBot with RAG - Setup Instructions

## What's New

Added a **💬 Chat Tab** with RAG (Retrieval-Augmented Generation):

✅ Ask questions about your documents  
✅ Get answers from document content  
✅ Uses OpenAI GPT-3.5 Turbo (or fallback to document search)  
✅ Shows relevant sources  
✅ Chat history support  

## Setup

### 1. Install OpenAI Package
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Optional: Setup OpenAI API Key

For AI-powered answers, get an API key from [platform.openai.com](https://platform.openai.com):

Create `.env` file in `app-1/`:
```bash
cp .env.example .env
```

Edit `.env` and add your key:
```
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-3.5-turbo
```

Or set environment variable:
```bash
export OPENAI_API_KEY=sk-your-key-here
```

### 3. Run App
```bash
mv app.py app_old.py
mv app_new.py app.py
python3 app.py
```

### 4. Use ChatBot

1. Go to **http://127.0.0.1:5000**
2. Login/Register
3. Add documents (URLs or files)
4. Go to **💬 Chat** tab
5. Enter User ID
6. Choose "Use LLM" option:
   - **Yes** = AI-powered answers (requires API key)
   - **No** = Show relevant document excerpts
7. Ask questions!

## How It Works

```
Your Question
    ↓
Search Vector DB (find relevant documents)
    ↓
Send with context to LLM
    ↓
LLM generates answer based on your documents
    ↓
Display answer + sources
```

## Without API Key

If you don't have an OpenAI API key:
- Select **"No - Just show document excerpts"**
- System will find and show relevant document sections
- Still useful for searching!

## API Key Cost

- ~$0.001 per question (GPT-3.5 Turbo)
- ~100 questions = $0.10

Check usage: [https://platform.openai.com/account/usage](https://platform.openai.com/account/usage)

## Features

### Chat Features
- 💬 Multi-turn conversation
- 📚 Document-based answers
- 🔗 Source attribution
- ⌨️ Enter to send, Shift+Enter for new line
- 🤖 AI-powered with OpenAI
- 🎯 Fallback to document search

### Commands

```bash
# Setup
pip install -r requirements.txt

# Run
python3 app.py

# Access
http://127.0.0.1:5000

# Chat API endpoint
POST /api/chat
{
    "user_id": 1,
    "question": "What is X?",
    "use_llm": true,
    "chat_history": []
}
```

## Troubleshooting

### "LLM not available"
- OPENAI_API_KEY not set
- Solution: Add key to .env or environment

### "No matching documents"
- Question doesn't match any documents
- Solution: Add more documents first

### High costs?
- Too many API calls
- Solution: Use "No LLM" option for testing

## Next Steps

- Add more LLM providers (Claude, Cohere, etc.)
- Add file upload for prompt templates
- Add conversation export
- Add rate limiting
- Add analytics

---

**Ready? Start here:**
```bash
cd /Users/pc/dev/techbubble/ai-bot/app-1
python3 app.py
# Open: http://127.0.0.1:5000
```
