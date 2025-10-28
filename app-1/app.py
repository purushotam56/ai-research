import os
import sys
from pathlib import Path
import gradio as gr
from flask import Flask, request, jsonify
from flask_cors import CORS
import tempfile
from werkzeug.utils import secure_filename

# Import custom modules
from database import db, User, Document
from auth import register_user, login_user, get_user_by_id
from processor import (
    is_valid_url, scrape_url, process_pdf_file, process_text_file,
    extract_meaningful_content, supported_file_type, get_file_extension
)
from vector_store import VectorStore
from llm import RAGChatBot, create_chatbot

# Configuration
class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    UPLOAD_FOLDER = 'uploads'

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Initialize database
db.init_app(app)

# Create upload folder
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

# Initialize vector store
# vector_store = VectorStore(persist_dir='./vector_db')
vector_store = None

def get_vector_store():
    global vector_store
    if vector_store is None:
        vector_store = VectorStore(persist_dir='./vector_db')
    return vector_store

# Initialize chatbot
chatbot = None

def get_chatbot():
    global chatbot
    if chatbot is None:
        try:
            chatbot = create_chatbot()
        except Exception as e:
            print(f"Warning: Chatbot init failed: {e}")
    return chatbot

# Global variable to track current logged-in user (for Gradio interface)
current_user = {'id': None, 'username': None}

# ============= FLASK ROUTES =============

@app.route('/api/register', methods=['POST'])
def api_register():
    """Register new user via API"""
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    result = register_user(username, email, password)
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code

@app.route('/api/login', methods=['POST'])
def api_login():
    """Login user via API"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    result = login_user(username, password)
    status_code = 200 if result.get('success') else 401
    return jsonify(result), status_code

@app.route('/api/user/<int:user_id>', methods=['GET'])
def api_get_user(user_id):
    """Get user info"""
    result = get_user_by_id(user_id)
    status_code = 200 if result.get('success') else 404
    return jsonify(result), status_code

@app.route('/api/documents/<int:user_id>', methods=['GET'])
def api_get_user_documents(user_id):
    """Get all documents for a user"""
    try:
        documents = Document.query.filter_by(user_id=user_id).all()
        return jsonify({
            'success': True,
            'documents': [doc.to_dict() for doc in documents]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/documents/<int:doc_id>', methods=['GET'])
def api_get_document(doc_id):
    """Get document details"""
    try:
        doc = Document.query.get(doc_id)
        if not doc:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        return jsonify({
            'success': True,
            'document': doc.to_dict(),
            'content_preview': doc.content[:500] + '...' if len(doc.content) > 500 else doc.content
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/search', methods=['POST'])
def api_search():
    """Search documents using vector similarity"""
    data = request.get_json()
    query = data.get('query')
    user_id = data.get('user_id')
    num_results = data.get('num_results', 5)
    
    if not query:
        return jsonify({'success': False, 'error': 'Query required'}), 400
    
    result = vector_store.search_documents(query, user_id, num_results)
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Chat endpoint with RAG"""
    data = request.get_json()
    user_id = data.get('user_id')
    question = data.get('question')
    doc_id = data.get('doc_id')  # Optional: specific document
    chat_history = data.get('chat_history', [])
    use_llm = data.get('use_llm', True)
    
    if not user_id or not question:
        return jsonify({'success': False, 'error': 'user_id and question required'}), 400
    
    try:
        vs = get_vector_store()
        if not vs:
            return jsonify({'success': False, 'error': 'Vector store not available'}), 400
        
        # Search for relevant documents
        search_result = vs.search_documents(question, user_id, num_results=5)
        
        if not search_result.get('success') or not search_result.get('results'):
            return jsonify({
                'success': False,
                'error': 'No matching documents found'
            }), 400
        
        context = search_result['results']
        
        # Get chatbot and generate answer
        if use_llm:
            cb = get_chatbot()
            if cb:
                result = cb.generate_answer(question, context, chat_history)
            else:
                # Fallback to document search
                result = {
                    'success': True,
                    'answer': f"LLM not available. Here's relevant content:\n\n{context[0]['document'][:300]}...",
                    'model': 'document-search'
                }
        else:
            # Use document search only
            result = {
                'success': True,
                'answer': context[0]['document'][:500] + "...",
                'model': 'document-search'
            }
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'answer': result.get('answer'),
                'model': result.get('model', 'gpt-3.5-turbo'),
                'sources': [c['metadata'].get('title', 'Unknown') for c in context[:3]]
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to generate answer')
            }), 400
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# ============= GRADIO INTERFACE =============

def gradio_login(username, password):
    """Gradio function for login"""
    result = login_user(username, password)
    if result['success']:
        current_user['id'] = result['user_id']
        current_user['username'] = username
        return f"✓ Welcome {username}!", result['user_id']
    else:
        return f"✗ Login failed: {result['error']}", None

def gradio_register(username, email, password, confirm_password):
    """Gradio function for registration"""
    if password != confirm_password:
        return "✗ Passwords do not match!"
    
    result = register_user(username, email, password)
    if result['success']:
        return f"✓ Registration successful! You can now login."
    else:
        return f"✗ Registration failed: {result['error']}"

def gradio_add_url(user_id, url):
    """Gradio function to add URL"""
    if not user_id:
        return "✗ Please login first!"
    
    if not url:
        return "✗ Please enter a URL!"
    
    if not is_valid_url(url):
        return "✗ Invalid URL format!"
    
    try:
        # Scrape URL
        scrape_result = scrape_url(url)
        if not scrape_result['success']:
            return f"✗ Scraping failed: {scrape_result['error']}"
        
        title = scrape_result['title']
        content = scrape_result['content']
        
        # Extract meaningful content
        meaningful_content = extract_meaningful_content(content)
        
        # Store in database
        doc = Document(
            user_id=user_id,
            title=title,
            source_type='url',
            source_url=url,
            content=meaningful_content
        )
        db.session.add(doc)
        db.session.commit()
        
        # Add to vector store
        vs = get_vector_store()
        vector_result = vs.add_document(
            user_id=user_id,
            document_id=doc.id,
            title=title,
            content=meaningful_content,
            metadata={'source_url': url}
        )
        
        if vector_result['success']:
            doc.vector_ids = ','.join(vector_result['vector_ids'])
            db.session.commit()
            vector_store.persist()
            return f"✓ URL added successfully!\n📄 Title: {title}\n📊 Chunks: {vector_result['num_chunks']}"
        else:
            return f"✗ Error adding to vector store: {vector_result['error']}"
    
    except Exception as e:
        db.session.rollback()
        return f"✗ Error: {str(e)}"

def gradio_upload_file(user_id, file):
    """Gradio function to upload file"""
    if not user_id:
        return "✗ Please login first!"
    
    if file is None:
        return "✗ Please select a file!"
    
    try:
        filename = secure_filename(file.name)
        
        if not supported_file_type(filename):
            return "✗ File type not supported. Supported: PDF, TXT, MD"
        
        # Save file temporarily
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Process file based on type
        ext = get_file_extension(filename)
        
        if ext == '.pdf':
            process_result = process_pdf_file(file_path)
        else:  # .txt, .md
            process_result = process_text_file(file_path)
        
        if not process_result['success']:
            return f"✗ Processing failed: {process_result['error']}"
        
        title = process_result['title']
        content = process_result['content']
        
        # Extract meaningful content
        meaningful_content = extract_meaningful_content(content)
        
        # Store in database
        doc = Document(
            user_id=user_id,
            title=title,
            source_type='file',
            filename=filename,
            content=meaningful_content
        )
        db.session.add(doc)
        db.session.commit()
        
        # Add to vector store
        vector_result = vector_store.add_document(
            user_id=user_id,
            document_id=doc.id,
            title=title,
            content=meaningful_content,
            metadata={'filename': filename}
        )
        
        if vector_result['success']:
            doc.vector_ids = ','.join(vector_result['vector_ids'])
            db.session.commit()
            vector_store.persist()
            return f"✓ File uploaded successfully!\n📄 Title: {title}\n📊 Chunks: {vector_result['num_chunks']}"
        else:
            return f"✗ Error adding to vector store: {vector_result['error']}"
    
    except Exception as e:
        db.session.rollback()
        return f"✗ Error: {str(e)}"
    finally:
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)

def gradio_list_documents(user_id):
    """Gradio function to list user documents"""
    if not user_id:
        return "✗ Please login first!"
    
    try:
        documents = Document.query.filter_by(user_id=user_id).all()
        
        if not documents:
            return "No documents yet. Add some URLs or upload files!"
        
        output = "📚 Your Documents:\n\n"
        for doc in documents:
            source = f"URL: {doc.source_url}" if doc.source_type == 'url' else f"File: {doc.filename}"
            output += f"• {doc.title}\n  {source}\n  Added: {doc.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        return output
    
    except Exception as e:
        return f"✗ Error: {str(e)}"

def gradio_search(user_id, query):
    """Gradio function to search documents"""
    if not user_id:
        return "✗ Please login first!"
    
    if not query:
        return "✗ Please enter a search query!"
    
    try:
        result = vector_store.search_documents(query, user_id, num_results=5)
        
        if not result['success']:
            return f"✗ Search failed: {result['error']}"
        
        if not result['results']:
            return "No matching documents found."
        
        output = f"🔍 Search Results for: '{query}'\n\n"
        for i, res in enumerate(result['results'], 1):
            metadata = res['metadata']
            output += f"{i}. Document: {metadata.get('title', 'Unknown')}\n"
            output += f"   Chunk {metadata.get('chunk_index', 0) + 1}/{metadata.get('chunk_count', 1)}\n"
            output += f"   {res['document'][:200]}...\n\n"
        
        return output
    
    except Exception as e:
        return f"✗ Error: {str(e)}"

# ============= BUILD GRADIO INTERFACE =============

def create_gradio_interface():
    with gr.Blocks(title="RAG Document Manager", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# 📚 RAG Document Manager")
        gr.Markdown("Manage your documents with intelligent vector storage for future RAG queries")
        
        with gr.Tabs():
            # TAB 1: AUTH
            with gr.Tab("🔐 Authentication"):
                with gr.Group():
                    gr.Markdown("### Register")
                    reg_username = gr.Textbox(label="Username", placeholder="Choose a username")
                    reg_email = gr.Textbox(label="Email", placeholder="your@email.com")
                    reg_password = gr.Textbox(label="Password", type="password")
                    reg_confirm = gr.Textbox(label="Confirm Password", type="password")
                    reg_button = gr.Button("Register", variant="primary")
                    reg_output = gr.Textbox(label="Status", interactive=False)
                    
                    reg_button.click(
                        gradio_register,
                        inputs=[reg_username, reg_email, reg_password, reg_confirm],
                        outputs=[reg_output]
                    )
                
                gr.Markdown("---")
                
                with gr.Group():
                    gr.Markdown("### Login")
                    login_username = gr.Textbox(label="Username")
                    login_password = gr.Textbox(label="Password", type="password")
                    login_button = gr.Button("Login", variant="primary")
                    login_output = gr.Textbox(label="Status", interactive=False)
                    user_id_state = gr.State(None)
                    
                    login_button.click(
                        gradio_login,
                        inputs=[login_username, login_password],
                        outputs=[login_output, user_id_state]
                    )
            
            # TAB 2: UPLOAD DATA
            with gr.Tab("📤 Add Data"):
                gr.Markdown("### Add data from URL or upload files")
                user_id_input = gr.Number(label="User ID (from login)", precision=0)
                
                with gr.Group():
                    gr.Markdown("#### Add from URL")
                    url_input = gr.Textbox(label="URL", placeholder="https://example.com")
                    url_button = gr.Button("Scrape & Add", variant="primary")
                    url_output = gr.Textbox(label="Result", interactive=False, lines=3)
                    
                    url_button.click(
                        gradio_add_url,
                        inputs=[user_id_input, url_input],
                        outputs=[url_output]
                    )
                
                gr.Markdown("---")
                
                with gr.Group():
                    gr.Markdown("#### Upload File")
                    file_input = gr.File(label="Upload PDF, TXT, or MD file", type="filepath")
                    file_button = gr.Button("Upload & Process", variant="primary")
                    file_output = gr.Textbox(label="Result", interactive=False, lines=3)
                    
                    file_button.click(
                        gradio_upload_file,
                        inputs=[user_id_input, file_input],
                        outputs=[file_output]
                    )
            
            # TAB 3: MANAGE DOCUMENTS
            with gr.Tab("📚 My Documents"):
                user_id_input2 = gr.Number(label="User ID (from login)", precision=0)
                list_button = gr.Button("Load My Documents", variant="primary")
                docs_output = gr.Textbox(label="Documents", interactive=False, lines=10)
                
                list_button.click(
                    gradio_list_documents,
                    inputs=[user_id_input2],
                    outputs=[docs_output]
                )
            
            # TAB 4: SEARCH
            with gr.Tab("🔍 Search"):
                user_id_input3 = gr.Number(label="User ID (from login)", precision=0)
                search_query = gr.Textbox(label="Search Query", placeholder="What are you looking for?")
                search_button = gr.Button("Search", variant="primary")
                search_output = gr.Textbox(label="Results", interactive=False, lines=10)
                
                search_button.click(
                    gradio_search,
                    inputs=[user_id_input3, search_query],
                    outputs=[search_output]
                )
            
            # TAB 5: INFO
            with gr.Tab("ℹ️ Info"):
                gr.Markdown("""
                ## How to Use

                ### Step 1: Authentication
                - **Register**: Create a new account with username, email, and password
                - **Login**: Sign in with your credentials. Note your User ID for next steps

                ### Step 2: Add Data
                Choose one:
                - **From URL**: Paste a web URL, and the system will scrape meaningful content
                - **Upload File**: Upload PDF, TXT, or Markdown files

                ### Step 3: View Documents
                See all your uploaded/scraped documents and their metadata

                ### Step 4: Search
                Use semantic search to find relevant content across all your documents

                ## Technical Details
                - **Database**: SQLite for user management
                - **Vector Store**: ChromaDB for semantic search
                - **Text Processing**: BeautifulSoup for web scraping, PyPDF2 for PDF extraction
                - **Embeddings**: Sentence-Transformers (all-MiniLM-L6-v2 model)

                ## Next Steps
                Future integration will include RAG (Retrieval-Augmented Generation) to answer questions using your document knowledge.
                """)
    
    return interface

# ============= MAIN ENTRY POINT =============

if __name__ == '__main__':
    with app.app_context():
        # Create database tables
        db.create_all()
        print("✓ Database initialized")
    
    # Create Gradio interface
    gradio_interface = create_gradio_interface()
    
    # Launch Gradio with Flask in background
    print("\n🚀 Starting RAG Document Manager...")
    print("📊 Gradio Interface: http://127.0.0.1:7860")
    print("🔌 Flask API: http://127.0.0.1:5000")
    print("\n(Flask runs in background, use Gradio interface)")
    
    gradio_interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True
    )
