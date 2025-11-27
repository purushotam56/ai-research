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

# ============= HELPER FUNCTIONS =============

def extract_key_information(question: str, context: str) -> str:
    """Extract relevant information from context based on question."""
    try:
        # Look for specific patterns in the context
        lines = context.split('\n')
        
        # Try to find directly relevant lines
        question_lower = question.lower()
        relevant_lines = []
        
        for line in lines:
            line_lower = line.lower()
            # Check if any word from question appears in the line
            if any(word in line_lower for word in question_lower.split() if len(word) > 3):
                if line.strip() and not line.startswith('---'):
                    relevant_lines.append(line.strip())
        
        if relevant_lines:
            # Return formatted relevant information
            answer = "Based on the documents, here's what I found:\n\n"
            for line in relevant_lines[:5]:  # Limit to 5 lines
                if line:
                    answer += f"• {line}\n"
            return answer
        else:
            # Fallback to first meaningful section
            for line in lines[:10]:
                if line.strip() and not line.startswith('[Section') and not line.startswith('---'):
                    return f"Based on the available information:\n\n{line}\n\nPlease ask more specific questions about team members, services, or other details."
            
            return "I found documents but couldn't extract specific information. Please try rephrasing your question."
    except:
        return "Unable to extract information from documents."

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

@app.route('/api/available-models', methods=['GET'])
def api_available_models():
    """Get list of available LLM models"""
    import requests
    
    available_models = {
        'cloud_models': [
            {'id': 'openai-gpt35', 'name': 'OpenAI - GPT-3.5 Turbo', 'desc': 'Fast, High Quality'},
            {'id': 'openai-gpt4', 'name': 'OpenAI - GPT-4', 'desc': 'Advanced, Slower'},
            {'id': 'perplexity-sonar', 'name': 'Perplexity - Sonar', 'desc': 'Fast, Free tier'},
            {'id': 'perplexity-sonar-pro', 'name': 'Perplexity - Sonar Pro', 'desc': 'Advanced reasoning'},
            {'id': 'ibm-granite', 'name': 'IBM Watson - Granite', 'desc': 'Good, Free tier'},
        ],
        'offline_models': [],
        'other_models': [
            {'id': 'document-search', 'name': 'Document Search Only', 'desc': 'No AI'}
        ]
    }
    
    # Check for Ollama availability
    ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    try:
        response = requests.get(f"{ollama_host}/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get('models', [])
            for model in models:
                model_name = model.get('name', '').split(':')[0]
                available_models['offline_models'].append({
                    'id': f'ollama-{model_name}',
                    'name': f'Ollama - {model_name.title()}',
                    'desc': 'Local, Offline',
                    'size': model.get('size', 0)
                })
    except:
        pass
    
    # Check for LlamaCpp availability
    llamacpp_model = os.getenv('LLAMACPP_MODEL_PATH')
    if llamacpp_model and os.path.exists(llamacpp_model):
        available_models['offline_models'].append({
            'id': 'llamacpp-default',
            'name': 'LlamaCpp - GGUF Model',
            'desc': f'Local: {os.path.basename(llamacpp_model)}'
        })
    
    return jsonify({
        'success': True,
        'models': available_models
    }), 200

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
    """Delete document and all its children (if parent) from DB and vector store"""
    try:
        doc = Document.query.get(doc_id)
        if not doc:
            return jsonify({'success': False, 'error': 'Not found'}), 404
        
        # Check if this is a parent document (parent_id is NULL)
        is_parent = doc.parent_id is None
        
        # Collect all documents to delete
        docs_to_delete = [doc]
        
        if is_parent:
            # If it's a parent, also collect all children
            children = Document.query.filter_by(parent_id=doc.id).all()
            docs_to_delete.extend(children)
        
        # Delete all documents and their vectors from vector store
        if vector_store:
            for document in docs_to_delete:
                if document.vector_ids:
                    vector_store.delete_document_vectors(document.id)
            vector_store.persist()
        
        # Delete all collected documents from database
        for document in docs_to_delete:
            db.session.delete(document)
        db.session.commit()
        
        deleted_count = len(docs_to_delete)
        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} document(s)',
            'deleted_count': deleted_count
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/add-url-stream', methods=['POST'])
def api_add_url_stream():
    """Add document from URL with progress streaming"""
    data = request.get_json()
    user_id = data.get('user_id')
    url = data.get('url')
    
    if not user_id or not url:
        return jsonify({'success': False, 'error': 'Missing fields'}), 400
    
    if not is_valid_url(url):
        return jsonify({'success': False, 'error': 'Invalid URL'}), 400
    
    # Store progress events in session
    progress_events = []
    
    def progress_callback(event_type, event_data):
        """Callback to collect progress events"""
        progress_events.append({
            'type': event_type,
            'data': event_data
        })
        print(f"[Progress] {event_type}: {event_data}")
    
    try:
        # Scrape URL with progress tracking
        scrape_result = scrape_url(url, progress_callback=progress_callback)
        
        if not scrape_result.get('success'):
            return jsonify({
                'success': False,
                'error': scrape_result.get('error'),
                'progress': progress_events
            }), 400
        
        title = scrape_result['title']
        # Ensure title is never None or empty
        if not title:
            title = urlparse(url).netloc or "Webpage"
        
        # Get the MAIN URL content specifically (first in all_content), not merged
        url_grouped = scrape_result.get('url_grouped_content', {})
        urls_data = scrape_result.get('urls_data', [])
        
        # Get main URL content from grouped data
        main_content = None
        main_sections = None
        if urls_data and urls_data[0]['is_main']:
            main_url = urls_data[0]['url']
            if main_url in url_grouped:
                main_content = url_grouped[main_url]['content']
                # Get sections if available
                main_sections = url_grouped[main_url].get('sections')
        
        # Fallback to merged content if not found
        if not main_content:
            main_content = scrape_result['content']
            main_sections = scrape_result.get('sections')
        
        content = extract_meaningful_content(main_content)
        
        # Store URL-grouped content as JSON
        url_grouped_json = None
        if url_grouped:
            import json
            url_grouped_json = json.dumps(url_grouped)
        
        # Store MAIN URL document (parent_id = NULL)
        doc = Document(
            user_id=user_id,
            parent_id=None,  # Main URL has no parent
            title=title,
            source_type='url',
            source_url=url,
            content=content,
            url_grouped_content=url_grouped_json
        )
        db.session.add(doc)
        db.session.flush()  # Get the ID before committing
        main_doc_id = doc.id
        
        # Create child documents for related URLs
        for url_info in urls_data:
            if not url_info['is_main']:  # Skip main URL, only create for related
                if url_info['url'] in url_grouped:
                    url_content = url_grouped[url_info['url']]['content']
                    url_title = scrape_result['url_grouped_content'][url_info['url']]['title']
                    
                    child_doc = Document(
                        user_id=user_id,
                        parent_id=main_doc_id,  # Link to parent
                        title=url_title,
                        source_type='url',
                        source_url=url_info['url'],
                        content=extract_meaningful_content(url_content),
                        url_grouped_content=None  # Individual documents don't need grouped content
                    )
                    db.session.add(child_doc)
        
        db.session.commit()
        
        # Add main document to vector store
        if vector_store:
            try:
                vector_result = vector_store.add_document(
                    user_id, doc.id, title, content,
                    metadata={'source_url': url, 'type': 'main'},
                    sections=main_sections
                )
                if vector_result.get('success'):
                    doc.vector_ids = ','.join(vector_result['vector_ids'])
                    db.session.commit()
                    vector_store.persist()
                else:
                    print(f"Vector store error: {vector_result.get('error')}")
            except Exception as ve:
                print(f"Error adding to vector store: {ve}")
            
            # Add child documents to vector store
            for url_info in urls_data:
                if not url_info['is_main']:  # Only for children
                    if url_info['url'] in url_grouped:
                        child_content = url_grouped[url_info['url']]['content']
                        child_title = url_grouped[url_info['url']]['title']
                        child_sections = url_grouped[url_info['url']].get('sections')
                        
                        # Find the child doc we just created
                        child_doc = Document.query.filter_by(
                            parent_id=doc.id,
                            source_url=url_info['url']
                        ).first()
                        
                        if child_doc:
                            try:
                                child_vector_result = vector_store.add_document(
                                    user_id, child_doc.id, child_title, child_content,
                                    metadata={'source_url': url_info['url'], 'type': 'child', 'parent_id': doc.id},
                                    sections=child_sections
                                )
                                if child_vector_result.get('success'):
                                    child_doc.vector_ids = ','.join(child_vector_result['vector_ids'])
                                    db.session.commit()
                                    vector_store.persist()
                            except Exception as child_ve:
                                print(f"Error adding child doc {child_doc.id} to vector store: {child_ve}")
        
        return jsonify({
            'success': True,
            'message': f'Added: {title}',
            'document': doc.to_dict(),
            'urls_scraped': scrape_result.get('urls_scraped', 1),
            'related_urls': scrape_result.get('related_urls', []),
            'parent_id': doc.id,
            'progress': progress_events
        }), 200
    
    except Exception as e:
        db.session.rollback()
        print(f"Error in add-url-stream: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'progress': progress_events
        }), 400


@app.route('/api/add-url', methods=['POST'])
def api_add_url():
    """Add document from URL (legacy endpoint for backward compatibility)"""
    # For backward compatibility, this redirects to the new streaming endpoint
    # but only returns the final result without progress events
    data = request.get_json()
    user_id = data.get('user_id')
    url = data.get('url')
    
    if not user_id or not url:
        return jsonify({'success': False, 'error': 'Missing fields'}), 400
    
    if not is_valid_url(url):
        return jsonify({'success': False, 'error': 'Invalid URL'}), 400
    
    try:
        # Scrape URL without progress tracking
        scrape_result = scrape_url(url)
        if not scrape_result.get('success'):
            return jsonify(scrape_result), 400
        
        title = scrape_result['title']
        # Ensure title is never None or empty
        if not title:
            title = urlparse(url).netloc or "Webpage"
        
        content = extract_meaningful_content(scrape_result['content'])
        sections = scrape_result.get('sections')
        
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
                    metadata={'source_url': url},
                    sections=sections
                )
                if vector_result.get('success'):
                    doc.vector_ids = ','.join(vector_result['vector_ids'])
                    db.session.commit()
                    vector_store.persist()
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
        
        # Extract sections
        from processor import extract_logical_sections
        sections = extract_logical_sections(content)
        
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
                    metadata={'filename': filename},
                    sections=sections
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

def is_greeting(question):
    """Check if question is a greeting"""
    greetings = ['hello', 'hi', 'hii', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening', 'howdy', 'what can you do', 'help']
    question_lower = question.strip().lower()
    return any(question_lower.startswith(g) or question_lower == g for g in greetings)


def is_low_quality_chunk(text):
    """
    Detect and filter out low-quality chunks (contact info, footers, form fields).
    Returns True if chunk should be filtered out.
    VERY AGGRESSIVE filtering to keep only meaningful content.
    """
    text_lower = text.lower()
    
    # EMAIL DETECTION: Any chunk with email addresses
    if '@' in text and ('email' in text_lower or 'contact' in text_lower or 
                        text_lower.count('@') >= 1):
        return True
    
    # PHONE DETECTION: Phone numbers
    phone_patterns = [
        r'\+61',           # Australia +61
        r'\+1\s?\(',       # US +1 (
        r'\(\d{3}\)',      # (XXX) format
        r'\d{3}-\d{3}-\d{4}',  # XXX-XXX-XXXX
    ]
    import re
    for pattern in phone_patterns:
        if re.search(pattern, text):
            return True
    
    # FORM FIELD DETECTION: Onboarding forms, input fields
    form_keywords = [
        'first name', 'last name', 'middle name',
        'phone number', 'email address',
        'employment type',
        'onboarding form',
        'form submission',
        'submit button',
        'required field',
        'your message',
        'delta first',
    ]
    form_count = sum(1 for keyword in form_keywords if keyword in text_lower)
    if form_count >= 2:  # Need at least 2 form keywords
        return True
    
    # ADDRESS DETECTION: Office/address keywords
    address_keywords = [
        'office', 'level', 'street', 'avenue', 'road', 'floor',
        'suite', 'building', 'blvd', 'drive',
        'banks ave', 'eastgardens', 'ahmedabad', 'delhi',
        'sydney nsw', 'nsw 2000', 'toronto', 'vancouver',
        'epitome', 'makrba', 'vinayak tower'
    ]
    # If text looks like pure address (multiple address keywords, no real content)
    address_count = sum(1 for keyword in address_keywords if keyword in text_lower)
    if address_count >= 2:
        return True
    
    # CONTACT MARKER DETECTION
    contact_markers = [
        'contact us', 'contact info', 'get in touch', 'visit us',
        'our office', 'office location', 'office address',
        'privacy policy', 'terms of use', 'terms & conditions',
        'cookie policy', 'gdpr',
    ]
    contact_count = sum(1 for marker in contact_markers if marker in text_lower)
    if contact_count >= 1:
        return True
    
    # FOOTER DETECTION: Common footer phrases
    footer_keywords = [
        '© ', 'copyright', 'all rights reserved',
        'follow us', 'social media', 'facebook', 'instagram', 'linkedin',
        'designed by', 'powered by',
    ]
    footer_count = sum(1 for keyword in footer_keywords if keyword in text_lower)
    if footer_count >= 1:
        return True
    
    # CAREER/RECRUITMENT DETECTION: Job posting content
    # Check for "join ... team" pattern with flexible matching
    has_join = 'join' in text_lower
    has_team = 'team' in text_lower
    has_career_markers = any(kw in text_lower for kw in 
                            ['passionate', 'innovation', 'grow', 'opportunity', 'culture',
                             'apply now', 'employment type', 'full time', 'contract'])
    
    if has_join and has_team and has_career_markers:
        return True
    
    # NAVIGATION/HEADER DETECTION: Too short
    if len(text.strip()) < 30:
        return True
    
    # Pure navigation menus
    nav_keywords = ['home', 'about us', 'services', 'careers', 
                    'blog', 'resources', 'contact', 'login', 'sign up']
    nav_count = sum(1 for keyword in nav_keywords if keyword in text_lower)
    if nav_count >= 4 and len(text.split()) < 15:
        return True
    
    return False


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
    
    print(llm_model)
    
    if not user_id or not question:
        return jsonify({'success': False, 'error': 'user_id and question required'}), 400
    
    try:
        if not vector_store:
            return jsonify({'success': False, 'error': 'Vector store not available'}), 400
        
        # NEW: Check for greeting and provide context summary
        if is_greeting(question):
            summary_data = vector_store.generate_context_summary(user_id, doc_id)
            if summary_data:
                greeting_response = f"Hello! I can help you understand your organization. {summary_data['summary']} What would you like to know?"
                return jsonify({
                    'success': True,
                    'answer': greeting_response,
                    'has_context': True,
                    'provider': 'greeting-fallback',
                    'status': 'greeting'
                }), 200
        
        # If doc_id specified, verify it belongs to user and get its children
        doc_ids_to_search = None
        if doc_id:
            doc = Document.query.get(doc_id)
            if not doc or doc.user_id != user_id:
                return jsonify({'success': False, 'error': 'Document not found or access denied'}), 403
            
            # If main document (parent_id = null), include all children
            if doc.parent_id is None:
                # Get all children of this parent
                children = Document.query.filter_by(parent_id=doc_id).all()
                doc_ids_to_search = [doc_id] + [child.id for child in children]
            else:
                # If it's a child, search only that document
                doc_ids_to_search = [doc_id]
        
        # Search for relevant documents
        search_result = None
        if doc_ids_to_search:
            # Search within selected document + children
            # Need to search each doc_id and combine results
            all_results = []
            for search_doc_id in doc_ids_to_search:
                result = vector_store.search_documents(question, user_id, num_results=5, doc_id=search_doc_id)
                if result.get('success') and result.get('results'):
                    all_results.extend(result['results'])
            
            # Sort by distance (lower is better) and take top 5
            all_results.sort(key=lambda x: x.get('distance', float('inf')))
            search_result = {
                'success': True,
                'results': all_results[:5]  # Return top 5 combined results
            }
        else:
            # Search all user documents
            search_result = vector_store.search_documents(question, user_id, num_results=5)
        
        if not search_result.get('success'):
            return jsonify({
                'success': False,
                'error': 'Search failed'
            }), 500
        
        # If no results found, provide helpful response with context summary
        if not search_result.get('results'):
            summary_data = vector_store.generate_context_summary(user_id, doc_id)
            if summary_data:
                fallback_answer = f"I couldn't find specific information about that. {summary_data['summary']} Try asking about these topics: team members, services, pricing, or career opportunities."
            else:
                fallback_answer = 'I cannot find relevant information in the documents to answer your question. Please try asking about specific topics like teams, services, or company information.'
            
            return jsonify({
                'success': True,
                'answer': fallback_answer,
                'has_context': False,
                'provider': 'document-search',
                'status': 'no-results'
            }), 200
        
        # Extract document text from search results
        context_docs = [result['document'] for result in search_result['results']]
        
        # Organize by section if metadata available
        organized_context = []
        section_groups = {}
        
        for i, result in enumerate(search_result['results']):
            doc_text = result['document']
            
            metadata = result.get('metadata', {})
            section = metadata.get('section_name', 'General')
            subsection = metadata.get('subsection_name')
            
            # Group by section
            if section not in section_groups:
                section_groups[section] = []
            
            section_groups[section].append({
                'text': doc_text,
                'subsection': subsection
            })
        
        # Build organized context with section headers
        for section_name in sorted(section_groups.keys()):
            organized_context.append(f"[Section: {section_name}]")
            for item in section_groups[section_name]:
                if item['subsection']:
                    organized_context.append(f"  [{item['subsection']}]")
                organized_context.append(item['text'])
                organized_context.append("---")
        
        context_text = '\n'.join(organized_context) if organized_context else '\n'.join(context_docs)
        
        # Get chatbot and generate answer
        if use_llm:
            if chatbot:
                # Convert context_text back to list for compatibility
                context_list = [context_text]
                # Pass the selected model to the chatbot
                result = chatbot.generate_answer(question, context_list, user_id, llm_model=llm_model)
                
                # Log the result for debugging
                print(f"[CHAT] LLM Result - Provider: {result.get('provider')}, Status: {result.get('status')}")
                
                # If LLM failed with error status, provide intelligent fallback
                if result.get('status') == 'error':
                    print(f"[CHAT] LLM error detected, providing formatted document search fallback")
                    # Extract key information from context for better fallback
                    try:
                        # Parse the organized context to provide better answers
                        extracted_answer = extract_key_information(question, context_text)
                        result = {
                            'answer': extracted_answer,
                            'status': 'fallback-with-extraction',
                            'provider': 'document-search',
                            'sources': [c.get('metadata', {}).get('title', 'Unknown') for c in search_result['results'][:3]],
                            'model': llm_model
                        }
                    except:
                        # If extraction fails, use raw fallback
                        result = {
                            'answer': f"Based on the available information:\n\n{context_docs[0][:600]}...",
                            'status': 'fallback',
                            'provider': 'document-search',
                            'sources': [c.get('metadata', {}).get('title', 'Unknown') for c in search_result['results'][:3]],
                            'model': llm_model
                        }
            else:
                # Chatbot not initialized
                print(f"[CHAT] Chatbot not available, using document search")
                result = {
                    'answer': f"Here's relevant information:\n\n{context_docs[0][:500]}...",
                    'status': 'fallback-no-chatbot',
                    'provider': 'document-search',
                    'sources': [c.get('metadata', {}).get('title', 'Unknown') for c in search_result['results'][:3]],
                    'model': None
                }
        else:
            # Use document search only
            result = {
                'answer': context_docs[0][:500] + "..." if context_docs else "No content available",
                'status': 'document-search',
                'provider': 'document-search',
                'sources': [c.get('metadata', {}).get('title', 'Unknown') for c in search_result['results'][:3]],
                'model': None
            }
        
        return jsonify({
            'success': True,
            'answer': result.get('answer'),
            'provider': result.get('provider', 'unknown'),
            'status': result.get('status', 'success'),
            'sources': result.get('sources', []),
            'model': result.get('model') or llm_model  # Ensure model is always returned
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
