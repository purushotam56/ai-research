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
    
    def chunk_by_sections(self, sections):
        """
        Create chunks from hierarchical sections data.
        Each section (or subsection) becomes a single chunk, preserving relationships.
        
        Args:
            sections: list of dicts with {section_name, subsection_name, content}
        
        Returns: list of dicts with {content, section_name, subsection_name}
        """
        chunks = []
        
        for section_data in sections:
            if section_data.get('content', '').strip():
                chunks.append({
                    'content': section_data['content'],
                    'section_name': section_data.get('section_name'),
                    'subsection_name': section_data.get('subsection_name')
                })
        
        return chunks
    
    def chunk_text(self, text, chunk_size=500, overlap=50):
        """
        Split text into semantic chunks for better vector embedding.
        - Breaks team/people sections into individual entries
        - Keeps other sections intact for context
        - Returns smaller, more focused chunks
        """
        chunks = []
        
        # Split by double newlines (paragraph breaks)
        paragraphs = text.split('\n\n')
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # Check if this is a team member line (format: Name + Role)
            # Typically: "Name\nRole, Location" or similar
            is_person_entry = self._is_person_entry(para)
            
            if is_person_entry:
                # Individual person entries should be their own chunk
                # This makes "dhruv" search return specific person info
                if current_chunk:
                    # Save any accumulated context
                    chunk_text = '\n\n'.join(current_chunk)
                    if chunk_text.strip():
                        chunks.append(chunk_text)
                    current_chunk = []
                    current_size = 0
                
                # Add the person entry as a separate chunk
                if para.strip():
                    chunks.append(para)
            else:
                # For non-person content, use normal chunking
                if current_size + para_size > chunk_size and current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    if chunk_text.strip():
                        chunks.append(chunk_text)
                    current_chunk = [para]
                    current_size = para_size
                else:
                    current_chunk.append(para)
                    current_size += para_size
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            if chunk_text.strip():
                chunks.append(chunk_text)
        
        # Fallback: if no good chunks created, use word-based chunking
        if not chunks:
            chunks = self._chunk_by_words(text, chunk_size, overlap)
        
        return chunks
    
    def _is_person_entry(self, text: str) -> bool:
        """
        Detect if a text block is a person entry (name + role).
        Patterns:
        - "Name\nRole, Location"
        - "Role\nName"
        - Single line with name-like pattern
        """
        if not text or len(text.strip()) < 3:
            return False
        
        lines = text.strip().split('\n')
        
        # Person entries typically have 1-3 lines
        if len(lines) > 3:
            return False
        
        # Look for role keywords
        role_keywords = [
            'manager', 'engineer', 'architect', 'developer', 'consultant',
            'director', 'lead', 'specialist', 'officer', 'executive',
            'coordinator', 'associate', 'recruiter', 'designer', 'analyst',
            'team', 'sr.', 'jr.', 'head', 'chief', 'vice'
        ]
        
        text_lower = text.lower()
        has_role = any(role in text_lower for role in role_keywords)
        
        # Person entries typically have 2+ words (name + role)
        word_count = len(text_lower.split())
        
        return has_role and word_count >= 2
    
    def _chunk_by_words(self, text, chunk_size=500, overlap=50):
        """
        Fallback: Split text into chunks by word count.
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
    
    def generate_context_summary(self, user_id=None, doc_id=None):
        """
        Generate a brief summary of available context (company info, teams, etc).
        Used to greet users and explain what information is available.
        """
        try:
            # Build filter
            where_filter = None
            if user_id and doc_id:
                where_filter = {
                    '$and': [
                        {'user_id': {'$eq': str(user_id)}},
                        {'document_id': {'$eq': str(doc_id)}}
                    ]
                }
            elif user_id:
                where_filter = {'user_id': {'$eq': str(user_id)}}
            elif doc_id:
                where_filter = {'document_id': {'$eq': str(doc_id)}}
            
            # Get all documents in collection
            all_docs = self.collection.get(where=where_filter) if where_filter else self.collection.get()
            
            if not all_docs or not all_docs['ids']:
                return None
            
            # Extract unique metadata and documents
            metadata_list = all_docs.get('metadatas', [])
            documents = all_docs.get('documents', [])
            titles = set()
            companies = set()
            has_team_info = False
            has_services = False
            has_pricing = False
            has_careers = False
            
            # Check metadata AND document content for better detection
            for i, meta in enumerate(metadata_list):
                if meta:
                    title = meta.get('title', '').lower()
                    titles.add(title)
                    
                    # Check title
                    if 'team' in title or 'leadership' in title or 'management' in title or 'about' in title:
                        has_team_info = True
                    if 'service' in title or 'solution' in title:
                        has_services = True
                    if 'price' in title or 'pricing' in title:
                        has_pricing = True
                    if 'career' in title or 'job' in title or 'recruitment' in title:
                        has_careers = True
                
                # Also check document content for keyword indicators
                if i < len(documents):
                    doc_content = (documents[i] or '').lower()
                    if doc_content:
                        if 'team' in doc_content or 'founder' in doc_content or 'director' in doc_content or 'manager' in doc_content:
                            has_team_info = True
                        if 'service' in doc_content or 'solution' in doc_content:
                            has_services = True
                        if 'price' in doc_content or 'pricing' in doc_content or 'cost' in doc_content:
                            has_pricing = True
                        if 'career' in doc_content or 'join us' in doc_content or 'hiring' in doc_content:
                            has_careers = True
            
            # Generate summary
            summary_parts = []
            
            if has_team_info:
                summary_parts.append("information about team members and their roles")
            if has_services:
                summary_parts.append("details about services and solutions")
            if has_pricing:
                summary_parts.append("pricing information")
            if has_careers:
                summary_parts.append("career opportunities")
            
            if summary_parts:
                summary = "I have access to " + ", ".join(summary_parts) + "."
                return {
                    'summary': summary,
                    'has_team_info': has_team_info,
                    'has_services': has_services,
                    'has_pricing': has_pricing,
                    'has_careers': has_careers,
                    'doc_count': len(set(meta.get('document_id') for meta in metadata_list if meta))
                }
            
            return None
            
        except Exception as e:
            return None
    
    def add_document(self, user_id, document_id, title, content, metadata=None, sections=None):
        """
        Add document to vector store.
        If sections provided, uses section-based chunking (preserves hierarchy).
        Otherwise uses character-based chunking.
        Returns list of vector IDs created.
        """
        try:
            # Determine chunking strategy
            if sections and isinstance(sections, list) and len(sections) > 0:
                # Use section-based chunking
                chunks_data = self.chunk_by_sections(sections)
            else:
                # Fallback to character-based chunking
                chunks_data = [{'content': chunk} for chunk in self.chunk_text(content)]
            
            if not chunks_data:
                return {'success': False, 'error': 'No content to chunk'}
            
            vector_ids = []
            
            # Add each chunk with metadata
            for idx, chunk_info in enumerate(chunks_data):
                chunk_id = f"{document_id}_chunk_{idx}"
                chunk_content = chunk_info.get('content') if isinstance(chunk_info, dict) else chunk_info
                
                # Prepare metadata
                chunk_metadata = {
                    'user_id': str(user_id),
                    'document_id': str(document_id),
                    'title': title,
                    'chunk_index': idx,
                    'chunk_count': len(chunks_data)
                }
                
                # Add section information if available
                if isinstance(chunk_info, dict):
                    if chunk_info.get('section_name'):
                        chunk_metadata['section_name'] = chunk_info['section_name']
                    if chunk_info.get('subsection_name'):
                        chunk_metadata['subsection_name'] = chunk_info['subsection_name']
                
                if metadata:
                    chunk_metadata.update(metadata)
                
                # Add to ChromaDB
                self.collection.add(
                    ids=[chunk_id],
                    documents=[chunk_content],
                    metadatas=[chunk_metadata]
                )
                
                vector_ids.append(chunk_id)
            
            return {
                'success': True,
                'vector_ids': vector_ids,
                'num_chunks': len(chunks_data),
                'message': f'Document added with {len(chunks_data)} chunks'
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def search_documents(self, query, user_id=None, num_results=5, doc_id=None):
        """
        Search documents by query with semantic + keyword fallback + team-aware search.
        If user_id provided, search only user's documents.
        If doc_id provided, search only within that document.
        Returns list of matching documents with scores.
        """
        try:
            # Use only the original query for initial search
            enhanced_queries = [query]
            query_lower = query.lower()
            
            # Build where filter for user if specified
            where_filter = None
            if user_id and doc_id:
                # When a parent doc_id is selected, search parent + all children
                # Metadata includes 'parent_id' (int) for child documents and 'document_id' (str) for all
                where_filter = {
                    '$and': [
                        {'user_id': {'$eq': str(user_id)}},
                        {'$or': [
                            {'document_id': {'$eq': str(doc_id)}},
                            {'parent_id': {'$eq': int(doc_id)}}  # parent_id is stored as int
                        ]}
                    ]
                }
            elif user_id:
                # Filter by user only
                where_filter = {'user_id': {'$eq': str(user_id)}}
            elif doc_id:
                # Filter by document only - include parent and children
                where_filter = {
                    '$or': [
                        {'document_id': {'$eq': str(doc_id)}},
                        {'parent_id': {'$eq': int(doc_id)}}  # parent_id is stored as int
                    ]
                }
            
            # Semantic search with enhanced queries
            all_formatted_results = []
            for search_query in enhanced_queries:
                results = self.collection.query(
                    query_texts=[search_query],
                    n_results=num_results * 3,  # Get more results for better filtering
                    where=where_filter
                )
                
                if not results or not results['ids'] or len(results['ids'][0]) == 0:
                    continue
                
                # Format results
                for i, doc_id_result in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i]
                    
                    all_formatted_results.append({
                        'id': doc_id_result,
                        'document': results['documents'][0][i],
                        'metadata': metadata,
                        'distance': results['distances'][0][i] if results['distances'] else None,
                        'query': search_query
                    })
            
            if not all_formatted_results:
                return {'success': True, 'results': []}
            
            # Remove duplicates, keeping lowest distance
            seen_ids = {}
            formatted_results = []
            for result in all_formatted_results:
                result_id = result['id']
                if result_id not in seen_ids or result['distance'] < seen_ids[result_id]['distance']:
                    seen_ids[result_id] = result
            
            formatted_results = list(seen_ids.values())
            
            # Also remove near-duplicate content (same text from different chunks)
            seen_documents = {}
            deduplicated_results = []
            for result in formatted_results:
                doc_text = result['document'][:100]  # First 100 chars as unique key
                if doc_text not in seen_documents:
                    seen_documents[doc_text] = True
                    deduplicated_results.append(result)
            
            formatted_results = deduplicated_results
            
            # Enhanced keyword matching with relevance scoring
            keywords = [word for word in query_lower.split() if len(word) > 2]  # Skip short words
            
            # Score results based on keyword presence and context
            for result in formatted_results:
                doc_text = result['document'].lower()
                keyword_matches = sum(1 for kw in keywords if kw in doc_text)
                
                # Calculate relevance score
                relevance_score = 0
                
                if keyword_matches > 0:
                    result['keyword_bonus'] = keyword_matches
                    # Strong keyword match: check if it's an exact phrase/person name context
                    # e.g., "Dhruv Bhatt", "Dhruv Manager", etc.
                    for kw in keywords:
                        if kw in doc_text:
                            # Check if keyword is near role/position keywords
                            context_window = doc_text.find(kw) + len(kw) + 50
                            role_keywords = ['manager', 'engineer', 'architect', 'developer', 'consultant', 
                                            'director', 'team', 'lead', 'specialist', 'officer', 'officer',
                                            'executive', 'coordinator', 'associate', 'recruiter', 'designer']
                            context = doc_text[max(0, doc_text.find(kw)-30):context_window]
                            if any(role in context for role in role_keywords):
                                relevance_score += 2  # High relevance for person with role context
                            else:
                                relevance_score += 1
                    
                    # Apply keyword boost (reduce distance)
                    result['distance'] = max(0, result['distance'] - (keyword_matches * 0.15))
                    result['relevance_score'] = relevance_score
                else:
                    result['relevance_score'] = 0
            
            # Sort by: relevance_score (desc), then distance (asc)
            formatted_results.sort(key=lambda x: (-x.get('relevance_score', 0), x.get('distance', float('inf'))))
            
            # Filter by relevance threshold - more lenient for exact keyword matches
            # Distance in ChromaDB: 0 = identical, 1 = completely different
            # For keyword matches with role context, accept higher distances
            relevant_results = []
            for r in formatted_results:
                distance = r.get('distance', 1.0)
                relevance = r.get('relevance_score', 0)
                
                # Accept results that meet either criterion:
                # 1. Very high semantic similarity (distance < 0.4) OR
                # 2. Good keyword match with role context (relevance_score >= 2 and distance < 0.85)
                if distance < 0.4 or (relevance >= 2 and distance < 0.85):
                    relevant_results.append(r)
            
            # If we have relevant results, use them
            if relevant_results:
                return {'success': True, 'results': relevant_results[:num_results]}
            
            # If no highly relevant results found, return best semantic matches with lower threshold
            # This handles edge cases where keyword context is poor but semantic similarity exists
            fallback_results = [r for r in formatted_results if r.get('distance', 1.0) < 0.95]
            
            if fallback_results:
                return {'success': True, 'results': fallback_results[:num_results]}
            
            # Return best matches anyway (even if below threshold) rather than nothing
            return {'success': True, 'results': formatted_results[:num_results]}
        
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
