import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from backend.agents.base import BaseAgent
from backend.utils.logger import get_logger, measure_time

logger = get_logger(__name__)

class ResponseValidatorAgent(BaseAgent):
    """
    Validates a generated LLM response for grammar, duplicate sentences,
    broken markdown, hallucinations, and readability (walls of text).
    """
    def __init__(self, llm=None):
        super().__init__()
        if llm:
            self.llm = llm

        self.system_prompt = """
You are the yAI Response Validator. Your job is to review an AI-generated draft response before it is shown to the user.

Check for the following criteria:
1. Grammar & Spelling: Are there any glaring errors?
2. Redundancy: Are there duplicate sentences or overly repetitive phrases?
3. Markdown Integrity: Are code blocks properly closed? Are bold/italics syntax broken? Are there rogue backticks?
4. Readability: Is it a giant wall of text? Does it lack spacing, bullet points, or sections?
5. Hallucinations / Logic: Does it suddenly cut off mid-sentence? Does it recommend something impossible?

If the draft FAILS any of these criteria:
1. Set "valid" to false.
2. Provide short "feedback" on what failed.
3. Provide a FULLY rewritten and structurally perfect "corrected_text" that fixes all issues.

If the draft PASSES all criteria perfectly:
1. Set "valid" to true.
2. Leave "feedback" empty.
3. Provide the original text in "corrected_text".

RULES:
- Return ONLY valid JSON in this exact format:
{
    "valid": true/false,
    "feedback": "...",
    "corrected_text": "..."
}
- Do NOT output any other text or markdown wrappers like ```json. Just raw JSON.
"""

    @measure_time(logger)
    def validate_draft(self, draft_text: str, user_prompt: str) -> dict:
        logger.info("[VALIDATOR] Validating draft response...")
        
        # If the draft is a build command, it's structurally meant for the Builder pipeline.
        if "[BUILD]" in draft_text:
            return {"valid": True, "feedback": "", "corrected_text": draft_text}

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"User's Original Prompt: {user_prompt}\n\nDraft Response to Evaluate:\n{draft_text}")
        ]

        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
                
            data = json.loads(content)
            
            if not data.get("valid", True):
                logger.warning(f"[VALIDATOR] Draft failed validation! Feedback: {data.get('feedback')}")
            else:
                logger.info("[VALIDATOR] Draft passed validation.")
                
            return data
            
        except Exception as e:
            logger.error(f"[VALIDATOR] Error during validation: {e}. Passing draft through.")
            return {"valid": True, "feedback": "", "corrected_text": draft_text}
