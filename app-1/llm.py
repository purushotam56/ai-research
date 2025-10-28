import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class RAGChatBot:
    """RAG Chatbot with flexible LLM provider support (OpenAI, IBM Watson, or fallback)."""
    
    def __init__(self, vector_store=None, llm_provider: str = None, **kwargs):
        """
        Initialize the RAG chatbot with flexible LLM provider.
        
        Args:
            vector_store: ChromaDB vector store instance
            llm_provider: LLM provider ('openai', 'ibm', or None for auto-detect)
            **kwargs: Additional parameters (model, temperature, etc.)
        """
        self.vector_store = vector_store
        self.chat_history = []
        
        # Auto-detect provider if not specified
        if llm_provider is None:
            llm_provider = os.getenv("LLM_PROVIDER", "ibm").lower()
        
        print('LLM provider')
        print(llm_provider)
        
        self.llm_provider = llm_provider
        self._init_llm_provider(**kwargs)
    
    def _init_llm_provider(self, **kwargs):
        """Initialize the appropriate LLM provider."""
        # Initialize llm_available to True by default, will be set to False if init fails
        self.llm_available = True
        
        if self.llm_provider == "ibm":
            self._init_ibm_watson(**kwargs)
        elif self.llm_provider == "openai":
            self._init_openai(**kwargs)
        else:
            # Fallback to whatever is available
            if os.getenv("IBM_API_KEY") and os.getenv("IBM_PROJECT_ID"):
                print("[LLM] Auto-detected IBM Watson from environment")
                self._init_ibm_watson(**kwargs)
            elif os.getenv("OPENAI_API_KEY"):
                print("[LLM] Auto-detected OpenAI from environment")
                self._init_openai(**kwargs)
            else:
                print("[LLM] No LLM credentials found - running in fallback mode")
                self.llm_available = False
    
    def _init_openai(self, model: str = "gpt-3.5-turbo", temperature: float = 0.7, **kwargs):
        """Initialize OpenAI LLM provider."""
        try:
            from openai import OpenAI
            
            self.api_key = os.getenv("OPENAI_API_KEY")
            
            if not self.api_key:
                print("[LLM] Warning: OPENAI_API_KEY not found in environment")
                self.llm_available = False
                return
            
            self.client = OpenAI(api_key=self.api_key)
            self.model = model
            self.temperature = temperature
            self.llm_available = True
            print(f"[LLM] ✓ OpenAI initialized (model: {model})")
        except ImportError:
            print("[LLM] Warning: openai package not installed")
            self.llm_available = False
        except Exception as e:
            print(f"[LLM] Error initializing OpenAI: {e}")
            self.llm_available = False
    
    def _init_ibm_watson(self, model: str = "ibm/granite-3-3-8b-instruct", temperature: float = 0.5, **kwargs):
        """Initialize IBM Watson/WatsonX LLM provider."""
        try:
            from langchain_ibm import WatsonxLLM
            
            self.ibm_api_key = os.getenv("IBM_API_KEY")
            self.ibm_project_id = os.getenv("IBM_PROJECT_ID")
            self.ibm_url = os.getenv("IBM_URL", "https://api.us-south.ml.cloud.ibm.com")
            self.model = model
            self.temperature = temperature
            
            if not self.ibm_api_key or not self.ibm_project_id:
                print("[LLM] Warning: IBM_API_KEY or IBM_PROJECT_ID not found in environment")
                self.llm_available = False
                return
            
            # Store parameters for lazy initialization
            self._ibm_client = None
            self.llm_available = True
            print(f"[LLM] ✓ IBM Watson configured (model: {model})")
        except ImportError:
            print("[LLM] Warning: langchain-ibm package not installed")
            self.llm_available = False
        except Exception as e:
            print(f"[LLM] Error initializing IBM Watson: {e}")
            self.llm_available = False
    
    def _get_ibm_client(self):
        """Lazily initialize IBM Watson client on first use."""
        if self._ibm_client is None:
            from langchain_ibm import WatsonxLLM
            
            self._ibm_client = WatsonxLLM(
                model_id=self.model,
                url=self.ibm_url,
                apikey=self.ibm_api_key,
                project_id=self.ibm_project_id,
                params={
                    "max_new_tokens": 512,
                    "temperature": self.temperature,
                    "top_p": 0.2,
                    "top_k": 1
                }
            )
        return self._ibm_client
    
    def generate_answer(self, question: str, documents: List[str], user_id: str = None) -> Dict[str, Any]:
        """
        Generate answer using RAG with LLM.
        
        Args:
            question: User's question
            documents: Retrieved documents as context (list of strings)
            user_id: Current user ID (optional)
            
        Returns:
            dict with answer, sources, has_context, status, and provider
        """
        # Build context from documents
        context = "\n\n---\n\n".join(documents) if documents else ""
        
        # Check if LLM is available (default to True if not set)
        llm_available = getattr(self, 'llm_available', True)
        
        if not llm_available:
            return {
                "answer": "No LLM configured. Context from documents:\n" + context if context else "No documents found.",
                "sources": documents[:3] if documents else [],
                "has_context": bool(documents),
                "status": "fallback",
                "provider": "fallback"
            }
        
        try:
            if self.llm_provider == "openai":
                return self._generate_openai(question, documents, context)
            elif self.llm_provider == "ibm":
                return self._generate_ibm(question, documents, context)
        except Exception as e:
            print(f"[LLM] Error generating answer: {e}")
            return {
                "answer": f"Error: {str(e)}",
                "sources": documents[:3] if documents else [],
                "has_context": bool(documents),
                "status": "error",
                "provider": self.llm_provider
            }
    
    def _generate_openai(self, question: str, documents: List[str], context: str) -> Dict[str, Any]:
        """Generate answer using OpenAI."""
        try:
            # Prepare system message with context
            system_message = f"""You are a helpful assistant. Use the provided context to answer questions.
If the answer is not in the context, say so clearly.

Context:
{context}"""
            
            # Build messages with chat history
            messages = [
                {"role": "system", "content": system_message}
            ]
            
            # Add chat history (last 10 messages for context)
            for msg in self.chat_history[-10:]:
                messages.append(msg)
            
            # Add current question
            messages.append({"role": "user", "content": question})
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=1024
            )
            
            answer = response.choices[0].message.content
            
            # Store in chat history
            self.chat_history.append({"role": "user", "content": question})
            self.chat_history.append({"role": "assistant", "content": answer})
            
            return {
                "answer": answer,
                "sources": documents[:3] if documents else [],
                "has_context": bool(documents),
                "status": "success",
                "provider": "openai"
            }
        except Exception as e:
            raise e
    
    def _generate_ibm(self, question: str, documents: List[str], context: str) -> Dict[str, Any]:
        """Generate answer using IBM Watson."""
        try:
            # Get or initialize IBM client
            llm = self._get_ibm_client()
            
            # Prepare prompt with context
            system_prompt = f"""You are a helpful assistant. Use the provided context to answer questions.
If the answer is not in the context, say so clearly.

Context:
{context}"""
            
            full_prompt = f"{system_prompt}\n\nQuestion: {question}\nAnswer:"
            
            # Generate response
            answer = llm.invoke(full_prompt)
            
            # Store in chat history
            self.chat_history.append({"role": "user", "content": question})
            self.chat_history.append({"role": "assistant", "content": answer})
            
            return {
                "answer": answer,
                "sources": documents[:3] if documents else [],
                "has_context": bool(documents),
                "status": "success",
                "provider": "ibm"
            }
        except Exception as e:
            raise e
    
    def clear_history(self):
        """Clear chat history."""
        self.chat_history = []
        print("[LLM] Chat history cleared")


def create_chatbot(vector_store=None, llm_provider: str = None, **kwargs) -> RAGChatBot:
    """
    Factory function to create and initialize RAG chatbot with flexible provider.
    
    Args:
        vector_store: ChromaDB vector store instance
        llm_provider: LLM provider ('openai', 'ibm', or None for auto-detect)
        **kwargs: Additional parameters (model, temperature, etc.)
        
    Returns:
        RAGChatBot instance
    """
    return RAGChatBot(vector_store=vector_store, llm_provider=llm_provider, **kwargs)
