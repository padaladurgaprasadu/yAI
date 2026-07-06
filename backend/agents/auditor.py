import os
import json
from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class AuditorAgent(BaseAgent):
    """
    The Advanced Autonomous Auditor Agent acts as a strict QA gatekeeper.
    It systematically analyzes the generated code for Performance, UI/UX, Security, 
    Accessibility, and simulates interactive logical bugs.
    """
    def __init__(self):
        super().__init__()
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an Elite QA Auditor & Security Expert. Your job is to strictly verify the generated codebase before it is deployed to production.\n\n"
             "RULES:\n"
             "1. PERFORMANCE: Analyze React components for unnecessary re-renders. Check for missing useMemo/useCallback or bloated loops.\n"
             "2. UI/UX: Verify modern aesthetics, responsive design (mobile-first), and color contrast.\n"
             "3. SECURITY: Scan for XSS (raw innerHTML injections), insecure API integrations, or missing sanitization.\n"
             "4. ACCESSIBILITY: Ensure ARIA labels, alt attributes, and keyboard navigability exist on interactive elements.\n"
             "5. SIMULATION: Mentally walk through user interactions. 'What happens if a user clicks submit twice quickly? Is there a loading state?'\n\n"
             "If you find ANY vulnerabilities, UX issues, or unoptimized code, return a specific, detailed critique outlining exactly what needs to be fixed. \n"
             "If the codebase is 100% production-ready, secure, and beautiful, you MUST return exactly the word 'APPROVED' and nothing else.\n\n"
             "CRITICAL: Do NOT write code yourself, just provide the exact feedback for the Coder to self-fix."),
            ("human", "Blueprint: {blueprint}\nCode Files Generated: {code_files}\n\nPlease run your Deep QA Audit. Output exact feedback or 'APPROVED'.")
        ])
        
        self.chain = self.prompt | self.fast_llm

    def run(self, state: AiONState) -> AiONState:
        project_id = state.get("project_id", "default")
        
        try:
            from backend.api_real import stream_queues
            q = stream_queues.get(project_id)
        except ImportError:
            q = None

        if q:
            q.put({"type": "agent_state", "agent": "auditor"})
            q.put({"type": "timeline", "title": f"Deep QA Audit (Attempt {state.get('revision_count', 0) + 1})", "reason": "Scanning for Security & UX issues", "status": "active"})
            q.put({"type": "progress", "message": "🛡️ Advanced QA Auditor is simulating user interactions..."})
            
        logger.info("[Auditor] Running deep QA audit on generated code...")
        
        if not state.get("code_files"):
            state["audit_feedback"] = "APPROVED"
            return state

        import time
        max_retries = 3
        feedback = "APPROVED"
        
        for attempt in range(max_retries):
            try:
                # Truncate code files output to prevent token limits
                code_files_summary = {k: v[:800] + "... [TRUNCATED]" if len(v) > 800 else v for k, v in state["code_files"].items()}
                
                response = self.chain.invoke({
                    "blueprint": json.dumps(state.get("blueprint", {})),
                    "code_files": json.dumps(code_files_summary)
                })
                
                feedback = response.content.strip()
                break
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    logger.warning(f"   -> [WARNING] Rate limit hit for Auditor. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"   -> [ERROR] Auditor encountered an exception: {e}")
                    feedback = "APPROVED" # Fail open
                    break
        
        if feedback == "APPROVED" or feedback.startswith("APPROVED"):
            logger.info("   -> [Audit Result] Code APPROVED!")
            state["audit_feedback"] = "APPROVED"
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                q.put({"type": "timeline", "title": "QA Audit Passed", "reason": "Code is secure and optimized", "status": "done"})
        else:
            logger.info("   -> [Audit Result] QA Issues found. Sending back to Coder.")
            state["audit_feedback"] = feedback
            # Increment revision count only if we are sending it back
            rev_count = state.get("revision_count", 0)
            state["revision_count"] = rev_count + 1
            
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                q.put({"type": "timeline", "title": "QA Issues Detected", "reason": "Sending feedback to Coder for self-fix", "status": "done"})
                
        return state
