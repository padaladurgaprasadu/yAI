from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
from backend.utils.logger import get_logger, measure_time
import json

logger = get_logger(__name__)

class TesterAgent(BaseAgent):
    """
    The Tester Agent analyzes generated code and writes automated unit tests.
    It feeds any immediate static analysis errors back into the state for debugging.
    """
    def __init__(self):
        super().__init__()

    @measure_time(logger)
    def run(self, state: AiONState) -> AiONState:
        agent_role = state.get("agent_role", "Fullstack Web Developer")
        code_files = state.get("code_files", {})
        
        logger.info(f"[Tester] Analyzing code and generating test suites...")
        
        if not code_files:
            logger.info("   -> [Tester] No code files found to test.")
            return state

        # Identify language/framework context
        if "Research" in agent_role:
            logger.info("   -> [Tester] Research role detected. Skipping code tests.")
            return state
            
        sys_prompt = """You are a Senior QA Automation Engineer.
Given a dictionary of generated code files, your job is to write a single, comprehensive unit test file that covers the most critical business logic.
If the project is Python, write `tests/test_main.py` using pytest.
If the project is Node.js/React, write `tests/app.test.js` using Jest.

IMPORTANT RULES:
1. Output the test file EXACTLY in this format:
<file path="tests/test_main.py">
[YOUR TEST CODE HERE]
</file>
2. Do NOT write any other text outside the tags.
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", sys_prompt),
            ("human", "Code Files:\n{code_files}")
        ])
        
        chain = prompt | self.llm
        
        try:
            # We convert code_files dict to a formatted string to avoid token explosion,
            # but for MVP we'll just pass the dictionary string representation.
            response = chain.invoke({
                "code_files": json.dumps(code_files, indent=2)
            })
            
            content = response.content
            if isinstance(content, list):
                content = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
                
            import re
            match = re.search(r'<file\s+path="([^"]+)">(.*?)</file>', content, re.DOTALL)
            if match:
                test_path = match.group(1).strip()
                test_code = match.group(2).strip()
                state["code_files"][test_path] = test_code
                print(f"   -> [Tester] Successfully generated {test_path}")
            else:
                print(f"   -> [Tester] Failed to generate test file format.")
                
        except Exception as e:
            logger.error(f"   -> [Tester] Error during test generation: {e}")
            
        return state
