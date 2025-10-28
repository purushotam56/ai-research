#!/usr/bin/env python3
"""
PDF Document Processor for AI Chatbot
This script demonstrates how to process PDF documents for the AI chatbot.
"""

import os
import sys
from typing import List
import glob

try:
    from langchain.document_loaders import PyPDFLoader, TextLoader
    from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
    from langchain.schema import Document
except ImportError:
    print("Please install required packages:")
    print("pip install -r requirements.txt")
    sys.exit(1)


class DocumentProcessor:
    """Enhanced document processor with PDF support"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def load_pdf(self, pdf_path: str) -> List[Document]:
        """Load and process a PDF file"""
        try:
            loader = PyPDFLoader(pdf_path)
            documents = loader.load()
            print(f"✅ Loaded {len(documents)} pages from {pdf_path}")
            return documents
        except Exception as e:
            print(f"❌ Error loading {pdf_path}: {e}")
            return []
    
    def load_text_file(self, text_path: str) -> List[Document]:
        """Load and process a text file"""
        try:
            loader = TextLoader(text_path, encoding='utf-8')
            documents = loader.load()
            print(f"✅ Loaded {len(documents)} documents from {text_path}")
            return documents
        except Exception as e:
            print(f"❌ Error loading {text_path}: {e}")
            return []
    
    def load_all_documents(self, directory: str = ".") -> List[Document]:
        """Load all PDF and text files from a directory"""
        all_documents = []
        
        # Change to the specified directory
        original_dir = os.getcwd()
        os.chdir(directory)
        
        try:
            # Load PDF files
            pdf_files = glob.glob("*.pdf")
            if pdf_files:
                print(f"\n📁 Found {len(pdf_files)} PDF files:")
                for pdf_file in pdf_files:
                    print(f"   - {pdf_file}")
                    documents = self.load_pdf(pdf_file)
                    all_documents.extend(documents)
            
            # Load text files
            text_files = glob.glob("companyPolicies*.txt") + glob.glob("*.txt")
            # Remove duplicates and filter out non-policy files if needed
            text_files = list(set(text_files))
            
            if text_files:
                print(f"\n📄 Found {len(text_files)} text files:")
                for text_file in text_files:
                    print(f"   - {text_file}")
                    documents = self.load_text_file(text_file)
                    all_documents.extend(documents)
            
        finally:
            # Return to original directory
            os.chdir(original_dir)
        
        return all_documents
    
    def process_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into smaller chunks"""
        if not documents:
            return []
        
        print(f"\n🔄 Processing {len(documents)} documents...")
        chunks = self.text_splitter.split_documents(documents)
        print(f"✅ Created {len(chunks)} text chunks")
        
        return chunks
    
    def get_document_info(self, documents: List[Document]) -> dict:
        """Get information about loaded documents"""
        if not documents:
            return {"total_documents": 0, "total_characters": 0, "sources": []}
        
        total_chars = sum(len(doc.page_content) for doc in documents)
        sources = list(set(doc.metadata.get('source', 'unknown') for doc in documents))
        
        return {
            "total_documents": len(documents),
            "total_characters": total_chars,
            "sources": sources,
            "avg_chars_per_doc": total_chars // len(documents) if documents else 0
        }


def main():
    """Main function to test PDF processing"""
    print("🤖 AI Chatbot PDF Document Processor")
    print("=" * 50)
    
    processor = DocumentProcessor()
    
    # Load documents
    documents = processor.load_all_documents()
    
    if not documents:
        print("\n❌ No documents found!")
        print("Make sure you have PDF files or text files in the current directory.")
        return
    
    # Process documents
    chunks = processor.process_documents(documents)
    
    # Get document info
    info = processor.get_document_info(documents)
    chunk_info = processor.get_document_info(chunks)
    
    # Print summary
    print(f"\n📊 Document Summary:")
    print(f"   Documents loaded: {info['total_documents']}")
    print(f"   Text chunks created: {chunk_info['total_documents']}")
    print(f"   Total characters: {info['total_characters']:,}")
    print(f"   Average chars per document: {info['avg_chars_per_doc']:,}")
    print(f"   Sources: {', '.join(info['sources'])}")
    
    # Show sample content
    if chunks:
        print(f"\n📝 Sample content from first chunk:")
        sample_content = chunks[0].page_content[:200]
        print(f"   {sample_content}...")


if __name__ == "__main__":
    main()