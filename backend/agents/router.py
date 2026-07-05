from pydantic import BaseModel, Field
import json
from langchain_core.messages import HumanMessage, SystemMessage
from backend.utils.logger import get_logger

logger = get_logger("AiON_Router")

class OmniIntelligenceEngine:
    def __init__(self, llm):
        """
        Omni Intelligence Engine (AiON 3.0)
        Dynamically analyzes tasks to select the optimal Multi-Speed Execution Strategy.
        """
        self.llm = llm
        
        self.system_prompt = """
You are the AiON 3.0 Omni Intelligence Engine.
Your job is to analyze the user's engineering request and determine the optimal Execution Strategy.

Follow these steps carefully:
STEP 1 - Estimate Task Complexity: (Trivial, Low, Medium, High, Extreme)
STEP 2 - Estimate Repository Impact: (Isolated File, Component Level, Module Level, Cross-Project)
STEP 3 - Estimate Risk Level: (Low, Medium, High - e.g., touches database migrations or auth)
STEP 4 - Select Execution Mode:
  - "Lightning": For Trivial complexity, Isolated impact. (e.g., CSS tweaks, text changes, small bug fixes). Bypasses planning. Latency 2-5s.
  - "Fast": For Low complexity, Component impact. (e.g., adding a single new React component or endpoint). Bypasses heavy architecture. Latency 5-15s.
  - "Deep": For Medium to High complexity. (e.g., new app creation, major refactors, database schemas). Triggers full Architecture phase. Latency 20-60s.
  - "Autonomous": For Extreme complexity. (e.g., large system implementations). Triggers Mission Planner.
  - "Research": For information gathering, debugging explanations, or conversational queries not requiring code generation.

RULES:
1. Output ONLY a valid JSON object in this format:
{
  "task_complexity": "Selected from Step 1",
  "repository_impact": "Selected from Step 2",
  "risk_level": "Selected from Step 3",
  "execution_mode": "Selected from Step 4",
  "missing_info_question": "Null if no info is missing. Otherwise, exactly what you need to proceed.",
  "primary_intent": "General categorization of the request",
  "needs_images": true/false,
  "needs_diagrams": true/false (True ONLY for architecture, algorithms, or workflows),
  "visual_query": "The exact name of the entity to search for images (e.g. 'Adiyogi Statue', 'Albert Einstein'). Null if needs_images is false."
}
2. Output raw JSON without markdown formatting.

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
        """
        Runs a fast LLM inference to determine the user's multi-dimensional intent.
        """
        try:
            context = ""
            if history and len(history) > 0:
                context += "Conversation History:\n"
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
            
            response = self.llm.invoke(messages)
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
