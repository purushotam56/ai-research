# Auto-Reload Setup - File Changes Now Restart App Automatically

## ✅ What Changed

Flask debug mode is now **enabled** in `app_new.py`:
- `debug=True` - enables debug mode with error stack traces
- `use_reloader=True` - watches Python files for changes
- App **automatically restarts** when you modify any Python file

## 🚀 How to Start

### Option 1: Simple Start (Recommended)
```bash
cd /Users/pc/dev/techbubble/ai-bot/app-1
python app_new.py
```

### Option 2: Using Bash Script
```bash
bash start.sh
```

### Option 3: Manual Flask Command
```bash
export FLASK_ENV=development
export FLASK_DEBUG=True
python -m flask run --reload --host 127.0.0.1 --port 5000
```

## 📝 What You'll See on Startup

```
🚀 Starting RAG Document Manager (Debug Mode - Auto-Reload Enabled)
📊 Web Interface: http://127.0.0.1:5000
🔌 API: http://127.0.0.1:5000/api/*
🔄 File changes will automatically reload the app

Press Ctrl+C to stop
```

## 🔄 Auto-Reload in Action

When you modify any Python file in the app (like `llm.py`, `app_new.py`, etc.):

1. Flask detects the change
2. Console shows: `* Detected change in [filename], reloading`
3. App restarts automatically
4. No need to stop and restart manually!

## 📁 Files Modified

- **app_new.py** - Changed `debug=False` → `debug=True` and added `use_reloader=True`
- **run_dev.sh** - Development startup script with flask run --reload (optional)
- **start.sh** - Simple startup script

## 🎯 Perfect For Development

Now when you:
- Fix code in `llm.py` → app reloads
- Modify `app_new.py` routes → app reloads  
- Change `processor.py` → app reloads
- Update `vector_store.py` → app reloads

**No manual restarts needed!** 🎉

## ⚠️ Notes

- Debug mode is slower than production mode (normal for development)
- Some changes to imports or class definitions might still need manual restart
- If you see errors, check the Flask console for stack traces
- Press Ctrl+C to stop the server (you may need to press it twice)

## 🛑 To Disable Auto-Reload

If you need to disable it, run:
```bash
export FLASK_DEBUG=False
python app_new.py
```

Or edit `app_new.py` and change `debug=True` back to `debug=False`
