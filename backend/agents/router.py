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
        
        self.system_prompt = """
You are the AiON 3.0 Omni Intelligence Engine.
Your job is to analyze the user's request and determine the optimal Execution Strategy.

Visual Generation Rules (MANDATORY):
- If the user asks to "draw", "sketch", "generate an image", or "show a picture", you MUST set "needs_images": true.
- Generative AI (`visual_type: "generative"`): Best for abstract concepts, UI designs, specific artistic requests, and un-real things.
- Real World (`visual_type: "real"`): Best for famous places, people, objects, and historical events. (This hits Wikipedia).
- Sketch (`visual_type: "sketch"`): Best for wireframes or diagram sketches.

*** ULTRA-LOW LATENCY SPEED MODE ***
If the user's message is a simple greeting (e.g., "hi", "hello"), a trivial conversational response, or a very short general knowledge question (e.g., "what is python?") that CLEARLY does NOT require coding, building, OR VISUALS, you MUST output ONLY this exact JSON object and nothing else:
{"execution_mode": "Research", "primary_intent": "general"}
This skips deep analysis to provide sub-0.2s latency. Do NOT use SPEED MODE if the user asks for a picture, image, or visual representation of any kind.

If it is NOT a trivial short message, follow these steps:
STEP 1 - Estimate Task Complexity: (Trivial, Low, Medium, High, Extreme)
STEP 2 - Estimate Repository Impact: (Isolated File, Component Level, Module Level, Cross-Project)
STEP 3 - Estimate Risk Level: (Low, Medium, High)
STEP 4 - Select Execution Mode:
  - "Lightning": For Trivial complexity, Isolated impact. Latency 2-5s.
  - "Fast": For Low complexity, Component impact. Latency 5-15s.
  - "Deep": For Medium to High complexity. Latency 20-60s.
  - "Autonomous": For Extreme complexity.
  - "Research": For information gathering or conversational queries.

RULES:
1. Output ONLY a valid JSON object in this format (unless using SPEED MODE):
{
  "task_complexity": "Selected from Step 1",
  "repository_impact": "Selected from Step 2",
  "risk_level": "Selected from Step 3",
  "execution_mode": "Selected from Step 4",
  "missing_info_question": "Null if no info is missing. Otherwise, exactly what you need to proceed.",
  "primary_intent": "MUST BE EXACTLY ONE OF: 'Project Development', 'Architecture Design', 'General Chat', 'Visual Request'",
  "needs_images": true/false,
  "needs_diagrams": true/false (True ONLY for architecture, algorithms, or workflows),
  "visual_type": "'real', 'generative', or 'sketch'",
  "visual_query": "The exact name or description of the entity to search/generate based ONLY on the Latest User Message.",
  "visual_count": "integer between 1 and 5"
}
2. Output raw JSON without markdown formatting.

Visual Generation Rules (MANDATORY):
- If the user asks to "draw", "sketch", "generate an image", or "show a picture", you MUST set "needs_images": true.
- Use "visual_type": "sketch" for pencil sketches. Use "generative" for general AI art.
- The "visual_query" MUST be a detailed prompt based on the user's request.

Clarification Rules (MANDATORY):
- Answer the user's question immediately whenever possible.
- Do not ask unnecessary follow-up questions.
- If a reasonable assumption can be made, make it and mention the assumption briefly.
- Only ask a clarifying question when the missing information would significantly change or prevent a correct answer.
- Ask at most one clarifying question at a time.
- Never turn simple requests into interviews.

Clarification Examples:
❌ Bad: "What type of cake? Chocolate? Vanilla?"
✅ Good: "Here's a simple homemade chocolate cake recipe. If you wanted eggless or vanilla instead, let me know."
❌ Bad: "What aspect of Python?"
✅ Good: "Python is a beginner-friendly programming language..."
❌ Bad: "What is your usage? Gaming? Coding? Editing?" (When asked for best laptop under 60k)
✅ Good: "Here are three excellent laptops under ₹60,000 for general use and programming. If you're buying for gaming, I can refine this."

CRITICAL RULE: Never ask for information that already exists in the conversation history. Review the full history before deciding if information is missing.
Do NOT output any other text, markdown, or explanation.
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
