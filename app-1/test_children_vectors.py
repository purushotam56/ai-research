#!/usr/bin/env python3
"""Test that children documents are now in vector store and searchable"""

from database import db, Document
from vector_store import VectorStore
from app_new import app
import os

with app.app_context():
    print("=" * 70)
    print("TESTING CHAT FOR TEAM INFORMATION")
    print("=" * 70)
    
    user_id = 1
    question = "Who is Jeet Bhatt?"
    doc_id = 1
    
    print(f"\nQuery: {question}")
    print(f"Document: {doc_id}")
    
    # Get parent and children
    parent_doc = Document.query.get(doc_id)
    children = Document.query.filter_by(parent_id=doc_id).all()
    
    doc_ids_to_search = [doc_id] + [child.id for child in children]
    print(f"Searching in: {len(doc_ids_to_search)} documents (1 parent + {len(children)} children)")
    
    # Search vector store
    vector_store = VectorStore(persist_dir=os.path.join(os.getcwd(), 'vector_db'))
    
    all_results = []
    for search_doc_id in doc_ids_to_search:
        result = vector_store.search_documents(question, user_id, num_results=3, doc_id=search_doc_id)
        if result.get('results'):
            print(f"\nDoc {search_doc_id}: {len(result['results'])} results")
            all_results.extend(result['results'])
    
    top_results = all_results[:5]
    print(f"\nTotal results: {len(all_results)} → Top 5 selected")
    
    if top_results:
        print("\nTop search results:")
        for i, result in enumerate(top_results, 1):
            snippet = result.get('document', '')[:100].replace('\n', ' ')
            metadata = result.get('metadata', {})
            
            if isinstance(metadata, dict):
                doc_id_str = metadata.get('document_id')
                doc_title = metadata.get('title', 'Unknown')
            else:
                doc_id_str = None
                doc_title = 'Unknown'
                
            print(f"  {i}. [{doc_title}] {snippet}...")
