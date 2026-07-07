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
                return ChatAnthropic(model=model_name, temperature=0.1, timeout=90, max_retries=2)
            elif provider == "groq" and os.getenv("GROQ_API_KEY"):
                return ChatGroq(model_name=model_name, temperature=0.1, timeout=90, max_retries=2)
            elif provider == "google" and os.getenv("GOOGLE_API_KEY"):
                return ChatGoogleGenerativeAI(model=model_name, temperature=0.1, timeout=90, max_retries=2)
            elif provider == "openai" and os.getenv("OPENAI_API_KEY"):
                return ChatOpenAI(model=model_name, temperature=0.1, request_timeout=90, max_retries=2)
        except Exception as e:
            logger.warning(f"[LiquidRouting] Failed to initialize {provider} {model_name}: {e}")
            
        # Fallback to whatever is available
        if os.getenv("OPENAI_API_KEY"):
            return ChatOpenAI(model="gpt-4o-mini" if complexity == "fast" else "gpt-4o", temperature=0.1)
        elif os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
            return ChatGoogleGenerativeAI(model="gemini-1.5-flash" if complexity == "fast" else "gemini-1.5-pro", temperature=0.1)
        elif os.getenv("NVIDIA_API_KEY"):
            return ChatOpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=os.getenv("NVIDIA_API_KEY"),
                model="meta/llama-3.1-8b-instruct" if complexity == "fast" else "meta/llama-3.1-70b-instruct",
                temperature=0.1
            )
        
        raise Exception("Missing credentials: No API keys configured for Liquid Routing.")

class OmniIntelligenceEngine:
    def __init__(self, llm):
        """
        Omni Intelligence Engine (AiON 3.0)
        Dynamically analyzes tasks to select the optimal Multi-Speed Execution Strategy.
        """
        self.llm = llm
        
        from backend.agents.base import GLOBAL_AGENT_RULES
        self.system_prompt = GLOBAL_AGENT_RULES + """
ROLE: Router
GOAL: Classify the user's request in under one reasoning pass. Decide: Tutor mode (explain/teach)
or Builder mode (produce a running artifact). Also detect scope size (single-file / small-app /
multi-service) so the Planner doesn't over- or under-plan.

INPUT: raw user message

OUTPUT SCHEMA:
{
  "mode": "tutor" | "builder",
  "scope_estimate": "trivial" | "small_app" | "multi_service",
  "ambiguity_flags": ["list any missing critical info"],
  "confidence": "high" | "medium" | "low",
  
  "entity_detection": {
    "requires_visuals": true/false,
    "entity_type": "place|person|landmark|animal|product|logo|movie|document|none",
    "search_query": "specific string to search for images (e.g. 'Taj Mahal exterior')"
  }
}

RULES:
- Default to Builder mode if the user names a deliverable (system, app, site, dashboard, tool).
- Only add an ambiguity_flag if it would change the architecture (e.g., multi-tenant vs. single-tenant). Do not flag cosmetic ambiguity — assume sensible defaults and let Planner note them.
- Do not ask the user a clarifying question yourself. Pass flags downstream; only the Orchestrator decides whether a question is worth interrupting the pipeline for.
- Output ONLY valid JSON, no markdown wrappers.
"""

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
