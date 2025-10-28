import chromadb
from chromadb.config import Settings
import os
from sentence_transformers import SentenceTransformer
import uuid

class VectorStore:
    def __init__(self, persist_dir='./vector_db'):
        """Initialize ChromaDB vector store"""
        self.persist_dir = persist_dir
        
        # Create persistence directory
        os.makedirs(persist_dir, exist_ok=True)
        
        # Initialize ChromaDB with new API
        self.client = chromadb.PersistentClient(path=persist_dir)
        
        # Get or create collection for all documents
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def chunk_text(self, text, chunk_size=500, overlap=50):
        """
        Split text into chunks for better vector embedding.
        Returns list of chunks.
        """
        chunks = []
        words = text.split()
        chunk_words = []
        
        for word in words:
            chunk_words.append(word)
            
            # Create chunk when reaching size
            if len(' '.join(chunk_words)) > chunk_size:
                chunk = ' '.join(chunk_words)
                chunks.append(chunk)
                
                # Keep overlap (overlap is number of chars, convert to word count)
                overlap_word_count = max(1, overlap // 5) if overlap else 0
                chunk_words = chunk_words[-overlap_word_count:] if overlap_word_count > 0 else []
        
        # Add remaining
        if chunk_words:
            chunks.append(' '.join(chunk_words))
        
        return chunks
    
    def add_document(self, user_id, document_id, title, content, metadata=None):
        """
        Add document to vector store.
        Returns list of vector IDs created.
        """
        try:
            # Chunk the content
            chunks = self.chunk_text(content)
            
            if not chunks:
                return {'success': False, 'error': 'No content to chunk'}
            
            vector_ids = []
            
            # Add each chunk with metadata
            for idx, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{idx}"
                
                # Prepare metadata
                chunk_metadata = {
                    'user_id': str(user_id),
                    'document_id': str(document_id),
                    'title': title,
                    'chunk_index': idx,
                    'chunk_count': len(chunks)
                }
                
                if metadata:
                    chunk_metadata.update(metadata)
                
                # Add to ChromaDB
                self.collection.add(
                    ids=[chunk_id],
                    documents=[chunk],
                    metadatas=[chunk_metadata]
                )
                
                vector_ids.append(chunk_id)
            
            return {
                'success': True,
                'vector_ids': vector_ids,
                'num_chunks': len(chunks),
                'message': f'Document added with {len(chunks)} chunks'
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def search_documents(self, query, user_id=None, num_results=5, doc_id=None):
        """
        Search documents by query.
        If user_id provided, search only user's documents.
        If doc_id provided, search only within that document.
        Returns list of matching documents with scores.
        """
        try:
            # Build where filter for user if specified
            where_filter = None
            if user_id and doc_id:
                # Filter by both user and specific document
                where_filter = {
                    '$and': [
                        {'user_id': {'$eq': str(user_id)}},
                        {'document_id': {'$eq': str(doc_id)}}
                    ]
                }
            elif user_id:
                # Filter by user only
                where_filter = {'user_id': {'$eq': str(user_id)}}
            elif doc_id:
                # Filter by document only
                where_filter = {'document_id': {'$eq': str(doc_id)}}
            
            # Search
            results = self.collection.query(
                query_texts=[query],
                n_results=num_results,
                where=where_filter
            )
            
            if not results or not results['ids'] or len(results['ids'][0]) == 0:
                return {'success': True, 'results': []}
            
            # Format results
            formatted_results = []
            for i, doc_id_result in enumerate(results['ids'][0]):
                formatted_results.append({
                    'id': doc_id_result,
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results['distances'] else None
                })
            
            return {'success': True, 'results': formatted_results}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_document_vectors(self, document_id):
        """Delete all vectors for a document"""
        try:
            # Query all chunks for this document
            results = self.collection.get(
                where={'document_id': {'$eq': str(document_id)}}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                return {
                    'success': True,
                    'deleted_count': len(results['ids']),
                    'message': f'Deleted {len(results["ids"])} vectors'
                }
            
            return {'success': True, 'deleted_count': 0, 'message': 'No vectors found'}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_document_vectors(self, document_id):
        """Get all vectors for a document"""
        try:
            results = self.collection.get(
                where={'document_id': {'$eq': str(document_id)}}
            )
            
            return {
                'success': True,
                'vectors': results['ids'],
                'count': len(results['ids'])
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def persist(self):
        """Persist the vector store to disk"""
        try:
            self.client.persist()
            return {'success': True, 'message': 'Vector store persisted'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
