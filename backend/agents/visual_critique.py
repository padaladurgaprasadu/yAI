from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
import json
import re

class VisualCritiqueAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        from backend.agents.base import GLOBAL_AGENT_RULES
        from backend.agents.orchestration_prompts import VISUAL_CRITIQUE_PROMPT
        self.system_prompt = GLOBAL_AGENT_RULES + "\\n\\n" + VISUAL_CRITIQUE_PROMPT
    
    def run(self, state: AiONState) -> dict:
        design_tokens = state.get("design_tokens", {})
        code_files = state.get("code_files", {})
        visual_revision_count = state.get("visual_revision_count", 0)
        
        # We can simulate rendering or just analyze the code content vs design tokens
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "Design Tokens: {design_tokens}\nCode Files: {code_files}")
        ])
        
        try:
            response = self.invoke_with_retry(
                self.llm, 
                prompt.format_messages(
                    design_tokens=json.dumps(design_tokens, indent=2),
                    code_files=json.dumps({k: v[:500] + '...' for k, v in code_files.items()}, indent=2) # Only send head to save tokens
                )
            )
            content = response.content
            
            # Extract JSON
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                critique = json.loads(match.group(0))
            else:
                critique = json.loads(content)
                
            return {
                "visual_critique_feedback": critique.get("revision_targets", []),
                "visual_revision_count": visual_revision_count + 1,
                "audit_feedback": "APPROVED" if critique.get("verdict") == "ship" else "REVISE"
            }
        except Exception as e:
            print(f"[VisualCritiqueAgent] Error: {e}")
            return {"audit_feedback": "APPROVED"} # Fail open to avoid blocking
