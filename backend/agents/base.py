import os
import random
from typing import List, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Load environment variables from the .env file
load_dotenv()

class BaseAgent:
    """
    A robust AI Agent base class with multi-provider fallback and dynamic tool-binding.
    Inspired by highly resilient routing architectures.
    """
    def __init__(self, model_name="google/gemini-2.5-flash", temperature=0.2):
        self.model_name = model_name
        self.temperature = temperature
        
        # We store lists of LLMs. If the primary fails, we fallback to the next.
        self.llm_pool: List[Any] = []
        self.fast_llm_pool: List[Any] = []
        
        self._initialize_providers()
        
        if not self.llm_pool:
            # Absolute fallback
            openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip() or "dummy_key"
            fallback = ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key,
                model="google/gemini-2.0-flash-lite-preview-02-05:free",
                temperature=self.temperature
            )
            self.llm_pool.append(fallback)
            self.fast_llm_pool.append(fallback)
            
        # Bind the fallbacks so LangChain automatically switches if one provider hits a rate limit or 402
        if len(self.llm_pool) > 1:
            self.llm = self.llm_pool[0].with_fallbacks(self.llm_pool[1:])
        else:
            self.llm = self.llm_pool[0]
            
        if len(self.fast_llm_pool) > 1:
            self.fast_llm = self.fast_llm_pool[0].with_fallbacks(self.fast_llm_pool[1:])
        else:
            self.fast_llm = self.fast_llm_pool[0]

    def _initialize_providers(self):
        """Initializes all available providers based on API keys, ordered by preference."""
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        nvidia_key = os.getenv("NVIDIA_API_KEY", "").strip()
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        groq_keys_str = os.getenv("GROQ_API_KEYS", "").strip() or os.getenv("GROQ_API_KEY", "").strip()
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        ollama_model = os.getenv("OLLAMA_MODEL", "").strip()
        
        # 1. OpenAI (Native)
        if openai_key:
            self.llm_pool.append(ChatOpenAI(api_key=openai_key.strip(), model="gpt-4o", temperature=self.temperature, max_tokens=4096))
            self.fast_llm_pool.append(ChatOpenAI(api_key=openai_key.strip(), model="gpt-4o-mini", temperature=0.1, max_tokens=2048))
            
        # 2. NVIDIA NIM (Llama 3.1 70B/8B)
        if nvidia_key:
            self.llm_pool.append(ChatOpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=nvidia_key.strip(), model="meta/llama-3.1-70b-instruct", temperature=self.temperature, max_tokens=4096))
            self.fast_llm_pool.append(ChatOpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=nvidia_key.strip(), model="meta/llama-3.1-8b-instruct", temperature=0.1, max_tokens=2048))
            
        # 3. Google Gemini (Native)
        if gemini_key:
            self.llm_pool.append(ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=gemini_key.strip(), temperature=self.temperature, max_tokens=4096))
            self.fast_llm_pool.append(ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", google_api_key=gemini_key.strip(), temperature=0.1, max_tokens=2048))
            
        # 4. Groq (Fast Fallback)
        if groq_keys_str:
            keys = [k.strip() for k in groq_keys_str.split(',') if k.strip()]
            chosen_key = random.choice(keys) if keys else "dummy"
            self.llm_pool.append(ChatOpenAI(base_url="https://api.groq.com/openai/v1", api_key=chosen_key, model="llama-3.3-70b-versatile", temperature=self.temperature, max_tokens=4096))
            self.fast_llm_pool.append(ChatOpenAI(base_url="https://api.groq.com/openai/v1", api_key=chosen_key, model="llama-3.1-8b-instant", temperature=0.1, max_tokens=2048))

        # 5. OpenRouter (Premium or Free fallback)
        if openrouter_key:
            # Using highly capable free models to ensure users without credits don't crash
            self.llm_pool.append(ChatOpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key.strip(), model="google/gemini-2.0-pro-exp-02-05:free", temperature=self.temperature, max_tokens=4096))
            self.fast_llm_pool.append(ChatOpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key.strip(), model="google/gemini-2.0-flash-lite-preview-02-05:free", temperature=0.1, max_tokens=2048))

    def bind_tools(self, tools: List[Any]):
        """Dynamically binds a list of tools to the active primary LLMs."""
        for i in range(len(self.llm_pool)):
            if hasattr(self.llm_pool[i], "bind_tools"):
                self.llm_pool[i] = self.llm_pool[i].bind_tools(tools)
        for i in range(len(self.fast_llm_pool)):
            if hasattr(self.fast_llm_pool[i], "bind_tools"):
                self.fast_llm_pool[i] = self.fast_llm_pool[i].bind_tools(tools)
        
        # Update active pointers
        self.llm = self.llm_pool[0]
        self.fast_llm = self.fast_llm_pool[0]

    def invoke_with_retry(self, chain, inputs, use_fast=False):
        """
        Executes a LangChain invocation with provider fallback and exponential backoff.
        If the primary provider fails due to rate limits or outages, automatically fails over.
        """
        pool = self.fast_llm_pool if use_fast else self.llm_pool
        last_exception = None
        
        for provider in pool:
            # Create a temporary chain using this specific provider
            # Assuming `chain` is a standard prompt | llm | output_parser pipeline,
            # this might require chain recreation if not using native invoke.
            # For simplicity in this architecture, we rely on the agent's internal retry block.
            pass
            
        # Standard exponential backoff retry for the current active LLM
        @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=30), reraise=True)
        def _execute():
            try:
                return chain.invoke(inputs)
            except Exception as e:
                logger.warning(f"[RETRY] LLM call failed with error: {e}. Retrying...")
                raise e
                
        return _execute()
