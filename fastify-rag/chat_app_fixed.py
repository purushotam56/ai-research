from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import your existing AI components - Updated imports for latest LangChain
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
import os
import glob
from ibm_watsonx_ai.foundation_models import Model
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes, DecodingMethods
from ibm_watson_machine_learning.foundation_models.extensions.langchain import WatsonxLLM

app = FastAPI(title="AI Company Policy Chatbot")

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Initialize your AI components
def load_documents():
    """Load documents from PDF and text files in the current directory"""
    all_documents = []
    
    # Load PDF files
    pdf_files = glob.glob("*.pdf")
    print(f"Found PDF files: {pdf_files}")
    
    for pdf_file in pdf_files:
        print(f"Loading PDF: {pdf_file}")
        try:
            loader = PyPDFLoader(pdf_file)
            documents = loader.load()
            all_documents.extend(documents)
            print(f"Loaded {len(documents)} pages from {pdf_file}")
        except Exception as e:
            print(f"Error loading {pdf_file}: {e}")
    
    # Load text files
    text_files = glob.glob("*.txt")
    print(f"Found text files: {text_files}")
    
    for text_file in text_files:
        print(f"Loading text file: {text_file}")
        try:
            loader = TextLoader(text_file, encoding='utf-8')
            documents = loader.load()
            all_documents.extend(documents)
            print(f"Loaded {len(documents)} documents from {text_file}")
        except Exception as e:
            print(f"Error loading {text_file}: {e}")
    
    # Debug: Print document content info
    for i, doc in enumerate(all_documents):
        content_length = len(doc.page_content.strip())
        print(f"Document {i+1}: {content_length} characters")
        if content_length > 0:
            print(f"  Preview: {doc.page_content.strip()[:100]}...")
        else:
            print(f"  Warning: Document {i+1} is empty!")
    
    return all_documents

def initialize_ai_system():
    """Initialize the AI system with document loading and model setup"""
    
    # Load and process documents
    print("Loading documents...")
    documents = load_documents()
    print(f"Total documents loaded: {len(documents)}")
    
    if not documents:
        raise Exception("No documents found to load. Please ensure PDF and/or text files are in the directory.")
    
    # Filter out empty documents
    non_empty_documents = [doc for doc in documents if doc.page_content.strip()]
    print(f"Non-empty documents: {len(non_empty_documents)} out of {len(documents)}")
    
    if not non_empty_documents:
        raise Exception("All loaded documents are empty. Please check your PDF and text files.")
    
    # Use RecursiveCharacterTextSplitter for better splitting
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    texts = text_splitter.split_documents(non_empty_documents)
    print(f"Total text chunks created: {len(texts)}")
    
    if not texts:
        raise Exception("No text chunks were created. Documents might be too short or contain no readable content.")
    
    # Debug: Print first few chunks
    for i, chunk in enumerate(texts[:3]):
        print(f"Chunk {i+1} length: {len(chunk.page_content)} characters")
        print(f"Chunk {i+1} preview: {chunk.page_content[:100]}...")
    
    # Create embeddings and vector store
    print("Creating embeddings...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    docsearch = Chroma.from_documents(texts, embeddings)
    print("Embeddings created successfully!")
    
    # Model configuration
    model_id = 'google/flan-t5-xl'
    parameters = {
        GenParams.DECODING_METHOD: DecodingMethods.SAMPLE,
        GenParams.MIN_NEW_TOKENS: 10,
        GenParams.MAX_NEW_TOKENS: 200,
        GenParams.TEMPERATURE: 0.3,
        GenParams.TOP_P: 0.9,
        GenParams.TOP_K: 50
    }
    
    # Use environment variables for credentials (more secure)
    credentials = {
        "url": "https://eu-de.ml.cloud.ibm.com",
        "apikey": os.getenv("IBM_WATSON_API_KEY", "kyFq8XEA_K50zeRSFQLqxZ9QiNQucONQmCCe_FZldpDj")
    }
    
    project_id = os.getenv("IBM_WATSON_PROJECT_ID", "8de58445-d17f-414f-8acf-5e2225192984")
    
    print("Initializing Watson model...")
    model = Model(
        model_id=model_id,
        params=parameters,
        credentials=credentials,
        project_id=project_id
    )
    
    flan_ul2_llm = WatsonxLLM(model=model)
    
    # Create a custom prompt template for better responses
    prompt_template = """Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer. Provide a clear, concise, and helpful answer.

Context: {context}

Question: {question}

Answer:"""
    
    PROMPT = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )
    
    print("Creating QA chain...")
    qa = RetrievalQA.from_chain_type(
        llm=flan_ul2_llm, 
        chain_type="stuff", 
        retriever=docsearch.as_retriever(search_kwargs={"k": 3}), 
        return_source_documents=True,  # Enable source documents
        chain_type_kwargs={"prompt": PROMPT}
    )
    
    return qa

# Initialize the AI system with error handling
print("Initializing AI system...")
qa_system = None
try:
    qa_system = initialize_ai_system()
    print("AI system ready!")
except Exception as e:
    print(f"Failed to initialize AI system: {e}")
    print("Application will start but AI features may not work properly.")

@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    """Serve the chat interface"""
    return templates.TemplateResponse("chat.html", {"request": request})

@app.post("/chat")
async def chat(question: str = Form(...)):
    """Handle chat messages with enhanced PDF document support"""
    try:
        # Check if AI system is available
        if qa_system is None:
            return {
                "question": question,
                "answer": "Sorry, the AI system is not available. Please check the server logs for initialization errors.",
                "sources": []
            }
        
        # Clean the question
        clean_question = question.strip()
        if not clean_question:
            return {
                "question": question,
                "answer": "Please ask a question about our company policies or documents.",
                "sources": []
            }
        
        # Get response from QA system
        print(f"Processing question: {clean_question}")
        result = qa_system.invoke({"query": clean_question})
        print(f"QA result type: {type(result)}")
        
        # Process the result
        answer = ""
        sources = []
        
        if isinstance(result, dict):
            # Try different possible keys for the answer
            answer = result.get("result", result.get("answer", result.get("output", str(result))))
            # Extract source documents if available
            if "source_documents" in result:
                sources = list(set([
                    doc.metadata.get('source', 'Unknown document')
                    for doc in result["source_documents"]
                    if doc.metadata.get('source')
                ]))
        else:
            answer = str(result)
        
        # Clean up the answer
        if not answer or answer.strip() == "":
            answer = "I couldn't find relevant information about that topic in our documents."
        
        # Limit answer length for better UX
        if len(answer) > 1000:
            answer = answer[:997] + "..."
        
        response = {
            "question": question,
            "answer": answer,
            "sources": sources[:3] if sources else []  # Limit to top 3 sources
        }
        
        print(f"Sending response: {response}")
        return response
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        return {
            "question": question,
            "answer": f"Sorry, I encountered an error while processing your question: {str(e)}",
            "sources": []
        }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "message": "AI Chatbot is running",
        "ai_system_ready": qa_system is not None
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)