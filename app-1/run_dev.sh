#!/bin/bash

# Development startup script with auto-reload enabled

echo "Starting Flask app with auto-reload enabled..."
echo ""
echo "The app will automatically restart when you modify Python files."
echo "Press Ctrl+C to stop."
echo ""

export FLASK_ENV=development
export FLASK_DEBUG=True
export FLASK_APP=app_new.py

python -m flask run --reload --host localhost --port 5000
