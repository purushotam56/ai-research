import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class RAGChatBot:
    """RAG Chatbot with flexible LLM provider support (OpenAI, IBM Watson, Perplexity, or fallback)."""
    
    def __init__(self, vector_store=None, llm_provider: str = None, **kwargs):
        """
        Initialize the RAG chatbot with flexible LLM provider.
        
        Args:
            vector_store: ChromaDB vector store instance
            llm_provider: LLM provider ('openai', 'ibm', 'perplexity', or None for auto-detect)
            **kwargs: Additional parameters (model, temperature, etc.)
        """
        self.vector_store = vector_store
        self.chat_history = []
        
        # Auto-detect provider if not specified
        if llm_provider is None:
            llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()
        
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
        elif self.llm_provider == "perplexity":
            self._init_perplexity(**kwargs)
        elif self.llm_provider == "openai":
            self._init_openai(**kwargs)
        else:
            # Fallback to whatever is available
            if os.getenv("PERPLEXITY_API_KEY"):
                print("[LLM] Auto-detected Perplexity from environment")
                self._init_perplexity(**kwargs)
            elif os.getenv("OPENAI_API_KEY"):
                print("[LLM] Auto-detected OpenAI from environment")
                self._init_openai(**kwargs)
            elif os.getenv("IBM_API_KEY") and os.getenv("IBM_PROJECT_ID"):
                print("[LLM] Auto-detected IBM Watson from environment")
                self._init_ibm_watson(**kwargs)
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
            
            # Initialize OpenAI client with only valid parameters
            try:
                self.client = OpenAI(api_key=self.api_key)
            except TypeError as te:
                # If there are unexpected kwargs, try without them
                print(f"[LLM] OpenAI client init error: {te}")
                print("[LLM] Retrying with minimal parameters...")
                self.client = OpenAI(api_key=self.api_key)
            
            self.model = model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
            self.temperature = temperature or float(os.getenv("OPENAI_TEMPERATURE", 0.7))
            self.llm_available = True
            print(f"[LLM] ✓ OpenAI initialized (model: {self.model})")
        except ImportError:
            print("[LLM] Warning: openai package not installed")
            print("[LLM] Install it with: pip install openai")
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
    
    def _init_perplexity(self, **kwargs):
        """Initialize Perplexity LLM provider."""
        try:
            api_key = os.getenv("PERPLEXITY_API_KEY")
            if not api_key:
                raise ValueError("PERPLEXITY_API_KEY not found in environment")
            
            self.perplexity_api_key = api_key
            self.model = os.getenv("PERPLEXITY_MODEL", "sonar")
            self.temperature = float(kwargs.get("temperature", os.getenv("PERPLEXITY_TEMPERATURE", 0.7)))
            
            self.llm_available = True
            print(f"[LLM] ✓ Perplexity configured (model: {self.model})")
        except Exception as e:
            print(f"[LLM] Error initializing Perplexity: {e}")
            self.llm_available = False
    
    def generate_answer(self, question: str, documents: List[str], user_id: str = None, llm_model: str = None) -> Dict[str, Any]:
        """
        Generate answer using RAG with LLM.
        
        Args:
            question: User's question
            documents: Retrieved documents as context (list of strings)
            user_id: Current user ID (optional)
            llm_model: Selected LLM model from UI (e.g., 'openai-gpt35', 'perplexity-sonar')
            
        Returns:
            dict with answer, sources, has_context, status, provider, and model
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
                "provider": "fallback",
                "model": llm_model
            }
        
        # Map UI model selection to provider
        if llm_model:
            if llm_model.startswith('openai'):
                provider = 'openai'
            elif llm_model.startswith('perplexity'):
                provider = 'perplexity'
            elif llm_model.startswith('ibm'):
                provider = 'ibm'
            elif llm_model == 'document-search':
                provider = 'document-search'
            else:
                provider = self.llm_provider
        else:
            provider = self.llm_provider
        
        try:
            # Route to appropriate provider based on selection or default
            if provider == "openai":
                return self._generate_openai(question, documents, context, llm_model)
            elif provider == "perplexity":
                return self._generate_perplexity(question, documents, context, llm_model)
            elif provider == "ibm":
                return self._generate_ibm(question, documents, context, llm_model)
            else:
                # Fallback to document search
                return {
                    "answer": f"Document content:\n\n{documents[0][:500]}..." if documents else "No documents found",
                    "sources": documents[:3] if documents else [],
                    "has_context": bool(documents),
                    "status": "document-search",
                    "provider": "document-search",
                    "model": llm_model
                }
        except Exception as e:
            print(f"[LLM] Error generating answer: {e}")
            return {
                "answer": f"Error: {str(e)}",
                "sources": documents[:3] if documents else [],
                "has_context": bool(documents),
                "status": "error",
                "provider": provider or self.llm_provider,
                "model": llm_model
            }
    
    def _generate_openai(self, question: str, documents: List[str], context: str, llm_model: str = None) -> Dict[str, Any]:
        """Generate answer using OpenAI."""
        try:
            # Ensure OpenAI is initialized
            if not hasattr(self, 'client') or not self.client:
                self._init_openai()
            
            if not hasattr(self, 'client') or not self.client:
                raise ValueError("OpenAI client not configured")
            
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
                "provider": "openai",
                "model": llm_model or self.model
            }
        except Exception as e:
            error_msg = str(e)
            print(f"[LLM] OpenAI error: {error_msg}")
            
            # Check if it's an authentication error
            if "API key" in error_msg or "authentication" in error_msg.lower() or "401" in error_msg:
                print("[LLM] ⚠️ OpenAI Authentication failed - credentials may be invalid or expired")
                print("[LLM] Try restarting the app or checking your OPENAI_API_KEY")
            
            # Fallback to document search
            return {
                "answer": f"Unable to use OpenAI. Error: {error_msg}\n\nHere's the relevant document content:\n{documents[0][:500]}..." if documents else f"Error: {error_msg}",
                "sources": documents[:3] if documents else [],
                "has_context": bool(documents),
                "status": "error",
                "provider": "openai",
                "model": llm_model or self.model
            }
    
    def _generate_ibm(self, question: str, documents: List[str], context: str, llm_model: str = None) -> Dict[str, Any]:
        """Generate answer using IBM Watson."""
        try:
            # Ensure IBM is initialized
            if not hasattr(self, '_ibm_client'):
                self._init_ibm_watson()
            
            if not hasattr(self, 'ibm_api_key') or not self.ibm_api_key:
                raise ValueError("IBM Watson not properly configured")
            
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
                "provider": "ibm",
                "model": llm_model or self.model
            }
        except Exception as e:
            error_msg = str(e)
            print(f"[LLM] IBM Watson error: {error_msg}")
            
            # Check if it's an authentication error
            if "API key" in error_msg or "authentication" in error_msg.lower() or "BXNIM0415E" in error_msg:
                print("[LLM] ⚠️ IBM Authentication failed - credentials may be invalid or expired")
                print("[LLM] Try restarting the app or checking your IBM_API_KEY")
            
            # Fallback to document search
            return {
                "answer": f"Unable to use IBM Watson. Error: {error_msg}\n\nHere's the relevant document content:\n{documents[0][:500]}..." if documents else f"Error: {error_msg}",
                "sources": documents[:3] if documents else [],
                "has_context": bool(documents),
                "status": "error",
                "provider": "ibm",
                "model": llm_model or self.model
            }
    
    def _generate_perplexity(self, question: str, documents: List[str], context: str, llm_model: str = None) -> Dict[str, Any]:
        """Generate answer using Perplexity API."""
        try:
            import requests
            
            # Ensure Perplexity is initialized
            if not hasattr(self, 'perplexity_api_key'):
                self._init_perplexity()
            
            if not hasattr(self, 'perplexity_api_key') or not self.perplexity_api_key:
                raise ValueError("Perplexity API key not configured")
            
            # Prepare prompt with context
            system_prompt = f"""You are a helpful assistant. Use the provided context to answer questions accurately.
If the answer is not in the context, say so clearly.

Context:
{context}"""
            
            full_prompt = f"{system_prompt}\n\nQuestion: {question}\nAnswer:"
            
            # Call Perplexity API
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model if hasattr(self, 'model') else "sonar",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                "temperature": self.temperature if hasattr(self, 'temperature') else 0.7,
                "max_tokens": 512
            }
            
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Perplexity API error: {response.status_code} - {response.text}")
            
            data = response.json()
            answer = data['choices'][0]['message']['content']
            
            # Store in chat history
            self.chat_history.append({"role": "user", "content": question})
            self.chat_history.append({"role": "assistant", "content": answer})
            
            return {
                "answer": answer,
                "sources": documents[:3] if documents else [],
                "has_context": bool(documents),
                "status": "success",
                "provider": "perplexity",
                "model": llm_model or (self.model if hasattr(self, 'model') else "sonar")
            }
        except Exception as e:
            error_msg = str(e)
            print(f"[LLM] Perplexity error: {error_msg}")
            
            # Check if it's an authentication error
            if "401" in error_msg or "authentication" in error_msg.lower() or "API key" in error_msg:
                print("[LLM] ⚠️ Perplexity Authentication failed - check your PERPLEXITY_API_KEY")
                print("[LLM] Get an API key from: https://www.perplexity.ai/api/")
            
            # Fallback to document search
            return {
                "answer": f"Unable to use Perplexity. Error: {error_msg}\n\nHere's the relevant document content:\n{documents[0][:500]}..." if documents else f"Error: {error_msg}",
                "sources": documents[:3] if documents else [],
                "has_context": bool(documents),
                "status": "error",
                "provider": "perplexity",
                "model": llm_model or (self.model if hasattr(self, 'model') else "sonar")
            }
    
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
