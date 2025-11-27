import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Import centralized LLM configuration
try:
    from llm_config import model_id_to_provider, model_id_to_model_name
except ImportError:
    # Fallback if llm_config not available
    def model_id_to_provider(model_id):
        if '-' in model_id:
            return model_id.split('-')[0]
        return model_id
    
    def model_id_to_model_name(model_id):
        if '-' in model_id:
            return model_id.split('-', 1)[1]
        return model_id

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
        elif self.llm_provider == "ollama":
            self._init_ollama(**kwargs)
        elif self.llm_provider == "llamacpp":
            self._init_llamacpp(**kwargs)
        elif self.llm_provider == "openai":
            self._init_openai(**kwargs)
        else:
            # Fallback to whatever is available
            # Check offline models first (no API key needed)
            if os.getenv("OLLAMA_HOST"):
                print("[LLM] Auto-detected Ollama from environment")
                self._init_ollama(**kwargs)
            elif os.getenv("LLAMACPP_MODEL_PATH"):
                print("[LLM] Auto-detected LlamaCpp from environment")
                self._init_llamacpp(**kwargs)
            elif os.getenv("PERPLEXITY_API_KEY"):
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
            
            # Initialize OpenAI client - be explicit about parameters, ignore others
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception as init_err:
                print(f"[LLM] OpenAI initialization failed: {init_err}")
                self.llm_available = False
                return
            
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
    
    def _init_ollama(self, model: str = "neural-chat", host: str = None, temperature: float = 0.7, **kwargs):
        """Initialize Ollama offline LLM provider."""
        try:
            import requests
            
            # Get Ollama configuration from environment or parameters
            self.ollama_host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
            self.model = model or os.getenv("OLLAMA_MODEL", "neural-chat")
            self.temperature = temperature
            
            # Test connection to Ollama server
            try:
                response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
                if response.status_code == 200:
                    print(f"[LLM] ✓ Ollama connected at {self.ollama_host}")
                    available_models = response.json().get('models', [])
                    model_names = [m.get('name') for m in available_models]
                    print(f"[LLM] Available models: {model_names}")
                    self.llm_available = True
                else:
                    print(f"[LLM] Warning: Ollama server returned status {response.status_code}")
                    self.llm_available = False
            except requests.exceptions.ConnectionError:
                print(f"[LLM] Warning: Cannot connect to Ollama at {self.ollama_host}")
                print("[LLM] Make sure Ollama is running: ollama serve")
                self.llm_available = False
            except Exception as e:
                print(f"[LLM] Error connecting to Ollama: {e}")
                self.llm_available = False
                
        except ImportError:
            print("[LLM] Warning: requests package not installed")
            self.llm_available = False
        except Exception as e:
            print(f"[LLM] Error initializing Ollama: {e}")
            self.llm_available = False
    
    def _init_llamacpp(self, model_path: str = None, n_ctx: int = 2048, n_threads: int = 4, temperature: float = 0.7, **kwargs):
        """Initialize LlamaCpp offline LLM provider for GGUF models."""
        try:
            from llama_cpp import Llama
            
            # Get model path from environment or parameters
            self.model_path = model_path or os.getenv("LLAMACPP_MODEL_PATH")
            self.n_ctx = n_ctx
            self.n_threads = n_threads
            self.temperature = temperature
            
            if not self.model_path:
                print("[LLM] Warning: No model path provided for LlamaCpp")
                print("[LLM] Set LLAMACPP_MODEL_PATH environment variable or provide model_path parameter")
                self.llm_available = False
                return
            
            # Check if model file exists
            if not os.path.exists(self.model_path):
                print(f"[LLM] Error: Model file not found at {self.model_path}")
                self.llm_available = False
                return
            
            # Load model (lazy initialization for performance)
            self._llamacpp_client = None
            print(f"[LLM] ✓ LlamaCpp configured for model: {self.model_path}")
            print(f"[LLM] Context size: {n_ctx}, Threads: {n_threads}")
            self.llm_available = True
            
        except ImportError:
            print("[LLM] Warning: llama-cpp-python package not installed")
            print("[LLM] Install with: pip install llama-cpp-python")
            self.llm_available = False
        except Exception as e:
            print(f"[LLM] Error initializing LlamaCpp: {e}")
            self.llm_available = False
    
    def _get_llamacpp_client(self):
        """Lazily load LlamaCpp model on first use."""
        if self._llamacpp_client is None:
            from llama_cpp import Llama
            print("[LLM] Loading LlamaCpp model... (this may take a moment)")
            self._llamacpp_client = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                verbose=False
            )
            print("[LLM] ✓ LlamaCpp model loaded")
        return self._llamacpp_client
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

        print(llm_model)
        
        # Check if LLM is available (default to True if not set)
        llm_available = getattr(self, 'llm_available', True)

        print(llm_available)
        print("llm_available-------")

        
        if not llm_available:
            # Gracefully fallback to document content
            print(f"[LLM] LLM not available, falling back to document search")
            return {
                "answer": f"{documents[0][:500]}..." if documents else "No documents found",
                "sources": documents[:3] if documents else [],
                "has_context": bool(documents),
                "status": "document-search",
                "provider": "document-search",
                "model": llm_model
            }
        
        # Map UI model selection to provider using centralized config
        if llm_model:
            print(f"[LLM] Processing with model: {llm_model}")
            # Use the centralized model config to get provider
            provider = model_id_to_provider(llm_model)
            print(f"[LLM] Resolved provider from model_id: {provider}")
        else:
            provider = self.llm_provider
        
        print(f"[LLM] Routing to provider: {provider}")
        
        # Ensure the selected provider is initialized
        # If user selected a different provider than default, initialize it
        if provider != self.llm_provider and provider != 'document-search':
            print(f"[LLM] User selected different provider ({provider}), ensuring it's initialized")
            if provider == 'perplexity' and not hasattr(self, 'perplexity_api_key'):
                self._init_perplexity()
            elif provider == 'openai' and not hasattr(self, 'client'):
                self._init_openai()
            elif provider == 'ibm' and not hasattr(self, 'watsonx_client'):
                self._init_ibm_watson()
            elif provider == 'ollama' and not hasattr(self, 'ollama_url'):
                self._init_ollama()
        
        try:
            # Route to appropriate provider based on selection or default
            if provider == "openai":
                return self._generate_openai(question, documents, context, llm_model)
            elif provider == "perplexity":
                return self._generate_perplexity(question, documents, context, llm_model)
            elif provider == "ibm":
                return self._generate_ibm(question, documents, context, llm_model)
            elif provider == "ollama":
                return self._generate_ollama(question, documents, context, llm_model)
            elif provider == "llamacpp":
                return self._generate_llamacpp(question, documents, context, llm_model)
            else:
                # Fallback to document search
                print(f"[LLM] Unknown provider {provider}, falling back to document search")
                return {
                    "answer": f"Document content:\n\n{documents[0][:500]}..." if documents else "No documents found",
                    "sources": documents[:3] if documents else [],
                    "has_context": bool(documents),
                    "status": "document-search",
                    "provider": "document-search",
                    "model": llm_model
                }
        except Exception as e:
            print(f"[LLM] Exception in generate_answer: {e}")
            import traceback
            traceback.print_exc()
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
            system_message = f"""You are a helpful assistant specialized in answering questions based on provided documents.

IMPORTANT INSTRUCTIONS:
1. ONLY use information from the provided context below to answer questions
2. Do NOT use any external knowledge or information from your training data
3. If the answer cannot be found in the provided context, respond with: "I cannot find this information in the provided documents."
4. Do NOT mention other people or entities with the same name from outside the provided context
5. Be direct and cite information from the documents when available

Context Documents:
---
{context}
---

Answer the user's question using ONLY the information from the above context."""
            
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
            system_prompt = f"""You are a helpful assistant specialized in answering questions based on provided documents.

IMPORTANT INSTRUCTIONS:
1. ONLY use information from the provided context below to answer questions
2. Do NOT use any external knowledge or information from your training data
3. If the answer cannot be found in the provided context, respond with: "I cannot find this information in the provided documents."
4. Do NOT mention other people or entities with the same name from outside the provided context
5. Be direct and cite information from the documents when available

Context Documents:
---
{context}
---

Answer the user's question using ONLY the information from the above context."""
            
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
                print("[LLM] Perplexity not yet initialized, initializing now...")
                self._init_perplexity()
            
            if not hasattr(self, 'perplexity_api_key') or not self.perplexity_api_key:
                raise ValueError("Perplexity API key not configured. Set PERPLEXITY_API_KEY in .env")
            
            # Extract model from llm_model parameter using centralized config
            # e.g., "perplexity-sonar" -> "sonar", "perplexity-sonar-pro" -> "sonar-pro"
            model_to_use = self.model if hasattr(self, 'model') else "sonar"
            if llm_model:
                # Use centralized config to get the actual model name
                model_to_use = model_id_to_model_name(llm_model)
            
            print(f"[LLM] Using Perplexity model: {model_to_use}")
            print(f"[LLM] API Key configured: {bool(self.perplexity_api_key)}")
            
            # Prepare prompt with context
            system_prompt = f"""You are a document analysis assistant. Your ONLY job is to answer questions using EXCLUSIVELY the provided context documents below.

CRITICAL RULES - FOLLOW THESE STRICTLY:
1. You MUST ONLY answer based on information present in the provided documents
2. You are FORBIDDEN from using any external knowledge, web search results, or training data
3. You are FORBIDDEN from mentioning any people with the same name who are NOT in the documents
4. If ANY part of the answer is not in the provided documents, you MUST respond: "I cannot find this information in the provided documents."
5. Do NOT speculate or infer beyond what is explicitly stated in the documents
6. Do NOT search the web or use any external sources
7. Cite the document content directly when answering

PROVIDED DOCUMENTS (use ONLY these):
---
{context}
---"""
            
            # Modify question to be explicit about context-only requirement
            user_content = f"""Based ONLY on the provided documents above, answer this question:

{question}

Remember: Only use information from the provided documents. Do not use any external knowledge or web search."""
            
            # Call Perplexity API
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model_to_use,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                "temperature": self.temperature if hasattr(self, 'temperature') else 0.7,
                "max_tokens": 512
            }
            
            print(f"[LLM] Sending request to Perplexity API...")
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            print(f"[LLM] Perplexity response status: {response.status_code}")
            
            if response.status_code != 200:
                raise Exception(f"Perplexity API error: {response.status_code} - {response.text}")
            
            data = response.json()
            answer = data['choices'][0]['message']['content']
            
            print(f"[LLM] ✓ Perplexity successfully generated answer")
            
            # Store in chat history
            self.chat_history.append({"role": "user", "content": question})
            self.chat_history.append({"role": "assistant", "content": answer})
            
            return {
                "answer": answer,
                "sources": documents[:3] if documents else [],
                "has_context": bool(documents),
                "status": "success",
                "provider": "perplexity",
                "model": llm_model or model_to_use
            }
        except Exception as e:
            error_msg = str(e)
            print(f"[LLM] Perplexity error: {error_msg}")
            import traceback
            traceback.print_exc()
            
            # Check if it's an authentication error
            if "401" in error_msg or "authentication" in error_msg.lower() or "API key" in error_msg:
                print("[LLM] ⚠️ Perplexity Authentication failed - check your PERPLEXITY_API_KEY")

                print("[LLM] Get an API key from: https://www.perplexity.ai/api/")
            
            # Extract meaningful information from documents for fallback
            if documents and len(documents) > 0:
                # Try to extract a concise summary from the first document
                doc_excerpt = documents[0][:1000]  # Get more content for better fallback
                fallback_answer = f"I found relevant information but encountered an issue with the AI model. Here's what I found:\n\n{doc_excerpt}..."
            else:
                fallback_answer = f"Error occurred: {error_msg}"
            
            # Return with fallback status but still report the error
            return {
                "answer": fallback_answer,
                "sources": documents[:3] if documents else [],
                "has_context": bool(documents),
                "status": "error",
                "provider": "perplexity",
                "model": llm_model or (self.model if hasattr(self, 'model') else "sonar")
            }
    
    def _generate_ollama(self, question: str, documents: List[str], context: str, llm_model: str = None) -> Dict[str, Any]:
        """Generate answer using Ollama offline LLM."""
        try:
            import requests
            
            # Prepare system message with context
            system_message = f"""You are a helpful assistant specialized in answering questions based on provided documents.

IMPORTANT INSTRUCTIONS:
1. ONLY use information from the provided context below to answer questions
2. Do NOT use any external knowledge or information from your training data
3. If the answer cannot be found in the provided context, respond with: "I cannot find this information in the provided documents."
4. Do NOT mention other people or entities with the same name from outside the provided context
5. Be direct and cite information from the documents when available

Context Documents:
---
{context}
---

Answer the user's question using ONLY the information from the above context."""
            
            # Prepare prompt
            prompt = f"{system_message}\n\nQuestion: {question}\n\nAnswer:"
            
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": self.temperature
                },
                timeout=300  # 5 minutes timeout for local inference
            )
            
            if response.status_code == 200:
                answer = response.json().get("response", "No response from Ollama")
                
                # Store in chat history
                self.chat_history.append({"role": "user", "content": question})
                self.chat_history.append({"role": "assistant", "content": answer})
                
                return {
                    "answer": answer.strip(),
                    "sources": documents[:3] if documents else [],
                    "has_context": bool(documents),
                    "status": "success",
                    "provider": "ollama",
                    "model": llm_model or self.model
                }
            else:
                error_msg = f"Ollama API returned status {response.status_code}"
                print(f"[LLM] {error_msg}")
                
                # Fallback to document content
                return {
                    "answer": f"{documents[0][:500]}..." if documents else "No documents found",
                    "sources": documents[:3] if documents else [],
                    "has_context": bool(documents),
                    "status": "document-search",
                    "provider": "document-search",
                    "model": llm_model
                }
                
        except Exception as e:
            error_msg = str(e)
            print(f"[LLM] Ollama error: {error_msg}")
            
            if "Connection" in str(type(e).__name__):
                print(f"[LLM] ⚠️ Cannot connect to Ollama at {self.ollama_host}")
                print("[LLM] Make sure Ollama is running with: ollama serve")
            
            # Fallback to document content instead of showing error
            return {
                "answer": f"{documents[0][:500]}..." if documents else "No documents found",
                "sources": documents[:3] if documents else [],
                "has_context": bool(documents),
                "status": "document-search",
                "provider": "document-search",
                "model": llm_model
            }
    
    def _generate_llamacpp(self, question: str, documents: List[str], context: str, llm_model: str = None) -> Dict[str, Any]:
        """Generate answer using LlamaCpp offline GGUF models."""
        try:
            client = self._get_llamacpp_client()
            
            # Prepare system message with context
            system_message = f"""You are a helpful assistant specialized in answering questions based on provided documents.

IMPORTANT INSTRUCTIONS:
1. ONLY use information from the provided context below to answer questions
2. Do NOT use any external knowledge or information from your training data
3. If the answer cannot be found in the provided context, respond with: "I cannot find this information in the provided documents."
4. Be direct and cite information from the documents when available

Context Documents:
---
{context}
---

Answer the user's question using ONLY the information from the above context."""
            
            # Format prompt for llama models
            prompt = f"{system_message}\n\nQuestion: {question}\n\nAnswer:"
            
            # Generate response using llamacpp
            response = client.create_completion(
                prompt=prompt,
                max_tokens=1024,
                temperature=self.temperature,
                top_p=0.9,
                top_k=40
            )
            
            answer = response['choices'][0]['text'].strip() if response['choices'] else "No response from model"
            
            # Store in chat history
            self.chat_history.append({"role": "user", "content": question})
            self.chat_history.append({"role": "assistant", "content": answer})
            
            return {
                "answer": answer,
                "sources": documents[:3] if documents else [],
                "has_context": bool(documents),
                "status": "success",
                "provider": "llamacpp",
                "model": llm_model or os.path.basename(self.model_path)
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"[LLM] LlamaCpp error: {error_msg}")
            
            # Fallback to document content instead of showing error
            return {
                "answer": f"{documents[0][:500]}..." if documents else "No documents found",
                "sources": documents[:3] if documents else [],
                "has_context": bool(documents),
                "status": "document-search",
                "provider": "document-search",
                "model": llm_model
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
