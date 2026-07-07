from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
import json
import re

class DesignAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        from backend.agents.base import GLOBAL_AGENT_RULES
        from backend.agents.orchestration_prompts import DESIGN_AGENT_PROMPT
        self.system_prompt = GLOBAL_AGENT_RULES + "\\n\\n" + DESIGN_AGENT_PROMPT
    
    def run(self, state: AiONState) -> dict:
        blueprint = state.get("blueprint", {})
        goal = state.get("goal", "")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "Goal: {goal}\nBlueprint: {blueprint}")
        ])
        
        try:
            response = self.invoke_with_retry(self.llm, prompt.format_messages(goal=goal, blueprint=json.dumps(blueprint, indent=2)))
            content = response.content
            
            # Extract JSON
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                tokens = json.loads(match.group(0))
            else:
                tokens = json.loads(content)
                
            return {"design_tokens": tokens}
        except Exception as e:
            print(f"[DesignAgent] Error: {e}")
            return {"design_tokens": None}
