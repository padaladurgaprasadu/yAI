from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from backend.agents.base import BaseAgent
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class FormatterAgent(BaseAgent):
    """
    Takes a validated LLM draft and formats it perfectly using rich Markdown
    (Headings, Bullet points, Code blocks, Tables). Streams the final result.
    """
    def __init__(self, llm=None):
        super().__init__()
        if llm:
            self.llm = llm

        self.system_prompt = """
You are the AiON Output Formatter. Your ONLY job is to take the provided draft text and reformat it into a beautiful, highly readable Markdown structure.

FORMATTING RULES:
1. Break up any long paragraphs.
2. Use bolding to highlight key terms.
3. Use Markdown lists (bullet points or numbered) wherever multiple items are mentioned.
4. Use appropriate Headings (## or ###) to separate sections.
5. If there is code, ensure it is wrapped in triple backticks with the correct language identifier.
6. Do NOT change the meaning, facts, or tone of the draft. Just beautify the structure.
7. Output NOTHING but the final formatted Markdown. No preamble, no "Here is your formatted text."
"""

    def stream_format(self, draft_text: str):
        logger.info("[FORMATTER] Formatting and streaming final response...")
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Draft Text:\n{draft_text}")
        ]

        # Return the stream generator so the API can yield it directly to the user
        return self.llm.stream(messages)
