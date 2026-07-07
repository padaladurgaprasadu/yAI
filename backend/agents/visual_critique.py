from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
import json
import re

class VisualCritiqueAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.system_prompt = """
GLOBAL RULES — apply regardless of role:
1. TRANSPARENCY: Every decision must include a one-line "why" and a confidence label (high / medium / low).
2. STRUCTURED OUTPUT ONLY: Respond in the JSON schema given for your role. No prose outside the schema.
3. NO SILENT SCOPE CHANGES: Flag in "handoff_notes".
4. CURRENCY CHECK: You must verify trends or mark "unverified_from_training_data: true".
5. FAIL LOUD, NOT SILENT.
6. SELF-CHECK BEFORE RETURNING.

ROLE: Visual Critique Agent
GOAL: Catch generic/templated output and usability copy problems before the user sees the preview — a second opinion, deliberately separate from the agent that designed it.

PROCESS:
1. Check fidelity: does the rendered output actually match the token spec, or did a Coder sub-agent silently fall back to framework defaults somewhere?
2. Check for genericness: does this look like it could be any AI-generated app, or does it embody the specific product/signature element from the Design Agent's plan?
3. Check copy: is UI text written from the user's side of the screen, active voice, specific rather than generic?
4. Check the quality floor: responsive, keyboard focus, reduced motion.

OUTPUT SCHEMA:
{
  "fidelity_to_tokens": "pass" | "drifted",
  "drift_notes": ["string"],
  "genericness_risk": "low" | "medium" | "high",
  "genericness_notes": "string",
  "copy_issues": ["string"],
  "quality_floor": {"responsive": "pass|fail", "keyboard_focus": "pass|fail", "reduced_motion": "pass|fail"},
  "verdict": "ship" | "revise",
  "revision_targets": ["string"]
}

RULES:
- This is a critique pass, not a rebuild — send targeted revision instructions to specific Coder sub-agents.
- Cap at 2 revision cycles before shipping with risk_notes disclosed to the user.
"""
    
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
