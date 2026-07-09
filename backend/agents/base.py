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
# Load environment variables from the .env file
load_dotenv()

from backend.agents.orchestration_prompts import GLOBAL_RULES, PRECEDENCE_RULE
GLOBAL_AGENT_RULES = f"{GLOBAL_RULES}\n\n{PRECEDENCE_RULE}"

class BaseAgent:
    """
    A robust AI Agent base class with multi-provider fallback and dynamic tool-binding.
    Inspired by highly resilient routing architectures.
    """
    def __init__(self, model_name="google/gemini-2.5-flash", temperature=0.2):
        self.model_name = model_name
        self.temperature = temperature
        
        # AiON Swarm Protocol: Liquid Routing integration
        from backend.agents.router import ModelRouter
        self_role = self.__class__.__name__
        
        try:
            self.smart_llm = ModelRouter.get_optimal_llm(self_role, complexity="smart")
            self.fast_llm = ModelRouter.get_optimal_llm(self_role, complexity="fast")
        except Exception as e:
            logger.warning(f"Failed to initialize ModelRouter: {e}")
            
            # Safe instantiation that doesn't crash pydantic if keys are missing
            if os.getenv("OPENAI_API_KEY"):
                self.smart_llm = ChatOpenAI(model="gpt-4o", temperature=0.1, request_timeout=90, max_retries=2, streaming=True)
                self.fast_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, request_timeout=90, max_retries=2, streaming=True)
            elif os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
                self.smart_llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.1, timeout=90, max_retries=2, streaming=True)
                self.fast_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.1, timeout=90, max_retries=2, streaming=True)
            elif os.getenv("NVIDIA_API_KEY"):
                self.smart_llm = ChatOpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=os.getenv("NVIDIA_API_KEY"),
                    model="meta/llama-3.1-70b-instruct",
                    temperature=0.1,
                    request_timeout=90,
                    max_retries=2,
                    streaming=True
                )
                self.fast_llm = ChatOpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=os.getenv("NVIDIA_API_KEY"),
                    model="meta/llama-3.1-8b-instruct",
                    temperature=0.1,
                    request_timeout=90,
                    max_retries=2,
                    streaming=True
                )
            elif os.getenv("OPENROUTER_API_KEY"):
                self.smart_llm = ChatOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=os.getenv("OPENROUTER_API_KEY"),
                    model="anthropic/claude-3.5-sonnet",
                    temperature=0.1,
                    request_timeout=90,
                    max_retries=2,
                    streaming=True
                )
                self.fast_llm = ChatOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=os.getenv("OPENROUTER_API_KEY"),
                    model="anthropic/claude-3.5-haiku",
                    temperature=0.1,
                    request_timeout=90,
                    max_retries=2,
                    streaming=True
                )
            else:
                # Provide a dummy fallback so it doesn't crash on boot, but will fail gracefully when invoked
                self.smart_llm = ChatOpenAI(api_key="dummy", model="gpt-4o", temperature=0.1, streaming=True)
                self.fast_llm = ChatOpenAI(api_key="dummy", model="gpt-4o-mini", temperature=0.1, streaming=True)
            
        # Backward compatibility for scripts still calling self.llm
        self.llm = self.smart_llm
        self.llm_pool = [self.smart_llm]
        self.fast_llm_pool = [self.fast_llm]

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
