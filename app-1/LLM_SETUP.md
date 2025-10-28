# LLM Provider Setup Guide

This guide explains how to configure different LLM providers for the RAG chatbot.

## Overview

The app supports multiple LLM providers:
- **OpenAI** (GPT-3.5 Turbo) - Default
- **IBM Watson** (Granite 3.3 8B) - Your current choice
- **Fallback Mode** - Returns document context without LLM processing

## Quick Start

### Using IBM Watson (Your Current Setup)

1. **Ensure you have the IBM credentials:**
   ```
   IBM_API_KEY=<your-api-key>
   IBM_PROJECT_ID=<your-project-id>
   IBM_URL=https://api.us-south.ml.cloud.ibm.com  # or your region
   ```

2. **Set in your `.env` file:**
   ```bash
   LLM_PROVIDER=ibm
   IBM_API_KEY=your-api-key-here
   IBM_PROJECT_ID=your-project-id-here
   IBM_MODEL=ibm/granite-3-3-8b-instruct
   ```

3. **Install IBM Watson packages** (if not already installed):
   ```bash
   pip install ibm-watsonx-ai langchain-ibm
   ```

### Using OpenAI

1. **Get your OpenAI API key** from https://platform.openai.com/api-keys

2. **Set in your `.env` file:**
   ```bash
   LLM_PROVIDER=openai
   OPENAI_API_KEY=sk-your-api-key-here
   OPENAI_MODEL=gpt-3.5-turbo
   ```

3. **Verify the `openai` package is installed:**
   ```bash
   pip install openai
   ```

### Auto-Detection Mode (No explicit provider)

If you don't set `LLM_PROVIDER`, the app will auto-detect:

1. **Priority order:**
   - If both IBM and OpenAI credentials are set → Uses IBM Watson
   - If only OpenAI credentials are set → Uses OpenAI
   - If only IBM credentials are set → Uses IBM Watson
   - If neither are set → Fallback mode (documents only)

2. **Example `.env` for auto-detection:**
   ```bash
   # Leave LLM_PROVIDER unset (or set to 'auto')
   IBM_API_KEY=your-ibm-key-here
   IBM_PROJECT_ID=your-project-id-here
   # App will auto-detect IBM Watson
   ```

## Environment Variables Reference

### OpenAI Configuration
```bash
OPENAI_API_KEY=sk-...              # Required for OpenAI
OPENAI_MODEL=gpt-3.5-turbo         # Optional (default: gpt-3.5-turbo)
OPENAI_TEMPERATURE=0.7             # Optional (default: 0.7)
```

### IBM Watson Configuration
```bash
IBM_API_KEY=...                    # Required for IBM Watson
IBM_PROJECT_ID=...                 # Required for IBM Watson
IBM_URL=...                        # Optional (defaults to us-south region)
IBM_MODEL=...                      # Optional (default: ibm/granite-3-3-8b-instruct)
IBM_TEMPERATURE=0.5                # Optional (default: 0.5)
```

### LLM Provider Selector
```bash
LLM_PROVIDER=openai                # 'openai', 'ibm', or leave unset for auto-detect
```

## Available IBM Watson Models

```
ibm/granite-3-3-8b-instruct       # Recommended (8B parameters)
ibm/granite-3-8b-instruct         # Alternative granite model
ibm/llama-2-70b-chat              # Llama 2 (larger, more capable)
ibm/mistral-7b-instruct           # Mistral 7B
```

## Installation & Setup

### Step 1: Install Dependencies

For OpenAI support:
```bash
pip install openai
```

For IBM Watson support:
```bash
pip install ibm-watsonx-ai langchain-ibm
```

For both:
```bash
# Simply install all requirements
pip install -r requirements.txt
```

### Step 2: Configure Environment

Copy the example file:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```bash
nano .env
# or
vim .env
# or use your favorite editor
```

### Step 3: Run the App

```bash
python app_new.py
```

The app will display which LLM provider is active:
```
[LLM] ✓ IBM Watson configured (model: ibm/granite-3-3-8b-instruct)
```
or
```
[LLM] ✓ OpenAI initialized (model: gpt-3.5-turbo)
```
or
```
[LLM] No LLM credentials found - running in fallback mode
```

## Troubleshooting

### "No LLM configured" Error

**Cause:** Neither IBM nor OpenAI credentials are set in `.env`

**Solution:** Add your credentials to `.env`:
```bash
# For IBM
IBM_API_KEY=your-api-key
IBM_PROJECT_ID=your-project-id

# OR for OpenAI
OPENAI_API_KEY=sk-your-key
```

### "ImportError: No module named 'langchain_ibm'"

**Cause:** IBM Watson packages not installed

**Solution:**
```bash
pip install ibm-watsonx-ai langchain-ibm
```

### "ImportError: No module named 'openai'"

**Cause:** OpenAI package not installed

**Solution:**
```bash
pip install openai
```

### IBM Watson Authentication Failed

**Cause:** Incorrect credentials or URL

**Solution:**
1. Verify `IBM_API_KEY` is correct
2. Verify `IBM_PROJECT_ID` is correct
3. Verify `IBM_URL` matches your region:
   - US South: `https://api.us-south.ml.cloud.ibm.com`
   - US East: `https://api.us-east.ml.cloud.ibm.com`
   - EU GB: `https://api.eu-gb.ml.cloud.ibm.com`

### OpenAI API Error

**Cause:** Invalid API key or quota exceeded

**Solution:**
1. Verify API key is correct at https://platform.openai.com/api-keys
2. Check account balance and quotas
3. Ensure the key has access to Chat Completion API

## How It Works

### Chat Endpoint Flow

1. **User sends question:** `POST /api/chat`
2. **App retrieves similar documents** from vector database
3. **LLM processes documents + question** to generate answer
4. **Response includes:** answer, source documents, LLM provider used

### Fallback Mode

If no LLM is available:
- Still retrieves relevant documents
- Returns documents as context instead of LLM-processed answer
- Marked with `"status": "fallback"` in response

## Switching Providers at Runtime

To switch LLM providers, update your `.env` file and restart the app:

```bash
# Current: Using OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Change to IBM Watson
LLM_PROVIDER=ibm
IBM_API_KEY=...
IBM_PROJECT_ID=...
```

Then restart:
```bash
# Stop the running app (Ctrl+C)
# Start it again
python app_new.py
```

## Performance Notes

- **IBM Watson (Granite 3.3 8B):** ~2-5s response time (free tier limited)
- **OpenAI (GPT-3.5):** ~1-3s response time (API pricing applies)
- **Fallback Mode:** Instant (no API calls)

## Additional Resources

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [IBM Watson Documentation](https://cloud.ibm.com/docs/watsonx-ai)
- [Granite Model Details](https://huggingface.co/ibm-granite)
