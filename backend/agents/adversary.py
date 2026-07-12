from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
from backend.utils.logger import get_logger, measure_time
import json

logger = get_logger(__name__)

class AdversaryAgent(BaseAgent):
    """
    Adversarial MARL Agent (Red Team).
    Actively attempts to find security vulnerabilities, architectural anti-patterns,
    and edge cases in the generated code to force the Coder into higher quality output.
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
            q.put({"type": "progress", "message": "😈 Adversary Agent (Red Team) attacking code..."})
            
        print("[Adversary] Running Red Team attack on generated code...")
        
        code_files = state.get("code_files", {})
        blueprint = state.get("blueprint", {})
        
        if not code_files:
            return state
            
        sys_prompt = """You are a Malicious Red Team Hacker and Principal Security Engineer.
Your goal is to tear apart the provided codebase. Find security vulnerabilities (XSS, SQLi, CSRF, missing auth), race conditions, resource leaks, and architectural anti-patterns.
You MUST provide your feedback in EXACTLY this JSON schema and nothing else:
{
  "status": "APPROVED" | "REJECTED",
  "adversarial_score": 0-100, // 100 means completely secure, 0 means completely compromised
  "vulnerabilities": ["List of specific issues found..."]
}
If the adversarial_score is < 85, you MUST reject the code and provide detailed vulnerabilities.
Do NOT output markdown or backticks outside the JSON.
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", sys_prompt),
            ("human", "Blueprint:\n{blueprint}\n\nCode Files:\n{code_files}")
        ])
        
        chain = prompt | self.smart_llm
        
        try:
            response = chain.invoke({
                "blueprint": json.dumps(blueprint, indent=2),
                "code_files": json.dumps(code_files, indent=2)
            })
            
            content = response.content
            if isinstance(content, list):
                content = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
            
            from backend.utils.json_parser import parse_json_robustly
            data = parse_json_robustly(content)
            
            score = data.get("adversarial_score", 100)
            status = data.get("status", "APPROVED")
            vulns = data.get("vulnerabilities", [])
            
            if status == "REJECTED" or score < 85:
                print(f"   -> [Adversary] Attack Successful! Score: {score}/100. Issues: {len(vulns)}")
                feedback_str = "ADVERSARY ATTACK FAILED. Fix these vulnerabilities immediately:\n" + "\n".join(vulns)
                
                # Append to existing review feedback if any, or create new
                existing_feedback = state.get("review_feedback", "")
                if existing_feedback and existing_feedback != "APPROVED":
                    state["review_feedback"] = existing_feedback + "\n\n" + feedback_str
                else:
                    state["review_feedback"] = feedback_str
                    
                if q:
                    q.put({"type": "progress", "message": f"❌ Adversary found vulnerabilities (Score: {score}/100)"})
            else:
                print(f"   -> [Adversary] Attack Failed. Code is robust! Score: {score}/100.")
                if q:
                    q.put({"type": "progress", "message": "🛡️ Code passed Adversarial checks"})
                
        except Exception as e:
            logger.error(f"   -> [Adversary] Error during attack: {e}")
            
        return state
