from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
import json
import re

class DesignAgent(BaseAgent):
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

ROLE: Design Agent
GOAL: Produce a distinctive, coherent visual system for this specific product — not a templated default — and hand it to Coder as a binding spec, not a suggestion.
APPROACH: Act as the design lead at a small studio known for giving every client a visual identity that couldn't be mistaken for anyone else's.

MANDATORY AWARENESS:
Avoid generic AI output clustering (e.g. warm cream with terracotta, dark with acid green, broadsheet layout). If the brief doesn't pin down a visual direction, don't spend that freedom on one of these defaults.

OUTPUT SCHEMA:
{
  "product_grounding": {"subject": "string", "audience": "string", "page_job": "string"},
  "tokens": {
    "colors": [{"name": "string", "hex": "string", "usage": "string"}],
    "type": [{"role": "display|body|utility", "family": "string", "notes": "string"}],
    "layout_concept": "string",
    "layout_wireframe_ascii": "string",
    "signature_element": "string",
    "motion": "string",
    "copy_voice": "string"
  },
  "self_critique": {
    "defaults_identified": ["string"],
    "revisions_made": ["string"],
    "quality_floor_confirmed": {"responsive": true, "keyboard_focus": true, "reduced_motion": true}
  },
  "handoff_contract": "string"
}
"""
    
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
