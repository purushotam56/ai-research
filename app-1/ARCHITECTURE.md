# RAG Document Manager - Architecture & Implementation Guide

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Gradio Web Interface                      │
│  (Authentication, Upload, Search, Document Management)       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Flask Backend (app.py)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  REST API Endpoints                                  │   │
│  │  /api/register  /api/login  /api/documents          │   │
│  │  /api/search    /api/user   /api/documents/{id}     │   │
│  └──────────────────────────────────────────────────────┘   │
└──────┬──────────────────────────┬──────────────────────┬─────┘
       │                          │                      │
       ▼                          ▼                      ▼
┌─────────────────┐    ┌──────────────────┐   ┌──────────────────┐
│  SQLite DB      │    │  Vector Store    │   │  File Processor  │
│  (app.db)       │    │  (ChromaDB)      │   │  (uploads/)      │
│  - Users        │    │  - Document      │   │  - PDF files     │
│  - Documents    │    │    embeddings    │   │  - Text files    │
│  - Auth         │    │  - Similarity    │   │  - URL scraping  │
│                 │    │    search        │   │                  │
└─────────────────┘    └──────────────────┘   └──────────────────┘
```

## 📁 File Descriptions

### Core Application Files

#### `app.py` (500+ lines)
**Main application file that ties everything together**
- Flask app initialization with CORS support
- Database initialization
- REST API endpoints for auth and data management
- Gradio interface with 5 tabs:
  1. **Authentication Tab**: Register & Login
  2. **Add Data Tab**: URL scraping & File upload
  3. **My Documents Tab**: View uploaded documents
  4. **Search Tab**: Vector similarity search
  5. **Info Tab**: Help & documentation

**Key Classes/Functions**:
- `gradio_login()`: Handle user login
- `gradio_register()`: Handle user registration
- `gradio_add_url()`: Scrape and store URL content
- `gradio_upload_file()`: Process uploaded files
- `gradio_list_documents()`: Show user's documents
- `gradio_search()`: Search using vector similarity

#### `database.py` (60 lines)
**SQLAlchemy ORM models for SQLite**
- `User` model:
  - username, email, password_hash
  - Password hashing with Werkzeug
  - Relationship to documents

- `Document` model:
  - title, source_type (url/file), content
  - source_url, filename, created_at/updated_at
  - vector_ids for ChromaDB references

#### `auth.py` (60 lines)
**User authentication functions**
- `validate_email()`: Email format validation
- `validate_password()`: Password strength check
- `register_user()`: Create new user with validation
- `login_user()`: Authenticate user credentials
- `get_user_by_id()`: Retrieve user information

#### `processor.py` (140 lines)
**Document processing and content extraction**
- `scrape_url()`: Fetch web pages and extract content
  - Uses BeautifulSoup4
  - Removes scripts/styles
  - Cleans whitespace
  - Extracts main content intelligently

- `process_pdf_file()`: Extract text from PDFs
  - Uses PyPDF2
  - Extracts all pages
  - Preserves structure

- `process_text_file()`: Read text/markdown files
  - UTF-8 encoding
  - Direct content reading

- `extract_meaningful_content()`: Clean extracted text
  - Removes empty lines
  - Filters short noise
  - Optional length limiting

#### `vector_store.py` (170 lines)
**ChromaDB vector database wrapper**
- `VectorStore` class:
  - Initialize ChromaDB with persistence
  - Sentence-Transformers for embeddings

- **Key Methods**:
  - `add_document()`: Create embeddings for document chunks
  - `search_documents()`: Find similar documents by query
  - `delete_document_vectors()`: Remove document embeddings
  - `chunk_text()`: Split text into manageable chunks
  - `persist()`: Save to disk

### Configuration & Setup Files

#### `requirements.txt`
13 Python packages with pinned versions:
- Web Framework: Flask, Flask-CORS, Werkzeug
- Database: Flask-SQLAlchemy
- UI: Gradio
- Web Scraping: requests, BeautifulSoup4, lxml
- Vector DB: ChromaDB, sentence-transformers
- File Processing: PyPDF
- Utilities: python-dotenv, python-multipart

#### `setup.sh` (Bash Script)
Automated setup script that:
1. Checks Python 3 installation
2. Creates virtual environment
3. Installs all dependencies
4. Initializes SQLite database
5. Displays startup instructions

#### `test_setup.sh` (Bash Script)
Verification script that tests:
- All package imports
- Database connectivity
- User model functionality
- Password hashing

#### `install_deps.py` (Python Script)
User-friendly dependency installer with:
- Python version checking
- Progressive package installation
- Error reporting
- Success summary

#### `.env.example`
Environment variables template for configuration

#### `README.md`
Comprehensive documentation covering:
- Features overview
- Setup instructions
- Usage guide
- API endpoints
- Database schema
- Troubleshooting

#### `COMMANDS.md`
Quick reference guide with all commands to run

## 🔄 Workflow Flowchart

```
User Registration
    │
    ├─→ Register Form
    │   ├─→ Validate Input
    │   ├─→ Hash Password
    │   └─→ Store in SQLite
    │
    └─→ Success/Error Response

User Login
    │
    ├─→ Login Form
    │   ├─→ Find User
    │   ├─→ Check Password
    │   └─→ Return User ID
    │
    └─→ Session/Token

Add Document (URL)
    │
    ├─→ Validate URL
    ├─→ Scrape Content
    │   ├─→ Fetch HTML
    │   ├─→ Parse with BeautifulSoup
    │   └─→ Extract Text
    ├─→ Clean Content
    ├─→ Store in SQLite
    ├─→ Create Embeddings
    │   ├─→ Split into Chunks
    │   ├─→ Generate Vectors
    │   └─→ Store in ChromaDB
    │
    └─→ Confirm Document Added

Add Document (File Upload)
    │
    ├─→ Validate File Type
    ├─→ Save Temporarily
    ├─→ Extract Content
    │   ├─→ PDF: Use PyPDF2
    │   ├─→ TXT/MD: Read Raw
    │   └─→ Clean Text
    ├─→ Store in SQLite
    ├─→ Create Embeddings
    │   ├─→ Split into Chunks
    │   ├─→ Generate Vectors
    │   └─→ Store in ChromaDB
    ├─→ Delete Temp File
    │
    └─→ Confirm Document Added

Search Documents
    │
    ├─→ User Query
    ├─→ Generate Query Embedding
    ├─→ Search ChromaDB
    │   ├─→ Find Similar Vectors
    │   ├─→ Filter by User ID
    │   └─→ Return Top 5 Results
    ├─→ Format Results
    │   ├─→ Show Document Title
    │   ├─→ Show Chunk Preview
    │   └─→ Show Relevance Score
    │
    └─→ Display Results
```

## 🗄️ Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Documents Table
```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL FOREIGN KEY,
    title VARCHAR(255) NOT NULL,
    source_type VARCHAR(20) NOT NULL,  -- 'url' or 'file'
    source_url VARCHAR(500),
    filename VARCHAR(255),
    content TEXT NOT NULL,
    content_summary TEXT,
    vector_ids VARCHAR(500),  -- comma-separated ChromaDB IDs
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 🔐 Security Features

1. **Password Security**
   - Werkzeug's `generate_password_hash()` with salt
   - PBKDF2 algorithm
   - Variable-length salts

2. **Input Validation**
   - Email format validation with regex
   - Username length requirements (3+ chars)
   - Password strength (6+ chars)
   - File upload restrictions

3. **CORS Protection**
   - Flask-CORS enabled
   - Configurable origins

4. **SQL Injection Prevention**
   - SQLAlchemy ORM prevents injection
   - Parameterized queries

## 📊 Chunking & Embedding Strategy

### Text Chunking
- **Chunk Size**: 500 characters
- **Overlap**: 50 characters (for context)
- **Purpose**: Fit into embedding model limits

### Embedding Model
- **Model**: `all-MiniLM-L6-v2`
- **Dimensions**: 384-D vectors
- **Optimized for**: Semantic search, speed
- **Performance**: ~10ms per embedding

### Vector Storage
- **ChromaDB Collections**: 1 per app
- **Metadata per chunk**:
  - user_id (for filtering)
  - document_id (trace back to source)
  - title (for display)
  - chunk_index (sequential)
  - source_url or filename

## 🚀 Deployment Considerations

### Current Setup (Development)
- Single-threaded Flask
- SQLite (suitable for ~1000 users)
- In-memory Gradio
- Local ChromaDB

### Production Recommendations
1. **Replace Flask with Gunicorn**
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. **Use PostgreSQL**
   ```python
   DATABASE_URL = 'postgresql://user:pass@host/dbname'
   ```

3. **Deploy Vector DB**
   - Use Chroma Cloud or self-hosted
   - Or: Pinecone, Weaviate, Milvus

4. **Use Nginx as Reverse Proxy**
   - Load balancing
   - SSL termination

5. **Docker Containerization**
   ```dockerfile
   FROM python:3.10-slim
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["gunicorn", "-w", "4", "app:app"]
   ```

## 📈 Scaling Considerations

| Component | Bottleneck | Solution |
|-----------|-----------|----------|
| SQLite | Concurrent writes | PostgreSQL/MySQL |
| ChromaDB | Local storage | Pinecone/Cloud |
| Flask | Single process | Gunicorn + Nginx |
| Embeddings | Compute | GPU acceleration |
| Gradio | Local interface | Separate UI server |

## 🔄 Future Enhancements

1. **LLM Integration** (Phase 2)
   - Add LLM query handler
   - Create RAG pipeline
   - Add chat interface

2. **Advanced Features**
   - Document versioning
   - Collaborative sharing
   - Batch processing
   - Custom embeddings
   - Fine-tuned models

3. **Performance**
   - Caching layer (Redis)
   - Async processing (Celery)
   - Lazy loading
   - Query optimization

4. **Analytics**
   - Search analytics
   - Usage statistics
   - Performance monitoring
   - Cost tracking

## 💾 File Structure After Complete Setup

```
app-1/
├── app.py                    # Main application (600+ lines)
├── database.py               # ORM models (60 lines)
├── auth.py                   # Authentication (60 lines)
├── processor.py              # File/URL processing (140 lines)
├── vector_store.py           # Vector DB wrapper (170 lines)
│
├── requirements.txt          # Python dependencies
├── setup.sh                  # Automated setup script
├── test_setup.sh             # Test verification script
├── install_deps.py           # Dependency installer
│
├── README.md                 # Full documentation
├── COMMANDS.md               # Command reference
├── .env.example              # Configuration template
│
├── venv/                     # Virtual environment (created after setup)
├── app.db                    # SQLite database (created on first run)
├── uploads/                  # Temporary file storage
└── vector_db/                # ChromaDB storage (created on first run)
```

## 📞 Support & Troubleshooting

For common issues, see `COMMANDS.md` and `README.md`.

Key commands:
- Setup: `./setup.sh`
- Run: `python3 app.py`
- Test: `./test_setup.sh`
- Reset: `rm -rf app.db vector_db/`

---

**Version**: 1.0  
**Last Updated**: October 2025  
**Status**: Production Ready (for single-user development)
