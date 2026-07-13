import os
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Capability-to-Model Registry Mapping
# Groups frontier models by capabilities (e.g. Chat, Coding, Reasoning, Vision, Embeddings, Safety)
PROVIDER_CONFIGS = {
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key_env": "NVIDIA_API_KEY",
        "capabilities": {
            "chat": [
                "meta/llama-3.1-8b-instruct"
            ],
            "coding": [
                "z-ai/glm-5.2",
                "meta/llama-3.1-70b-instruct",
                "meta/llama-3.1-8b-instruct"
            ],
            "reasoning": [
                "z-ai/glm-5.2",
                "meta/llama-3.3-70b-instruct",
                "meta/llama-3.1-70b-instruct"
            ],
            "architecture": [
                "z-ai/glm-5.2",
                "meta/llama-3.1-70b-instruct"
            ],
            "safety": [
                "meta/llama-3.1-8b-instruct"
            ],
            "vision": [
                "meta/llama-3.2-90b-vision-instruct"
            ],
            "embeddings": [
                "nvidia/nv-embedqa-e5-v5"
            ]
        }
    },
    "openai": {
        "base_url": None,
        "api_key_env": "OPENAI_API_KEY",
        "capabilities": {
            "chat": ["gpt-4o-mini", "gpt-3.5-turbo"],
            "coding": ["gpt-4o", "gpt-4o-mini"],
            "reasoning": ["gpt-4o", "gpt-4o-mini"],
            "vision": ["gpt-4o", "gpt-4o-mini"],
            "safety": ["gpt-4o-mini"],
            "memory": ["gpt-4o-mini"]
        }
    },
    "groq": {
        "base_url": None,
        "api_key_env": "GROQ_API_KEY",
        "capabilities": {
            "chat": ["llama-3.1-8b-instant", "gemma2-9b-it"],
            "coding": ["llama3-70b-8192", "llama-3.1-8b-instant"],
            "reasoning": ["llama3-70b-8192", "llama-3.1-8b-instant"],
            "vision": ["llama-3.2-11b-vision-preview"],
            "safety": ["llama-3.1-8b-instant"],
            "memory": ["llama-3.1-8b-instant"]
        }
    },
    "google": {
        "base_url": None,
        "api_key_env": "GOOGLE_API_KEY",
        "capabilities": {
            "chat": ["gemini-1.5-flash"],
            "coding": ["gemini-1.5-pro", "gemini-1.5-flash"],
            "reasoning": ["gemini-1.5-pro", "gemini-1.5-flash"],
            "vision": ["gemini-1.5-flash"],
            "safety": ["gemini-1.5-flash"],
            "memory": ["gemini-1.5-flash"]
        }
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "capabilities": {
            "chat": ["anthropic/claude-3.5-haiku", "google/gemini-flash-1.5"],
            "coding": ["anthropic/claude-3.5-sonnet", "anthropic/claude-3.5-haiku"],
            "reasoning": ["anthropic/claude-3.5-sonnet", "google/gemini-pro-1.5"],
            "vision": ["anthropic/claude-3.5-sonnet"],
            "safety": ["google/gemini-flash-1.5"],
            "memory": ["anthropic/claude-3.5-haiku"]
        }
    }
}

class AIModelRegistry:
    @staticmethod
    def get_provider() -> str:
        """
        Determines the active provider based on environment variables.
        Prioritizes: nvidia -> openai -> google -> groq -> openrouter.
        """
        if os.getenv("NVIDIA_API_KEY"):
            return "nvidia"
        if os.getenv("OPENAI_API_KEY"):
            return "openai"
        if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
            return "google"
        if os.getenv("GROQ_API_KEY"):
            return "groq"
        if os.getenv("OPENROUTER_API_KEY"):
            return "openrouter"
        return "fallback"

    @staticmethod
    def resolve_capability(role: str, complexity: str) -> str:
        """
        Maps an agent role/task to a target capability category.
        """
        role_lower = role.lower()
        
        # New 5-model strict capability mapping
        if "chat" in role_lower or "router" in role_lower or "intent" in role_lower:
            return "chat"
        if "architect" in role_lower or "research" in role_lower or "plan" in role_lower or "reason" in role_lower or "math" in role_lower or "review" in role_lower:
            return "reasoning"
        if "visual" in role_lower or "vision" in role_lower:
            return "vision"
        if "safety" in role_lower or "guard" in role_lower:
            return "safety"
        if "coder" in role_lower or "devops" in role_lower or "test" in role_lower:
            return "coding"
            
        return "chat"

    @staticmethod
    def get_llm_chain(capability: str, temperature: float = 0.1) -> Any:
        """
        Builds a robust LLM chain with transparent fallbacks based on capability.
        """
        provider = AIModelRegistry.get_provider()
        
        if provider == "fallback":
            logger.warning("[AIModelRegistry] No API keys configured. Falling back to dummy OpenAI instance.")
            return ChatOpenAI(api_key="dummy", model="gpt-4o-mini", temperature=temperature, streaming=True)

        config = PROVIDER_CONFIGS.get(provider)
        models = config["capabilities"].get(capability, config["capabilities"]["chat"])
        api_key = os.getenv(config["api_key_env"])
        
        llm_instances = []
        for model in models:
            try:
                if provider == "nvidia":
                    llm_instances.append(ChatOpenAI(
                        base_url=config["base_url"],
                        api_key=api_key,
                        model=model,
                        temperature=temperature,
                        timeout=60,
                        max_retries=0,
                        streaming=True
                    ))
                elif provider == "openai":
                    llm_instances.append(ChatOpenAI(
                        api_key=api_key,
                        model=model,
                        temperature=temperature,
                        timeout=60,
                        max_retries=0,
                        streaming=True
                    ))
                elif provider == "groq":
                    llm_instances.append(ChatGroq(
                        model_name=model,
                        groq_api_key=api_key,
                        temperature=temperature,
                        timeout=90,
                        max_retries=1,
                        streaming=True
                    ))
                elif provider == "google":
                    llm_instances.append(ChatGoogleGenerativeAI(
                        model=model,
                        google_api_key=api_key,
                        temperature=temperature,
                        timeout=90,
                        max_retries=1,
                        streaming=True
                    ))
                elif provider == "openrouter":
                    llm_instances.append(ChatOpenAI(
                        base_url=config["base_url"],
                        api_key=api_key,
                        model=model,
                        temperature=temperature,
                        request_timeout=90,
                        max_retries=1,
                        streaming=True
                    ))
            except Exception as e:
                logger.warning(f"[Model Registry] Failed to construct model {model} on provider {provider}: {e}")

        if not llm_instances:
            raise Exception(f"No models could be resolved for capability '{capability}' under provider '{provider}'.")

        primary = llm_instances[0]
        fallbacks = llm_instances[1:]
        
        if fallbacks:
            return primary.with_fallbacks(fallbacks)
        return primary
