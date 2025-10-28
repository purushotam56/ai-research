#!/usr/bin/env python3
"""
Enhanced AI Chatbot with PDF Support
This version includes robust PDF reading capabilities and improved error handling.
"""

# Suppress warnings
def warn(*args, **kwargs):
    pass
import warnings
warnings.warn = warn
warnings.filterwarnings('ignore')

import os
import sys
import glob
from typing import List, Optional

# Check for required libraries
try:
    from langchain.document_loaders import TextLoader, PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.vectorstores import Chroma
    from langchain.embeddings import HuggingFaceEmbeddings
    from langchain.chains import RetrievalQA
    from langchain.prompts import PromptTemplate
    from langchain.schema import Document
    
    from ibm_watsonx_ai.foundation_models import Model
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
    from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes, DecodingMethods
    from ibm_watson_machine_learning.foundation_models.extensions.langchain import WatsonxLLM
except ImportError as e:
    print(f"❌ Missing required library: {e}")
    print("Please install required packages:")
    print("pip install PyPDF2 pymupdf langchain chromadb sentence-transformers")
    sys.exit(1)


class EnhancedDocumentLoader:
    """Enhanced document loader with PDF support and error handling"""
    
    def __init__(self):
        self.supported_pdf_extensions = ['.pdf']
        self.supported_text_extensions = ['.txt']
    
    def load_pdf_file(self, file_path: str) -> List[Document]:
        """Load a PDF file and return documents"""
        documents = []
        try:
            print(f"📖 Loading PDF: {file_path}")
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            
            # Clean up the content
            for doc in docs:
                # Remove excessive whitespace and empty lines
                content = doc.page_content.strip()
                if content:  # Only add non-empty pages
                    # Add source information to metadata
                    doc.metadata['source_file'] = os.path.basename(file_path)
                    doc.metadata['source_type'] = 'pdf'
                    documents.append(doc)
            
            print(f"✅ Loaded {len(documents)} pages from {file_path}")
            
        except Exception as e:
            print(f"❌ Error loading PDF {file_path}: {e}")
            
        return documents
    
    def load_text_file(self, file_path: str) -> List[Document]:
        """Load a text file and return documents"""
        documents = []
        try:
            print(f"📄 Loading text file: {file_path}")
            loader = TextLoader(file_path, encoding='utf-8')
            docs = loader.load()
            
            # Add metadata
            for doc in docs:
                doc.metadata['source_file'] = os.path.basename(file_path)
                doc.metadata['source_type'] = 'text'
                documents.extend(docs)
            
            print(f"✅ Loaded {len(documents)} documents from {file_path}")
            
        except Exception as e:
            print(f"❌ Error loading text file {file_path}: {e}")
            
        return documents
    
    def load_all_documents(self, directory: str = ".") -> List[Document]:
        """Load all supported documents from a directory"""
        all_documents = []
        
        # Get all files in directory
        all_files = os.listdir(directory)
        
        # Load PDF files
        pdf_files = [f for f in all_files if f.lower().endswith('.pdf')]
        for pdf_file in pdf_files:
            file_path = os.path.join(directory, pdf_file)
            documents = self.load_pdf_file(file_path)
            all_documents.extend(documents)
        
        # Load text files (prioritize company policy files)
        policy_files = [f for f in all_files if 'policy' in f.lower() and f.lower().endswith('.txt')]
        other_txt_files = [f for f in all_files if f.lower().endswith('.txt') and 'policy' not in f.lower()]
        
        # Load policy files first
        for txt_file in policy_files + other_txt_files:
            file_path = os.path.join(directory, txt_file)
            documents = self.load_text_file(file_path)
            all_documents.extend(documents)
        
        return all_documents


class AIAssistant:
    """Main AI Assistant class with enhanced capabilities"""
    
    def __init__(self):
        self.qa_system = None
        self.document_loader = EnhancedDocumentLoader()
        
    def setup_model(self):
        """Setup the Watson AI model"""
        model_id = 'google/flan-t5-xl'
        
        parameters = {
            GenParams.DECODING_METHOD: DecodingMethods.SAMPLE,
            GenParams.MIN_NEW_TOKENS: 10,
            GenParams.MAX_NEW_TOKENS: 300,  # Increased for better responses
            GenParams.TEMPERATURE: 0.3,
            GenParams.TOP_P: 0.9,
            GenParams.TOP_K: 50
        }
        
        credentials = {
            "url": "https://eu-de.ml.cloud.ibm.com",
            "apikey": "kyFq8XEA_K50zeRSFQLqxZ9QiNQucONQmCCe_FZldpDj"
        }
        
        project_id = "8de58445-d17f-414f-8acf-5e2225192984"
        
        model = Model(
            model_id=model_id,
            params=parameters,
            credentials=credentials,
            project_id=project_id
        )
        
        return WatsonxLLM(model=model)
    
    def initialize(self):
        """Initialize the AI system"""
        print("🤖 Initializing Enhanced AI Assistant...")
        print("=" * 50)
        
        # Load documents
        print("\n📚 Loading documents...")
        documents = self.document_loader.load_all_documents()
        
        if not documents:
            print("❌ No documents found!")
            print("Please ensure you have PDF files or text files in the current directory.")
            return False
        
        print(f"✅ Total documents loaded: {len(documents)}")
        
        # Process documents into chunks
        print("\n🔄 Processing documents...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        texts = text_splitter.split_documents(documents)
        print(f"✅ Created {len(texts)} text chunks")
        
        # Create embeddings and vector store
        print("\n🧠 Creating embeddings...")
        try:
            embeddings = HuggingFaceEmbeddings()
            docsearch = Chroma.from_documents(texts, embeddings)
            print("✅ Vector store created successfully")
        except Exception as e:
            print(f"❌ Error creating embeddings: {e}")
            return False
        
        # Setup model
        print("\n🔧 Setting up AI model...")
        try:
            llm = self.setup_model()
            print("✅ AI model initialized")
        except Exception as e:
            print(f"❌ Error setting up model: {e}")
            return False
        
        # Create prompt template
        prompt_template = """Use the following pieces of context to answer the question at the end. 

If you don't know the answer based on the provided context, just say that you don't know, don't try to make up an answer. 

Provide a clear, concise, and helpful answer based on the context provided.

Context: {context}

Question: {question}

Answer:"""
        
        PROMPT = PromptTemplate(
            template=prompt_template, 
            input_variables=["context", "question"]
        )
        
        # Create QA system
        try:
            self.qa_system = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=docsearch.as_retriever(search_kwargs={"k": 5}),
                return_source_documents=True,
                chain_type_kwargs={"prompt": PROMPT}
            )
            print("✅ QA system ready!")
            return True
        except Exception as e:
            print(f"❌ Error creating QA system: {e}")
            return False
    
    def ask_question(self, question: str) -> dict:
        """Ask a question to the AI system"""
        if not self.qa_system:
            return {
                "question": question,
                "answer": "AI system not initialized. Please run initialize() first.",
                "sources": []
            }
        
        try:
            result = self.qa_system.invoke(question)
            
            answer = result.get("result", "No answer provided")
            sources = []
            
            # Extract source information if available
            if "source_documents" in result:
                sources = list(set([
                    doc.metadata.get('source_file', 'Unknown')
                    for doc in result["source_documents"]
                ]))
            
            return {
                "question": question,
                "answer": answer,
                "sources": sources
            }
            
        except Exception as e:
            return {
                "question": question,
                "answer": f"Error processing question: {str(e)}",
                "sources": []
            }


def main():
    """Main function"""
    # Initialize AI Assistant
    assistant = AIAssistant()
    
    if not assistant.initialize():
        print("\n❌ Failed to initialize AI Assistant")
        return
    
    print("\n" + "=" * 50)
    print("🎉 AI Assistant is ready!")
    print("Ask questions about your company policies and PDF documents.")
    print("Type 'quit' to exit.")
    print("=" * 50)
    
    # Interactive loop
    while True:
        try:
            question = input("\n🤔 Your question: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not question:
                continue
            
            print("\n🤖 Processing...")
            result = assistant.ask_question(question)
            
            print(f"\n💬 Answer: {result['answer']}")
            
            if result['sources']:
                print(f"\n📚 Sources: {', '.join(result['sources'])}")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()