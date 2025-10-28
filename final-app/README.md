# final-app: Gradio + Flask scraper

This small app embeds a Gradio interface in a Flask page. The Gradio UI accepts either a URL or a file upload (PDF or text). It will attempt to extract text from the provided source and show the extracted content.

Quick start

1. Create a virtual environment (recommended) and activate it:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python app.py
```

This will launch Gradio on http://localhost:7860 and Flask on http://localhost:5000. Open http://localhost:5000 to see a page embedding the Gradio UI.

Notes
- The app uses BeautifulSoup for HTML scraping and PyPDF2 for PDF text extraction.
- The Gradio server is launched with `prevent_thread_lock=True` so the script starts Gradio non-blocking then runs Flask.

If you want the Gradio interface directly, open http://localhost:7860
