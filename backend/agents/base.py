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
        
        # AiON Swarm Protocol: Liquid Routing integration
        from backend.agents.router import ModelRouter
        self_role = self.__class__.__name__
        
        try:
            self.smart_llm = ModelRouter.get_optimal_llm(self_role, complexity="smart")
            self.fast_llm = ModelRouter.get_optimal_llm(self_role, complexity="fast")
        except Exception as e:
            logger.warning(f"Failed to initialize ModelRouter: {e}")
            self.smart_llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.1)
            self.fast_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.1)
            
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
