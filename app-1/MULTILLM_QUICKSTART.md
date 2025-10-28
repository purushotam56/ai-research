# 🚀 Multi-Provider LLM Configuration - Ready to Use!

Your RAG chatbot now supports **flexible LLM providers**. Choose between OpenAI, IBM Watson, or auto-detect!

## ⚡ Quick Start (3 Steps)

### 1️⃣ Install Dependencies
```bash
cd /Users/pc/dev/techbubble/ai-bot/app-1
pip install -r requirements.txt
```

### 2️⃣ Configure Your LLM Provider

**Using IBM Watson (Recommended for you):**
```bash
# Install IBM Watson packages
bash install_ibm_watson.sh

# Copy config template
cp .env.example .env

# Edit .env and add your credentials:
# LLM_PROVIDER=ibm
# IBM_API_KEY=<your-api-key>
# IBM_PROJECT_ID=<your-project-id>
```

**OR Using OpenAI:**
```bash
# Copy config
cp .env.example .env

# Edit .env and add:
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-<your-key>
```

### 3️⃣ Start the App
```bash
python app_new.py
```

Look for this in the console:
```
[LLM] ✓ IBM Watson configured (model: ibm/granite-3-3-8b-instruct)
```
or
```
[LLM] ✓ OpenAI initialized (model: gpt-3.5-turbo)
```

## 📋 What Was Updated

✅ **llm.py** - Now supports OpenAI, IBM Watson, and fallback mode  
✅ **requirements.txt** - Added IBM Watson packages  
✅ **requirements.txt** - Already has OpenAI  
✅ **.env.example** - Comprehensive configuration guide  
✅ **LLM_SETUP.md** - Detailed provider-specific setup  
✅ **SETUP_MULTILLM.md** - Complete multi-LLM guide  

## 🎯 Key Features

### ✨ Auto-Detection
If you don't set `LLM_PROVIDER`, the app automatically:
- Uses IBM Watson if IBM credentials exist
- Falls back to OpenAI if IBM not available
- Falls back to document context if no LLM configured

### 🔄 Easy Switching
Switch providers by editing `.env` and restarting:
```bash
# Current setup
LLM_PROVIDER=ibm
IBM_API_KEY=...

# Switch to OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### 💾 No LLM? No Problem
App works without LLM - returns document context as fallback

### 📊 Provider Info in Responses
Each chat response includes which provider was used:
```json
{
  "answer": "...",
  "provider": "ibm",  // or "openai" or "fallback"
  "status": "success"
}
```

## 📦 Commands to Run

### First Time Setup
```bash
# Navigate to app directory
cd /Users/pc/dev/techbubble/ai-bot/app-1

# Install base dependencies
pip install -r requirements.txt

# For IBM Watson support (recommended)
bash install_ibm_watson.sh

# For OpenAI support (already in requirements.txt)
# No extra install needed
```

### Configuration
```bash
# Copy example config
cp .env.example .env

# Edit with your editor (replace EDITOR with vim, nano, code, etc.)
vim .env
nano .env
code .env

# View what you configured
grep -E "(LLM_PROVIDER|IBM_API|OPENAI_API)" .env
```

### Running the App
```bash
# Start the application
python app_new.py

# View just LLM logs
python app_new.py 2>&1 | grep LLM

# Run with debug output
FLASK_DEBUG=True python app_new.py
```

## 🔍 Check Your Configuration

After starting the app, look for these lines in the console:

**✓ Using IBM Watson:**
```
[LLM] Auto-detected IBM Watson from environment
[LLM] ✓ IBM Watson configured (model: ibm/granite-3-3-8b-instruct)
```

**✓ Using OpenAI:**
```
[LLM] Auto-detected OpenAI from environment
[LLM] ✓ OpenAI initialized (model: gpt-3.5-turbo)
```

**✓ Fallback (no LLM):**
```
[LLM] No LLM credentials found - running in fallback mode
```

**✗ Problems:**
```
[LLM] Warning: IBM_API_KEY not found in environment
[LLM] Error initializing OpenAI: ...
```

## 📚 Documentation Files

- **LLM_SETUP.md** - Detailed setup for each provider
- **SETUP_MULTILLM.md** - Complete multi-provider guide  
- **.env.example** - All environment variables explained

## 🧪 Testing

After setup, test the app at: **http://localhost:5000**

1. Register a new user
2. Upload or paste some documents
3. Go to Chat tab
4. Ask questions about your documents
5. Check the response includes provider info

## ⚙️ Environment Variables

### Essential
```bash
LLM_PROVIDER=ibm              # (or 'openai' or leave blank for auto)
```

### IBM Watson
```bash
IBM_API_KEY=<your-key>
IBM_PROJECT_ID=<your-project>
IBM_URL=https://api.us-south.ml.cloud.ibm.com
```

### OpenAI
```bash
OPENAI_API_KEY=sk-<your-key>
OPENAI_MODEL=gpt-3.5-turbo
```

### Other
```bash
FLASK_ENV=development
DATABASE_URL=sqlite:///app.db
VECTOR_DB_PATH=./vector_db
```

## 🚨 Troubleshooting

### Missing Modules
```bash
# If you see: "ModuleNotFoundError: No module named 'langchain_ibm'"
bash install_ibm_watson.sh

# If you see: "ModuleNotFoundError: No module named 'openai'"
pip install openai
```

### No LLM Credentials
```bash
# Check your .env file has the right keys
cat .env | grep -E "(IBM_API|OPENAI_API)"

# Copy template if missing
cp .env.example .env
# Edit and add your credentials
```

### Authentication Failed
```bash
# Verify credentials are correct
echo "API Key: $IBM_API_KEY"
echo "Project: $IBM_PROJECT_ID"

# Check .env file
cat .env | grep IBM
```

## 💡 Tips

1. **IBM Watson is free tier available** - Great for testing
2. **Auto-detection is smart** - Set both credentials, let app choose
3. **App works without LLM** - Always get document context fallback
4. **Check logs** - Look for `[LLM]` messages to see what's happening
5. **Provider is in responses** - See which LLM processed your question

## 🔗 Resources

- **OpenAI**: https://platform.openai.com/api-keys
- **IBM Watson**: https://cloud.ibm.com/docs/watsonx-ai
- **Granite Models**: https://huggingface.co/ibm-granite

## ✅ Checklist

- [ ] Installed base dependencies: `pip install -r requirements.txt`
- [ ] Installed IBM Watson (if using): `bash install_ibm_watson.sh`
- [ ] Created `.env` from `.env.example`: `cp .env.example .env`
- [ ] Added your LLM credentials to `.env`
- [ ] Set `LLM_PROVIDER` in `.env` (or leave blank for auto-detect)
- [ ] Started app: `python app_new.py`
- [ ] Checked console for `[LLM]` startup message
- [ ] Accessed app at http://localhost:5000
- [ ] Uploaded documents and tested chat

---

**Ready to go! Start with the Quick Start section above.** 🎉
