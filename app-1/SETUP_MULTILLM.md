# Setup Instructions for Multi-Provider LLM Support

Your app now supports **flexible LLM provider configuration** to use either **OpenAI**, **IBM Watson**, or fallback mode without any LLM.

## TL;DR - Quick Setup

### To use IBM Watson (your preference):

```bash
# 1. Install IBM packages
bash install_ibm_watson.sh

# 2. Copy .env.example to .env
cp .env.example .env

# 3. Edit .env and add your IBM credentials
# LLM_PROVIDER=ibm
# IBM_API_KEY=your-api-key-here
# IBM_PROJECT_ID=your-project-id-here

# 4. Run the app
python app_new.py
```

### To use OpenAI:

```bash
# 1. Update requirements.txt (already done)
# 2. Copy .env and add OpenAI key
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-your-key-here

# 3. Run the app
python app_new.py
```

## What Changed

### ✨ New Features

1. **Multi-Provider Support**
   - OpenAI (GPT-3.5 Turbo)
   - IBM Watson (Granite 3.3 8B)
   - Automatic fallback mode

2. **Environment-Based Configuration**
   - Set `LLM_PROVIDER` to choose provider
   - Auto-detect mode if not specified
   - All credentials from environment variables

3. **Graceful Degradation**
   - App works without LLM configured
   - Returns document context as fallback
   - No hard errors if API keys missing

### 📝 Files Updated

- **llm.py** - Complete rewrite with provider abstraction
- **requirements.txt** - Added IBM Watson packages
- **.env.example** - Comprehensive configuration examples
- **LLM_SETUP.md** - Detailed setup guide (see this file)

### 🔧 No Changes Needed To

- `app_new.py` - Automatically uses new flexible `llm.py`
- `database.py`, `auth.py`, `processor.py`, `vector_store.py` - Unchanged
- `templates/index.html` - Unchanged

## Installation Steps

### Step 1: Install Base Requirements

```bash
pip install -r requirements.txt
```

This installs OpenAI dependencies by default.

### Step 2: Install IBM Watson (Optional, if using IBM provider)

**Option A - Using the provided script:**
```bash
bash install_ibm_watson.sh
```

**Option B - Manual installation:**
```bash
pip install ibm-watsonx-ai>=0.1.0
pip install langchain-ibm>=0.1.0
```

### Step 3: Configure Environment

```bash
# Copy the example to .env
cp .env.example .env

# Edit with your credentials (use nano, vim, VS Code, etc.)
nano .env
```

### Step 4: Set Your LLM Provider

In your `.env` file, choose one:

#### Option A: Use IBM Watson
```bash
# Uncomment and fill in your IBM credentials
LLM_PROVIDER=ibm
IBM_API_KEY=<paste-your-ibm-api-key>
IBM_PROJECT_ID=<paste-your-ibm-project-id>
IBM_URL=https://api.us-south.ml.cloud.ibm.com  # Change region if needed
IBM_MODEL=ibm/granite-3-3-8b-instruct

# Optional: comment out or remove OpenAI key
# OPENAI_API_KEY=...
```

#### Option B: Use OpenAI
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-<paste-your-openai-api-key>
OPENAI_MODEL=gpt-3.5-turbo

# Optional: comment out IBM credentials
# IBM_API_KEY=...
```

#### Option C: Auto-Detect (Use whichever credentials you have)
```bash
# Leave LLM_PROVIDER unset or blank
# App will use IBM if both IBM credentials are set, otherwise OpenAI

# Your credentials here
IBM_API_KEY=<your-ibm-key>
IBM_PROJECT_ID=<your-project-id>
# OR
# OPENAI_API_KEY=sk-<your-openai-key>
```

### Step 5: Verify Configuration

Start the app and check the logs:

```bash
python app_new.py
```

Look for one of these messages:
```
[LLM] ✓ IBM Watson configured (model: ibm/granite-3-3-8b-instruct)
[LLM] ✓ OpenAI initialized (model: gpt-3.5-turbo)
[LLM] No LLM credentials found - running in fallback mode
```

## Architecture

### New RAGChatBot Class

```python
# Flexible provider support
chatbot = create_chatbot(vector_store=vector_store)  # Auto-detects provider

# Or explicit provider
chatbot = create_chatbot(
    vector_store=vector_store,
    llm_provider='ibm',
    model='ibm/granite-3-3-8b-instruct',
    temperature=0.5
)

# Generate answers
response = chatbot.generate_answer(
    question="What is...",
    documents=["Doc 1", "Doc 2"],
    user_id="user123"
)

# Response includes provider info
print(response['provider'])  # 'ibm', 'openai', or 'fallback'
```

### Response Format

All responses from `/api/chat` endpoint now include provider info:

```json
{
  "answer": "The answer based on documents...",
  "sources": ["Document 1", "Document 2"],
  "has_context": true,
  "status": "success",  // 'success', 'fallback', or 'error'
  "provider": "ibm"     // 'ibm', 'openai', or 'fallback'
}
```

## Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'langchain_ibm'"

**Solution:** Install IBM Watson packages
```bash
bash install_ibm_watson.sh
# OR
pip install ibm-watsonx-ai langchain-ibm
```

### Problem: "[LLM] No LLM credentials found - running in fallback mode"

**Solution:** Add credentials to `.env`:
```bash
# For IBM
IBM_API_KEY=your-key-here
IBM_PROJECT_ID=your-project-here

# OR for OpenAI
OPENAI_API_KEY=sk-your-key-here
```

### Problem: IBM Watson authentication failed

**Solution:** Check credentials and URL:
1. Verify `IBM_API_KEY` - Get from IBM Cloud console
2. Verify `IBM_PROJECT_ID` - From WatsonX project settings
3. Verify `IBM_URL` for your region:
   - US South: `https://api.us-south.ml.cloud.ibm.com`
   - US East: `https://api.us-east.ml.cloud.ibm.com`
   - EU GB: `https://api.eu-gb.ml.cloud.ibm.com`

### Problem: OpenAI API returns 401 Unauthorized

**Solution:** Check your OpenAI key:
1. Get new key from https://platform.openai.com/api-keys
2. Verify it starts with `sk-`
3. Check account balance and quotas

### Problem: Chat endpoint returns empty answers

**Solution:** 
1. Check if documents were uploaded and indexed
2. Try `/api/search` to verify vector search works
3. Check if LLM provider is properly configured (see startup logs)
4. Try adding debug logging to requests

## Configuration Priority

When the app starts, provider selection works like this:

```
1. If LLM_PROVIDER explicitly set in .env
   ├─ Use 'ibm' if set to IBM
   ├─ Use 'openai' if set to OpenAI
   └─ Use 'openai' (default) if set to anything else

2. Else if LLM_PROVIDER not set (auto-detect mode)
   ├─ If IBM credentials exist → Use IBM Watson
   ├─ Else if OpenAI API key exists → Use OpenAI
   └─ Else → Fallback mode
```

## Commands

### Run the app
```bash
python app_new.py
```

### Install all dependencies
```bash
pip install -r requirements.txt
```

### Install IBM Watson support
```bash
bash install_ibm_watson.sh
```

### Copy and edit environment config
```bash
cp .env.example .env
nano .env  # or vim .env or open in VS Code
```

### View startup logs
```bash
python app_new.py 2>&1 | grep -i llm
```

## Migration Guide (if you have existing code)

### Old Usage (OpenAI-only)
```python
from llm import create_chatbot
chatbot = create_chatbot(vector_store)
answer = chatbot.generate_answer(question, documents, user_id)
```

### New Usage (Works same, but with provider support)
```python
from llm import create_chatbot
chatbot = create_chatbot(vector_store)  # Auto-detects provider
answer = chatbot.generate_answer(question, documents, user_id)
# Response now includes 'provider' field
```

**No code changes needed!** The API is backward compatible.

## Advanced: Manual Provider Specification

```python
from llm import create_chatbot

# Explicitly use IBM Watson
chatbot = create_chatbot(
    vector_store=my_vector_store,
    llm_provider='ibm',
    model='ibm/granite-3-3-8b-instruct',
    temperature=0.5
)

# Explicitly use OpenAI
chatbot = create_chatbot(
    vector_store=my_vector_store,
    llm_provider='openai',
    model='gpt-3.5-turbo',
    temperature=0.7
)
```

## Performance Comparison

| Provider | Speed | Cost | Quality | Setup |
|----------|-------|------|---------|-------|
| OpenAI | 1-3s | $$ (pay per token) | Excellent | Easy |
| IBM Watson | 2-5s | $ (free tier available) | Good | Medium |
| Fallback | Instant | Free | Context only | Automatic |

## Next Steps

1. **Complete Setup:** Follow the TL;DR section above
2. **Test Chat:** Visit http://localhost:5000 and use the Chat tab
3. **Upload Docs:** Add some documents to test RAG
4. **Ask Questions:** Ask about your documents in the chat
5. **Monitor Logs:** Watch console output for LLM processing

## Support

For detailed provider-specific setup, see:
- `LLM_SETUP.md` - Comprehensive LLM configuration guide
- `.env.example` - All available environment variables
- Comments in `llm.py` - Code-level documentation

## Key Variables Reference

```bash
# LLM Provider Selection
LLM_PROVIDER=ibm              # Force IBM
LLM_PROVIDER=openai           # Force OpenAI
# (Leave blank for auto-detect)

# IBM Watson
IBM_API_KEY=...              # Required
IBM_PROJECT_ID=...           # Required
IBM_URL=...                  # Optional (defaults to us-south)
IBM_MODEL=...                # Optional
IBM_TEMPERATURE=0.5          # Optional

# OpenAI
OPENAI_API_KEY=...           # Required
OPENAI_MODEL=...             # Optional
OPENAI_TEMPERATURE=0.7       # Optional

# Flask & Database
FLASK_ENV=development
DATABASE_URL=sqlite:///app.db
VECTOR_DB_PATH=./vector_db
```
