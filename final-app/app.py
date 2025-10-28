import io
import threading
import uuid
import hashlib
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
import gradio as gr
import PyPDF2

from db import init_db, create_user, get_user_by_username, add_document_record, list_user_documents
from vector_store import create_client, get_or_create_collection, add_documents, query

from sentence_transformers import SentenceTransformer

app = Flask(__name__)
app.secret_key = "changeme-secret-key"


def extract_text_from_url(url: str) -> str:
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    # Remove script and style
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Collapse multiple blank lines
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines[:10000])


def extract_text_from_file(file_obj) -> str:
    # file_obj is a tempfile-like object from Gradio; read bytes
    content = file_obj.read()
    # Try PDF first
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                continue
        text = "\n".join(texts)
        if text.strip():
            return text
    except Exception:
        pass

    # Fallback: try decode as utf-8 text
    try:
        return content.decode("utf-8", errors="replace")
    except Exception:
        return "<binary file: unable to extract text>"


def process(url: str, upload) -> str:
    url = (url or "").strip()
    if url:
        try:
            return extract_text_from_url(url)
        except Exception as e:
            return f"Error fetching URL: {e}"

    if upload is not None:
        try:
            # Gradio provides a file-like object with a .name attribute
            return extract_text_from_file(upload)
        except Exception as e:
            return f"Error reading uploaded file: {e}"

    return "Please provide a URL or upload a file."


def create_gradio_app():
    with gr.Blocks() as demo:
        gr.Markdown("# URL scraper / File extractor\nProvide a URL or upload a file (PDF or text) and click Submit.")
        with gr.Row():
            url_in = gr.Textbox(label="URL (optional)")
            file_in = gr.File(label="Upload file (optional)")
        out = gr.Textbox(label="Extracted text", interactive=False)
        submit = gr.Button("Submit")

        submit.click(fn=process, inputs=[url_in, file_in], outputs=out)

    return demo


GRADIO_PORT = 7860


@app.route("/")
def index():
    # Embed gradio app in an iframe
    html = f"""
    <!doctype html>
    <html>
      <head>
        <meta charset=\"utf-8\"> 
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> 
        <title>Gradio + Flask - Scraper</title>
      </head>
      <body>
        <h1>Gradio + Flask - Scraper</h1>
        <p>The Gradio app runs on port {GRADIO_PORT}. If it is not started yet, start this script and it will launch both servers.</p>
        <iframe src=\"http://localhost:{GRADIO_PORT}\" width=\"100%\" height=\"800\" style=\"border:1px solid #ddd\"></iframe>
      </body>
    </html>
    """
    return render_template_string(html)


def main():
    # initialize DB and vector store
    init_db()

    # simple embedding model
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    client = create_client()
    collection = get_or_create_collection(client, "documents")

    demo = create_gradio_app()
    # Launch gradio in non-blocking mode
    demo.launch(server_name="127.0.0.1", server_port=GRADIO_PORT, share=False, prevent_thread_lock=True)

    # Then start Flask app (blocking)
    app.run(host="0.0.0.0", port=5000)


# Minimal Flask endpoints for auth and uploads


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


@app.route("/register", methods=["POST"])
def register():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    if get_user_by_username(username):
        return jsonify({"error": "user exists"}), 400
    user_id = create_user(username, hash_password(password))
    return jsonify({"user_id": user_id}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    user = get_user_by_username(username)
    if not user or user["password"] != hash_password(password):
        return jsonify({"error": "invalid credentials"}), 401
    session["user_id"] = user["id"]
    return jsonify({"user_id": user["id"]})


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"ok": True})


@app.route("/me/docs", methods=["GET"])
def my_docs():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "not logged in"}), 401
    docs = list_user_documents(user_id)
    return jsonify(docs)


@app.route("/upload", methods=["POST"])
def upload():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "not logged in"}), 401

    url = request.form.get("url")
    file = request.files.get("file")

    content = None
    source = ""
    if url:
        try:
            content = extract_text_from_url(url)
            source = url
        except Exception as e:
            return jsonify({"error": f"error fetching url: {e}"}), 400
    elif file:
        try:
            content = extract_text_from_file(file.stream)
            source = getattr(file, "filename", "uploaded")
        except Exception as e:
            return jsonify({"error": f"error reading file: {e}"}), 400
    else:
        return jsonify({"error": "provide url or file"}), 400

    snippet = content[:500]

    # create an id and add to chroma
    doc_id = str(uuid.uuid4())
    # Using client here would require passing it; for simplicity create one
    client = create_client()
    collection = get_or_create_collection(client, "documents")

    # embed via model
    model = SentenceTransformer("all-MiniLM-L6-v2")
    emb = model.encode([content])
    add_documents(collection, ids=[doc_id], metadatas=[{"user_id": user_id, "source": source}], documents=[snippet], embeddings=emb.tolist())

    add_document_record(user_id, source, snippet, doc_id)

    return jsonify({"ok": True, "doc_id": doc_id})


if __name__ == "__main__":
    main()
