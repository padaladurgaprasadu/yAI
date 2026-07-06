import os
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class ModelRouter:
    """
    AiON Swarm Protocol: Liquid Routing.
    Dynamically routes micro-tasks to the most optimal frontier model based on the required specialization.
    """
    
    @staticmethod
    def get_optimal_llm(task_role: str, complexity: str = "fast"):
        """
        Routes the task based on role and required speed.
        If the optimal provider's API key is missing, falls back to the default (OpenAI).
        """
        # Determine optimal provider based on role
        if "UI" in task_role or "React" in task_role or "CSS" in task_role:
            provider = "anthropic" # Claude 3.5 Sonnet is unmatched for UI/Frontend
            model_name = "claude-3-5-sonnet-20240620"
        elif "Database" in task_role or "Schema" in task_role:
            provider = "groq" # Groq is blazing fast for JSON/Schema generation
            model_name = "llama3-70b-8192"
        elif "Security" in task_role or "Audit" in task_role or "Architect" in task_role:
            provider = "openai" # GPT-4o for complex reasoning / logic / vision
            model_name = "gpt-4o"
        elif "Research" in task_role:
            provider = "google" # Gemini 1.5 Pro for massive context window research
            model_name = "gemini-1.5-pro"
        else:
            provider = "openai"
            model_name = "gpt-4o-mini" if complexity == "fast" else "gpt-4o"

        # Try to instantiate the optimal model
        try:
            if provider == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
                return ChatAnthropic(model=model_name, temperature=0.1)
            elif provider == "groq" and os.getenv("GROQ_API_KEY"):
                return ChatGroq(model_name=model_name, temperature=0.1)
            elif provider == "google" and os.getenv("GOOGLE_API_KEY"):
                return ChatGoogleGenerativeAI(model=model_name, temperature=0.1)
            elif provider == "openai" and os.getenv("OPENAI_API_KEY"):
                return ChatOpenAI(model=model_name, temperature=0.1)
        except Exception as e:
            logger.warning(f"[LiquidRouting] Failed to initialize {provider} {model_name}: {e}")
            
        # Fallback to whatever is available
        if os.getenv("OPENAI_API_KEY"):
            return ChatOpenAI(model="gpt-4o-mini" if complexity == "fast" else "gpt-4o", temperature=0.1)
        elif os.getenv("GOOGLE_API_KEY"):
            return ChatGoogleGenerativeAI(model="gemini-1.5-flash" if complexity == "fast" else "gemini-1.5-pro", temperature=0.1)
        
        raise Exception("Missing credentials: No API keys configured for Liquid Routing.")
