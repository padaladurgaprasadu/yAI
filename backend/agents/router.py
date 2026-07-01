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

HEURISTIC MAPPING (Follow this closely):
- "How to learn X?" → Roadmap / Learning roadmap
- "What is X?" → Explanation / Tutorial
- "How to reach X?" → Travel directions / Step-by-step
- "Write code" → Code-first response
- "Compare X vs Y" → Comparison table
- "Fix this bug" → Debugging steps

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
