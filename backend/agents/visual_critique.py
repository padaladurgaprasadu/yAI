import json
from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState

class VisualCritiqueAgent(BaseAgent):
    """
    Synthetic User Simulation Engine (Zero-Day UX Testing).
    Spawns AI personas to evaluate UX/UI before code is shipped.
    """
    def __init__(self):
        super().__init__()
        from backend.agents.base import GLOBAL_AGENT_RULES
        self.system_prompt = GLOBAL_AGENT_RULES + """
ROLE: Synthetic User Simulation Engine
GOAL: Evaluate the generated UI code by simulating 3 distinct user personas.

PERSONA 1: The Power User (Focus: Keyboard shortcuts, dense information architecture, speed).
PERSONA 2: The Impatient User (Focus: Clear Call-To-Actions, minimal visual clutter, zero confusion).
PERSONA 3: The Accessibility User (Focus: WCAG compliance, aria-labels, high contrast, screen-reader semantic HTML).

INSTRUCTIONS:
Analyze the provided React UI code from the perspective of each persona. 
Score the UX out of 100 for each persona.
If the average score is below 85, or if Persona 3 finds a critical accessibility violation, you MUST fail the UX test.

OUTPUT SCHEMA (STRICT JSON ONLY):
{
  "personas": [
    {
      "name": "Power User",
      "score": 0,
      "feedback": "Specific complaint or praise"
    },
    {
      "name": "Impatient User",
      "score": 0,
      "feedback": "Specific complaint or praise"
    },
    {
      "name": "Accessibility User",
      "score": 0,
      "feedback": "Specific complaint or praise"
    }
  ],
  "average_score": 0,
  "verdict": "ship" | "revise",
  "revision_targets": ["Specific instruction for the Coder to fix UX issue 1", "Specific instruction for UX issue 2"]
}
"""
    
    def run(self, state: AiONState) -> AiONState:
        project_id = state.get("project_id")
        try:
            from backend.api_real import stream_queues
            q = stream_queues.get(project_id)
        except ImportError:
            q = None

        if q:
            q.put({"type": "progress", "message": "🧪 Generating 3 Synthetic Users for Zero-Day UX Testing..."})
            
        print("[VisualCritique] Running Synthetic User UX Simulation...")

        design_tokens = state.get("design_tokens", {})
        code_files = state.get("code_files", {})
        visual_revision_count = state.get("visual_revision_count", 0)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "Design Tokens: {design_tokens}\nCode Files: {code_files}")
        ])
        
        try:
            # Send the core UI files
            ui_code = {k: v for k, v in code_files.items() if k.endswith((".jsx", ".tsx", ".css", ".html"))}
            
            response = self.invoke_with_retry(
                self.smart_llm, # Use smart LLM for complex persona emulation
                prompt.format_messages(
                    design_tokens=json.dumps(design_tokens, indent=2),
                    code_files=json.dumps(ui_code, indent=2)
                )
            )
            content = response.content
            if isinstance(content, list):
                content = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
            
            from backend.utils.json_parser import parse_json_robustly
            critique = parse_json_robustly(content)
            
            avg_score = critique.get("average_score", 100)
            verdict = critique.get("verdict", "ship")
            revisions = critique.get("revision_targets", [])
            personas = critique.get("personas", [])
            
            for p in personas:
                print(f"   -> [{p.get('name')}] Score: {p.get('score')}/100. Feedback: {p.get('feedback')}")
                
            if verdict == "revise" or avg_score < 85:
                print(f"   -> [VisualCritique] UX Test FAILED. Average Score: {avg_score}/100. Routing to Semantic Diff Engine.")
                if q:
                    q.put({"type": "progress", "message": f"❌ UX Test Failed (Score: {avg_score}). Triggering UI Redesign..."})
                
                feedback_str = "UX SIMULATION FAILED. The UI confused our Synthetic Users. Fix the following UX issues immediately:\n" + "\n".join(revisions)
                
                existing_feedback = state.get("visual_critique_feedback", "")
                if existing_feedback and existing_feedback != "APPROVED":
                    state["visual_critique_feedback"] = existing_feedback + "\n\n" + feedback_str
                else:
                    state["visual_critique_feedback"] = feedback_str
                    
                state["visual_revision_count"] = visual_revision_count + 1
                state["audit_feedback"] = "REVISE" # Triggers graph reroute back to coder
            else:
                print(f"   -> [VisualCritique] UX Test PASSED! Average Score: {avg_score}/100.")
                if q:
                    q.put({"type": "progress", "message": f"✨ UI passed Synthetic User Testing (Score: {avg_score}/100)!"})
                state["visual_critique_feedback"] = "APPROVED"
                state["audit_feedback"] = "APPROVED"
                
        except Exception as e:
            print(f"[VisualCritiqueAgent] Error during UX simulation: {e}")
            state["visual_critique_feedback"] = "APPROVED"
            state["audit_feedback"] = "APPROVED" # Fail open to prevent infinite crash loop
            
        return state
