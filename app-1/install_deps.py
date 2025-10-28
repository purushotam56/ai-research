#!/usr/bin/env python3
"""
Dependency installer script with detailed progress reporting.
More user-friendly than direct pip install.
"""

import subprocess
import sys
from pathlib import Path

def print_banner(text):
    print(f"\n{'='*50}")
    print(f"  {text}")
    print(f"{'='*50}\n")

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8+ required. You have {version.major}.{version.minor}")
        sys.exit(1)
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")

def run_command(cmd, description=""):
    """Run command and report results"""
    try:
        if description:
            print(f"→ {description}...")
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"✓ {description if description else cmd}")
            return True
        else:
            print(f"✗ {description if description else cmd}")
            if result.stderr:
                print(f"  Error: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"✗ Error running command: {e}")
        return False

def main():
    print_banner("RAG Document Manager - Dependency Installer")
    
    # Check Python version
    print("Checking Python version...")
    check_python_version()
    
    # Upgrade pip
    print("\nUpgrading pip, setuptools, wheel...")
    run_command("pip install --upgrade pip setuptools wheel", "Upgrading pip")
    
    # Install requirements
    print_banner("Installing Requirements")
    
    requirements = {
        "flask==3.0.0": "Flask Web Framework",
        "flask-cors==4.0.0": "Flask CORS Support",
        "flask-sqlalchemy==3.1.1": "SQLAlchemy ORM",
        "gradio==4.26.0": "Gradio UI Framework",
        "requests==2.31.0": "HTTP Requests Library",
        "beautifulsoup4==4.12.2": "Web Scraping",
        "lxml==4.9.3": "XML/HTML Parser",
        "chromadb==0.4.21": "Vector Database",
        "sentence-transformers==2.2.2": "Text Embeddings",
        "python-dotenv==1.0.0": "Environment Variables",
        "pypdf==3.17.1": "PDF Text Extraction",
        "python-multipart==0.0.6": "Form Data Parsing",
        "werkzeug==3.0.1": "WSGI Utilities",
    }
    
    failed = []
    for package, description in requirements.items():
        if not run_command(f"pip install {package}", description):
            failed.append(package)
    
    # Summary
    print_banner("Installation Summary")
    
    if failed:
        print(f"✗ {len(failed)} package(s) failed to install:")
        for pkg in failed:
            print(f"  - {pkg}")
        print("\n❌ Installation incomplete. Try running again or check internet connection.")
        sys.exit(1)
    else:
        print(f"✓ All {len(requirements)} packages installed successfully!")
        print("\n📌 Next steps:")
        print("  1. Run: python3 -c \"from app import app, db; app.app_context().push(); db.create_all()\"")
        print("  2. Run: python3 app.py")
        print("  3. Open: http://127.0.0.1:7860")

if __name__ == "__main__":
    main()
