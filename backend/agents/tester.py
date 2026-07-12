from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
from backend.utils.logger import get_logger, measure_time
import json
import re

logger = get_logger(__name__)

class TesterAgent(BaseAgent):
    """
    TDD-AI Tester Agent.
    Runs BEFORE the Coder Agent. Analyzes the Architect's blueprint and generates
    exhaustive unit/integration tests that the future code must pass.
    """
    def __init__(self):
        super().__init__()

    @measure_time(logger)
    def run(self, state: AiONState) -> AiONState:
        project_id = state.get("project_id")
        try:
            from backend.api_real import stream_queues
            q = stream_queues.get(project_id)
        except ImportError:
            q = None

        if q:
            q.put({"type": "progress", "message": "🧪 Tester Agent is generating TDD Suite..."})
            
        print("[Tester] Generating Test-Driven Development Suite...")
        
        agent_role = state.get("agent_role", "Fullstack Web Developer")
        blueprint = state.get("blueprint", {})
        
        if "Research" in agent_role:
            logger.info("   -> [Tester] Research role detected. Skipping TDD tests.")
            return state
            
        sys_prompt = """You are an Elite QA Automation Architect.
We are practicing strictly Test-Driven Development (TDD).
Given the Architectural Blueprint for a new project, write an exhaustive test suite (unit and integration tests) BEFORE the application code is written.

IMPORTANT RULES:
1. If it's a Python backend, write PyTest code. If Node/React, write Jest/React Testing Library code.
2. Focus on testing the core business logic, API contracts, and edge cases described in the blueprint.
3. Your output MUST be EXACTLY in this JSON schema and nothing else:
{{
  "test_suite_spec": "Raw code string containing the complete test suite"
}}
4. Do NOT output markdown or backticks outside the JSON.
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", sys_prompt),
            ("human", "Blueprint:\n{blueprint}")
        ])
        
        chain = prompt | self.smart_llm
        
        try:
            response = chain.invoke({
                "blueprint": json.dumps(blueprint, indent=2)
            })
            
            content = response.content
            if isinstance(content, list):
                content = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
            
            from backend.utils.json_parser import parse_json_robustly
            data = parse_json_robustly(content)
            
            test_suite = data.get("test_suite_spec", "")
            if test_suite:
                state["test_suite"] = test_suite
                print("   -> [Tester] Successfully generated TDD Suite.")
                if q:
                    q.put({"type": "progress", "message": "✅ TDD Suite Generated"})
            else:
                print("   -> [Tester] Failed to generate test suite spec.")
                
        except Exception as e:
            logger.error(f"   -> [Tester] Error during TDD generation: {e}")
            
        return state
