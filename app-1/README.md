# RAG Document Manager - Flask + Gradio

A Flask-based application with Gradio interface for managing documents with vector database storage. Perfect for building RAG (Retrieval-Augmented Generation) systems.

## Features

✅ **User Authentication**
- Register new users with email validation
- Secure login with password hashing
- SQLite-based user management

✅ **Document Management**
- Add documents from URLs (web scraping)
- Upload local files (PDF, TXT, Markdown)
- Automatic content extraction and cleaning
- Meaningful data extraction from web pages

✅ **Vector Database**
- ChromaDB for vector storage
- Sentence-Transformers for embeddings
- Semantic search across documents
- Persistent storage with automatic chunking

✅ **User Interfaces**
- **Gradio UI**: Interactive web interface for all features
- **Flask REST API**: For programmatic access

## Setup Instructions

### Step 1: Create Virtual Environment

```bash
cd app-1
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- Flask & Flask-CORS: Web framework and CORS support
- SQLAlchemy: ORM for database
- Gradio: Interactive UI
- ChromaDB: Vector database
- BeautifulSoup4: Web scraping
- sentence-transformers: Text embeddings
- PyPDF: PDF text extraction
- And other supporting libraries

### Step 3: Initialize Database

```bash
python3 -c "from app import app; from database import db; app.app_context().push(); db.create_all(); print('✓ Database initialized')"
```

### Step 4: Run the Application

```bash
python3 app.py
```

The application will start with:
- **Gradio Interface**: http://127.0.0.1:7860
- **Flask API**: http://127.0.0.1:5000

## Project Structure

```
app-1/
├── app.py                 # Main Flask + Gradio application
├── database.py            # SQLAlchemy models (User, Document)
├── auth.py                # Authentication functions
├── processor.py           # URL scraping & file processing
├── vector_store.py        # ChromaDB wrapper for vector operations
├── requirements.txt       # Python dependencies
├── uploads/               # Temporary file storage
├── vector_db/             # ChromaDB persistent storage
└── app.db                 # SQLite database
```

## Usage Guide

### 1. Register & Login
- Go to **Authentication** tab
- Register with username, email, password
- Login to get your User ID (you'll need this for other operations)

### 2. Add Data

#### From URL:
- Go to **Add Data** tab
- Enter URL in "Add from URL" section
- The system will:
  - Fetch the webpage
  - Extract meaningful content
  - Clean and parse text
  - Store in database
  - Create vector embeddings

#### Upload File:
- Go to **Add Data** tab
- Upload PDF, TXT, or Markdown file
- The system will:
  - Extract text content
  - Process and clean content
  - Store in database
  - Create vector embeddings

### 3. View Documents
- Go to **My Documents** tab
- Enter your User ID
- See all documents you've added with timestamps

### 4. Search
- Go to **Search** tab
- Enter your User ID and search query
- Get semantically similar results across all your documents
- Results show document title, chunk, and preview

## API Endpoints

### Authentication
```bash
# Register
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","email":"user@example.com","password":"pass123"}'

# Login
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","password":"pass123"}'
```

### Documents
```bash
# Get user's documents
curl http://localhost:5000/api/documents/1

# Get specific document
curl http://localhost:5000/api/documents/1

# Get user info
curl http://localhost:5000/api/user/1
```

### Search
```bash
# Search documents
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"your search query","user_id":1,"num_results":5}'
```

## Database Schema

### Users Table
- `id`: Primary key
- `username`: Unique username
- `email`: Unique email
- `password_hash`: Hashed password
- `created_at`: Registration timestamp

### Documents Table
- `id`: Primary key
- `user_id`: Foreign key to user
- `title`: Document title
- `source_type`: 'url' or 'file'
- `source_url`: Original URL (if from web)
- `filename`: Filename (if uploaded)
- `content`: Processed document content
- `vector_ids`: Comma-separated ChromaDB chunk IDs
- `created_at`/`updated_at`: Timestamps

## Vector Store Details

### Chunking Strategy
- Text split into 500-character chunks
- 50-character overlap between chunks
- Each chunk gets unique embedding
- Metadata stored with each chunk

### Embedding Model
- **Model**: `all-MiniLM-L6-v2`
- **Dimensions**: 384-dimensional vectors
- **Performance**: Fast, accurate for semantic search

### Persistence
- ChromaDB uses DuckDB + Parquet format
- Vectors stored in `vector_db/` directory
- Automatic persistence after document addition

## Next Steps: RAG Integration

To add RAG capabilities:

1. **Add LLM Integration**
   - Install OpenAI/other LLM SDK
   - Create `llm.py` module for API calls

2. **Create RAG Pipeline**
   - Use search results as context
   - Send to LLM with user question
   - Return enriched answer

3. **Build Chat Interface**
   - Add chat tab to Gradio
   - Maintain conversation history
   - Display retrieved documents

## Troubleshooting

### ChromaDB Issues
```bash
# Reset vector database
rm -rf vector_db/
```

### Database Issues
```bash
# Reset SQLite database
rm app.db
python3 -c "from app import app; from database import db; app.app_context().push(); db.create_all()"
```

### Dependency Issues
```bash
# Reinstall all packages
pip install -r requirements.txt --force-reinstall
```

### Port Already in Use
```bash
# Change port in app.py:
# gradio_interface.launch(server_port=7861)  # or any other port
```

## Performance Tips

- **For large files**: Processing may take time, be patient
- **For many documents**: Search returns top 5 by default, adjustable
- **Vector DB size**: Grows with document count, currently unrestricted
- **Chunk overlap**: Increases storage but improves search relevance

## Security Notes

- Passwords are hashed using Werkzeug's secure hash
- SQLite suitable for development, use PostgreSQL for production
- Add authentication headers for API access in production
- Validate file uploads and URLs carefully

## Dependencies Overview

| Package | Purpose |
|---------|---------|
| Flask | Web framework |
| SQLAlchemy | Database ORM |
| Gradio | Interactive UI |
| ChromaDB | Vector database |
| BeautifulSoup4 | Web scraping |
| sentence-transformers | Text embeddings |
| PyPDF | PDF extraction |
| requests | HTTP requests |
| python-dotenv | Environment variables |

## Future Enhancements

- [ ] RAG query interface with LLM
- [ ] Multi-user collaboration
- [ ] Document versioning
- [ ] Advanced filtering options
- [ ] API key authentication
- [ ] Batch document processing
- [ ] Custom embedding models
- [ ] Cost tracking for LLM usage
