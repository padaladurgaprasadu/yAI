import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
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
        Routes the task based on role, complexity, and availability.
        Prioritizes NVIDIA NIM models if NVIDIA_API_KEY is configured,
        implementing Phase 4 Model Routing with transparent failover.
        """
        role = task_role.lower()
        nvidia_key = os.getenv("NVIDIA_API_KEY")

        if nvidia_key:
            logger.info(f"[NVIDIA Routing] Mapping role '{task_role}' with complexity '{complexity}'")
            # 1. Map to target model pool (Primary -> Fallback 1 -> Fallback 2)
            if "router" in role or "planner" in role or "intent" in role:
                models = ["meta/llama-3.1-8b-instruct", "meta/llama-3.2-3b-instruct", "meta/llama-3.1-70b-instruct"]
            elif "architect" in role or "system" in role:
                models = ["meta/llama-3.1-70b-instruct", "nvidia/llama-3.1-nemotron-51b-instruct", "meta/llama-3.1-8b-instruct"]
            elif "coder" in role or "generator" in role or "programmer" in role:
                models = ["meta/llama-3.1-70b-instruct", "meta/llama-3.1-8b-instruct", "nvidia/llama-3.1-nemotron-51b-instruct"]
            elif "design" in role or "ui" in role or "css" in role:
                models = ["meta/llama-3.1-70b-instruct", "meta/llama-3.1-8b-instruct", "meta/llama-3.2-3b-instruct"]
            elif "reviewer" in role or "audit" in role or "critique" in role:
                models = ["meta/llama-3.1-70b-instruct", "nvidia/llama-3.1-nemotron-51b-instruct", "meta/llama-3.1-8b-instruct"]
            elif "visual" in role or "vision" in role:
                models = ["meta/llama-3.2-11b-vision-instruct", "meta/llama-3.1-70b-instruct", "meta/llama-3.1-8b-instruct"]
            elif "devops" in role or "deployment" in role:
                models = ["meta/llama-3.1-70b-instruct", "meta/llama-3.1-8b-instruct", "meta/llama-3.2-3b-instruct"]
            elif "executor" in role:
                models = ["meta/llama-3.1-8b-instruct", "meta/llama-3.1-70b-instruct", "meta/llama-3.2-3b-instruct"]
            elif "memory" in role:
                models = ["meta/llama-3.1-8b-instruct", "meta/llama-3.2-3b-instruct", "meta/llama-3.1-70b-instruct"]
            else:
                if complexity == "fast":
                    models = ["meta/llama-3.1-8b-instruct", "meta/llama-3.2-3b-instruct", "meta/llama-3.1-70b-instruct"]
                else:
                    models = ["meta/llama-3.1-70b-instruct", "nvidia/llama-3.1-nemotron-51b-instruct", "meta/llama-3.1-8b-instruct"]

            # 2. Build the fallback chain
            llm_instances = []
            for model_name in models:
                llm_instances.append(ChatOpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=nvidia_key,
                    model=model_name,
                    temperature=0.1,
                    request_timeout=90,
                    max_retries=1,
                    streaming=True
                ))
            
            # Wrap in LangChain's fallback mechanism
            primary_llm = llm_instances[0]
            fallback_llms = llm_instances[1:]
            return primary_llm.with_fallbacks(fallback_llms)

        # Standard Multi-Provider routing if NVIDIA key is not set
        # Determine optimal provider based on role
        if "ui" in role or "react" in role or "css" in role:
            provider = "anthropic"
            model_name = "claude-3-5-sonnet-20240620"
        elif "database" in role or "schema" in role:
            provider = "groq"
            model_name = "llama3-70b-8192"
        elif "security" in role or "audit" in role or "architect" in role:
            provider = "openai"
            model_name = "gpt-4o"
        elif "research" in role:
            provider = "google"
            model_name = "gemini-1.5-pro"
        else:
            provider = "openai"
            model_name = "gpt-4o-mini" if complexity == "fast" else "gpt-4o"

        # Try to instantiate the optimal model
        try:
            if provider == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
                primary = ChatAnthropic(model=model_name, temperature=0.1, timeout=90, max_retries=1, streaming=True)
                fallback = ChatAnthropic(model="claude-3-5-haiku-20241022", temperature=0.1, timeout=90, max_retries=1, streaming=True)
                return primary.with_fallbacks([fallback])
            elif provider == "groq" and os.getenv("GROQ_API_KEY"):
                primary = ChatGroq(model_name=model_name, temperature=0.1, timeout=90, max_retries=1, streaming=True)
                fallback = ChatGroq(model_name="llama3-8b-8192", temperature=0.1, timeout=90, max_retries=1, streaming=True)
                return primary.with_fallbacks([fallback])
            elif provider == "google" and os.getenv("GOOGLE_API_KEY"):
                primary = ChatGoogleGenerativeAI(model=model_name, temperature=0.1, timeout=90, max_retries=1, streaming=True)
                fallback = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.1, timeout=90, max_retries=1, streaming=True)
                return primary.with_fallbacks([fallback])
            elif provider == "openai" and os.getenv("OPENAI_API_KEY"):
                primary = ChatOpenAI(model=model_name, temperature=0.1, request_timeout=90, max_retries=1, streaming=True)
                fallback = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, request_timeout=90, max_retries=1, streaming=True)
                return primary.with_fallbacks([fallback])
        except Exception as e:
            logger.warning(f"[LiquidRouting] Failed to initialize {provider} {model_name}: {e}")

        # Fallback to whatever is available
        if os.getenv("OPENAI_API_KEY"):
            primary = ChatOpenAI(model="gpt-4o" if complexity == "smart" else "gpt-4o-mini", temperature=0.1, streaming=True)
            fallback = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.1, streaming=True)
            return primary.with_fallbacks([fallback])
        elif os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
            primary = ChatGoogleGenerativeAI(model="gemini-1.5-pro" if complexity == "smart" else "gemini-1.5-flash", temperature=0.1, streaming=True)
            return primary
        elif os.getenv("OPENROUTER_API_KEY"):
            primary = ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                model="anthropic/claude-3.5-sonnet" if complexity == "smart" else "anthropic/claude-3.5-haiku",
                temperature=0.1,
                streaming=True
            )
            fallback = ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                model="google/gemini-flash-1.5",
                temperature=0.1,
                streaming=True
            )
            return primary.with_fallbacks([fallback])

        raise Exception("Missing credentials: No API keys configured for Liquid Routing.")

class OmniIntelligenceEngine:
    def __init__(self, llm):
        """
        Omni Intelligence Engine (AiON 3.0)
        Dynamically analyzes tasks to select the optimal Multi-Speed Execution Strategy.
        """
        self.llm = llm
        
        from backend.agents.base import GLOBAL_AGENT_RULES
        from backend.agents.orchestration_prompts import ROUTER_PROMPT
        self.system_prompt = GLOBAL_AGENT_RULES + "\\n\\n" + ROUTER_PROMPT

    def detect_intent(self, message: str, history: list = None) -> dict:
        import asyncio
        return asyncio.run(self.adetect_intent(message, history))

    async def adetect_intent(self, message: str, history: list = None) -> dict:
        """
        Runs a fast LLM inference to determine the user's multi-dimensional intent asynchronously.
        """
        try:
            context = ""
            if history and len(history) > 0:
                context += "Conversation History (FOR CONTEXT ONLY - DO NOT EXTRACT QUERIES FROM HERE):\n"
                # Keep up to the last 5 messages for context
                for msg in history[-5:]:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    # Strip massive code blocks or huge texts to save tokens, but keep semantic meaning
                    if len(content) > 300:
                        content = content[:300] + "..."
                    context += f"{role.capitalize()}: {content}\n"
                context += "\n"
                
            context += f"Latest User Message: {message}"

            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=context)
            ]
            
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()
            
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
                
            data = json.loads(content)
            logger.info(f"[ROUTER] Detected Intent: {data}")
            return data
            
        except Exception as e:
            logger.warning(f"[ROUTER] Intent detection failed, falling back to GENERAL. Error: {e}")
            return {
                "domain": "General",
                "specific_intent": "General Chat",
                "complexity": "Intermediate",
                "style": "Clear and concise"
            }
