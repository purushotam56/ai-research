import os 
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from urllib.parse import urlparse

# Import custom modules
from database import db, User, Document
from auth import register_user, login_user, get_user_by_id
from processor import (
    is_valid_url, scrape_url, process_pdf_file, process_text_file,
    extract_meaningful_content, supported_file_type, get_file_extension
)
from vector_store import VectorStore
from llm import create_chatbot

# Configuration
class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = 'uploads'
    SECRET_KEY = 'dev-secret-key'

# Initialize Flask
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Initialize database
db.init_app(app)
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

# Initialize vector store
try:
    vector_store = VectorStore(persist_dir='./vector_db')
except Exception as e:
    print(f"Warning: Vector store init failed: {e}")
    vector_store = None

# Initialize chatbot
try:
    chatbot = create_chatbot(vector_store=vector_store)
except Exception as e:
    print(f"Warning: Chatbot init failed: {e}")
    chatbot = None

# ============= WEB PAGES =============

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard page"""
    return render_template('dashboard.html')

# ============= API ROUTES =============

@app.route('/api/register', methods=['POST'])
def api_register():
    """Register new user"""
    data = request.get_json()
    result = register_user(
        data.get('username'),
        data.get('email'),
        data.get('password')
    )
    status = 200 if result.get('success') else 400
    return jsonify(result), status

@app.route('/api/login', methods=['POST'])
def api_login():
    """Login user"""
    data = request.get_json()
    result = login_user(data.get('username'), data.get('password'))
    status = 200 if result.get('success') else 401
    return jsonify(result), status

@app.route('/api/documents/<int:user_id>', methods=['GET'])
def api_get_documents(user_id):
    """Get user documents"""
    try:
        documents = Document.query.filter_by(user_id=user_id).all()
        return jsonify({
            'success': True,
            'documents': [doc.to_dict() for doc in documents]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/document/<int:doc_id>', methods=['GET'])
def api_get_document(doc_id):
    """Get document details"""
    try:
        doc = Document.query.get(doc_id)
        if not doc:
            return jsonify({'success': False, 'error': 'Not found'}), 404
        
        preview = doc.content[:500] + '...' if len(doc.content) > 500 else doc.content
        return jsonify({
            'success': True,
            'document': doc.to_dict(),
            'preview': preview
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/document/<int:doc_id>', methods=['DELETE'])
def api_delete_document(doc_id):
    """Delete document"""
    try:
        doc = Document.query.get(doc_id)
        if not doc:
            return jsonify({'success': False, 'error': 'Not found'}), 404
        
        # Delete from vector store
        if vector_store and doc.vector_ids:
            vector_store.delete_document_vectors(doc.id)
            vector_store.persist()
        
        # Delete from database
        db.session.delete(doc)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Document deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/add-url', methods=['POST'])
def api_add_url():
    """Add document from URL"""
    data = request.get_json()
    user_id = data.get('user_id')
    url = data.get('url')
    
    if not user_id or not url:
        return jsonify({'success': False, 'error': 'Missing fields'}), 400
    
    if not is_valid_url(url):
        return jsonify({'success': False, 'error': 'Invalid URL'}), 400
    
    try:
        # Scrape URL
        scrape_result = scrape_url(url)
        if not scrape_result.get('success'):
            return jsonify(scrape_result), 400
        
        title = scrape_result['title']
        # Ensure title is never None or empty
        if not title:
            title = urlparse(url).netloc or "Webpage"
        
        content = extract_meaningful_content(scrape_result['content'])
        
        # Store in database
        doc = Document(
            user_id=user_id,
            title=title,
            source_type='url',
            source_url=url,
            content=content
        )
        db.session.add(doc)
        db.session.commit()
        
        # Add to vector store
        if vector_store:
            try:
                vector_result = vector_store.add_document(
                    user_id, doc.id, title, content,
                    metadata={'source_url': url}
                )
                if vector_result.get('success'):
                    doc.vector_ids = ','.join(vector_result['vector_ids'])
                    db.session.commit()
                    vector_store.persist()
                else:
                    print(f"Vector store error: {vector_result.get('error')}")
            except Exception as ve:
                print(f"Error adding to vector store: {ve}")
        
        return jsonify({
            'success': True,
            'message': f'Added: {title}',
            'document': doc.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/upload-file', methods=['POST'])
def api_upload_file():
    """Upload and process file"""
    user_id = request.form.get('user_id')
    file = request.files.get('file')
    
    if not user_id or not file:
        return jsonify({'success': False, 'error': 'Missing fields'}), 400
    
    try:
        filename = secure_filename(file.filename)
        if not supported_file_type(filename):
            return jsonify({'success': False, 'error': 'File type not supported'}), 400
        
        # Save temporarily
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Process file
        ext = get_file_extension(filename)
        if ext == '.pdf':
            process_result = process_pdf_file(file_path)
        else:
            process_result = process_text_file(file_path)
        
        if not process_result.get('success'):
            os.remove(file_path)
            return jsonify(process_result), 400
        
        title = process_result['title']
        raw_content = process_result['content']
        
        # Log for debugging
        print(f"[UPLOAD] PDF extraction result:")
        print(f"  - Title: {title}")
        print(f"  - Raw content length: {len(raw_content)} chars")
        if raw_content:
            print(f"  - Content preview: {raw_content[:100]}...")
        else:
            print(f"  - WARNING: Empty content from PDF!")
        
        content = extract_meaningful_content(raw_content)
        print(f"  - After filtering: {len(content)} chars")
        
        # Store in database
        doc = Document(
            user_id=user_id,
            title=title,
            source_type='file',
            filename=filename,
            content=content
        )
        db.session.add(doc)
        db.session.commit()
        
        # Add to vector store
        if vector_store:
            try:
                vector_result = vector_store.add_document(
                    user_id, doc.id, title, content,
                    metadata={'filename': filename}
                )
                if vector_result.get('success'):
                    doc.vector_ids = ','.join(vector_result['vector_ids'])
                    db.session.commit()
                    vector_store.persist()
                else:
                    print(f"Vector store error: {vector_result.get('error')}")
            except Exception as ve:
                print(f"Error adding to vector store: {ve}")
        
        # Clean up
        os.remove(file_path)
        
        return jsonify({
            'success': True,
            'message': f'Uploaded: {title}',
            'document': doc.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/search', methods=['POST'])
def api_search():
    """Search documents"""
    data = request.get_json()
    query = data.get('query')
    user_id = data.get('user_id')
    num_results = data.get('num_results', 5)
    
    if not query or not user_id:
        return jsonify({'success': False, 'error': 'Missing fields'}), 400
    
    try:
        if not vector_store:
            return jsonify({'success': False, 'error': 'Vector store not available'}), 400
        
        result = vector_store.search_documents(query, user_id, num_results)
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Chat endpoint with RAG"""
    data = request.get_json()
    user_id = data.get('user_id')
    question = data.get('question')
    doc_id = data.get('doc_id')  # Optional: specific document
    chat_history = data.get('chat_history', [])
    use_llm = data.get('use_llm', True)
    llm_model = data.get('llm_model', 'openai-gpt35')  # New: selected model from UI
    
    if not user_id or not question:
        return jsonify({'success': False, 'error': 'user_id and question required'}), 400
    
    try:
        if not vector_store:
            return jsonify({'success': False, 'error': 'Vector store not available'}), 400
        
        # Verify document belongs to user if doc_id is specified
        if doc_id:
            doc = Document.query.get(doc_id)
            if not doc or doc.user_id != user_id:
                return jsonify({'success': False, 'error': 'Document not found or access denied'}), 403
        
        # Search for relevant documents
        search_result = vector_store.search_documents(question, user_id, num_results=5, doc_id=doc_id)
        
        if not search_result.get('success') or not search_result.get('results'):
            return jsonify({
                'success': False,
                'error': 'No matching documents found'
            }), 400
        
        # Extract document text from search results
        context_docs = [result['document'] for result in search_result['results']]
        
        # Get chatbot and generate answer
        if use_llm:
            if chatbot:
                # Pass the selected model to the chatbot
                result = chatbot.generate_answer(question, context_docs, user_id, llm_model=llm_model)
            else:
                # Fallback to document search
                result = {
                    'answer': f"LLM not available. Here's relevant content:\n\n{context_docs[0][:300]}...",
                    'status': 'fallback',
                    'provider': 'fallback',
                    'sources': [c['metadata'].get('title', 'Unknown') for c in search_result['results'][:3]],
                    'model': None
                }
        else:
            # Use document search only
            result = {
                'answer': context_docs[0][:500] + "...",
                'status': 'document-search',
                'provider': 'document-search',
                'sources': [c['metadata'].get('title', 'Unknown') for c in search_result['results'][:3]],
                'model': None
            }
        
        return jsonify({
            'success': True,
            'answer': result.get('answer'),
            'provider': result.get('provider', 'unknown'),
            'status': result.get('status', 'success'),
            'sources': result.get('sources', []),
            'model': result.get('model', llm_model)
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# ============= ERROR HANDLERS =============

@app.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'success': False, 'error': 'Server error'}), 500

# ============= MAIN =============

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("✓ Database initialized")
    
    print("\n🚀 Starting RAG Document Manager (Debug Mode - Auto-Reload Enabled)")
    print("📊 Web Interface: http://127.0.0.1:5000")
    print("🔌 API: http://127.0.0.1:5000/api/*")
    print("🔄 File changes will automatically reload the app")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True,
        use_reloader=True
    )
