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
    yAI Swarm Protocol: Liquid Routing.
    Dynamically routes micro-tasks to the most optimal frontier model based on the required specialization.
    """
    
    @staticmethod
    def get_optimal_llm(task_role: str, complexity: str = "fast"):
        """
        Routes the task using the centralized Provider + Model Registry,
        mapping agent roles to capability profiles.
        """
        from backend.utils.model_registry import AIModelRegistry
        
        if complexity == "omega":
            logger.info(f"[ModelRouter] Spinning up Omega Meta-Model (MoA) for {task_role}...")
            # Grab multiple distinct models for the mixture
            worker1 = AIModelRegistry.get_llm_chain(AIModelRegistry.resolve_capability(task_role, "fast"))
            worker2 = AIModelRegistry.get_llm_chain(AIModelRegistry.resolve_capability(task_role, "smart"))
            
            # Try to grab a third fallback model for diverse reasoning
            worker3 = worker2
            
            synthesizer = AIModelRegistry.get_llm_chain(AIModelRegistry.resolve_capability("Supervisor", "smart"))
            
            from backend.models.omega import OmegaModel
            return OmegaModel(workers=[worker1, worker2, worker3], synthesizer=synthesizer)
            
        capability = AIModelRegistry.resolve_capability(task_role, complexity)
        return AIModelRegistry.get_llm_chain(capability)
        
    @staticmethod
    def route_by_file_type(file_path: str):
        """
        AST-Level Liquid Routing: Dynamically instantiate the best LLM based on file extension.
        """
        ext = file_path.split('.')[-1].lower() if '.' in file_path else ''
        
        # UI / Styling -> Vision/Design capable model
        if ext in ['css', 'scss', 'html', 'jsx', 'tsx', 'vue', 'svelte']:
            return ModelRouter.get_optimal_llm("DesignAgent", complexity="smart")
        
        # Heavy Logic / Backend -> Reasoning model
        elif ext in ['py', 'java', 'go', 'rs', 'sql', 'c', 'cpp']:
            return ModelRouter.get_optimal_llm("ArchitectAgent", complexity="smart")
            
        # Default / Config -> Fast model
        else:
            return ModelRouter.get_optimal_llm("CoderAgent", complexity="fast")

class OmniIntelligenceEngine:
    def __init__(self, llm):
        """
        Omni Intelligence Engine (yAI 3.0)
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
