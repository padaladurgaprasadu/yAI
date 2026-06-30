from pydantic import BaseModel, Field
import json
from langchain_core.messages import HumanMessage, SystemMessage
from backend.utils.logger import get_logger

logger = get_logger("AiON_Router")

class IntentRouter:
    def __init__(self, llm):
        """
        Initializes the IntentRouter with an LLM. 
        For speed, we should ideally use a fast model (e.g., Llama 3 8B), but we accept the system default.
        """
        self.llm = llm
        
        self.system_prompt = """
You are the AiON Response Planner v1.0.
Your job is NOT to answer the user's question. Your job is to decide HOW the answer should be generated.

Follow these steps carefully:
STEP 1 - Understand Intent: (General Question, Learning, Coding, Debugging, Project Development, Research, Travel, Writing, Brainstorming, Comparison, Math, Business, Medical, Legal, Career, Shopping, News, Conversation)
STEP 2 - Detect User Goal: (Learn a concept, Write code, Fix code, Plan something, Compare options, Get directions, Solve a problem, Generate content, Summarize, Translate, Research deeply, Create a project)
STEP 3 - Detect Complexity: (Simple, Medium, Complex, Research-level)
STEP 4 - Detect Missing Information: Can this be answered correctly? If NO, formulate the exact clarification question.
STEP 5 - Choose Best Style: (Conversation, Step-by-step, Bullet list, Table, Roadmap, Tutorial, Comparison, Code, Checklist, Flowchart, Timeline, Decision Tree, FAQ, Report, Article, Interview Style)
STEP 6 - Decide Length: (Very Short, Short, Medium, Detailed, Research)
STEP 7 - Decide Sections: Pick only useful ones from (Definition, Purpose, Syntax, Example, Code, Diagram, Table, Advantages, Disadvantages, Comparison, Best Practices, Timeline, Checklist, Resources, Practice, Exercises, Summary).

RULES:
1. Output ONLY a valid JSON object in this format:
{
  "primary_intent": "Selected from Step 1",
  "user_goal": "Selected from Step 2",
  "complexity": "Selected from Step 3",
  "missing_info_question": "Null if no info is missing. Otherwise, a string with the exact clarifying question.",
  "response_style": "Selected from Step 5",
  "answer_length": "Selected from Step 6",
  "sections_to_include": ["Selected from Step 7"]
}
2. Do NOT output any other text, markdown, or explanation.
"""

    def detect_intent(self, message: str, history: list = None) -> dict:
        """
        Runs a fast LLM inference to determine the user's multi-dimensional intent.
        """
        try:
            context = f"User Message: {message}"
            if history and len(history) > 0:
                context = f"Previous context: {history[-1].get('content', '')[:100]}\n{context}"

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
