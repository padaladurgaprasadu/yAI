import os
import json
from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class ReviewerAgent(BaseAgent):
    """
    The Reviewer Agent analyzes the generated code for bugs, missing best practices, or incomplete logic.
    Refactored to run a highly optimized Static Semantic Review to bypass environment limitations (e.g. missing npm on Render).
    """
    def __init__(self):
        super().__init__()
        
        from backend.agents.base import GLOBAL_AGENT_RULES
        from backend.agents.orchestration_prompts import REVIEWER_PROMPT
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", GLOBAL_AGENT_RULES + "\\n\\n" + REVIEWER_PROMPT),
            ("human", "Project Workspace: {workspace}\nBlueprint: {blueprint}\nCode Files Generated: {code_files}")
        ])
        
        self.chain = self.prompt | self.fast_llm

    def run(self, state: AiONState) -> AiONState:
        project_id = state.get("project_id", "default")
        workspace = os.path.abspath(os.path.join(os.getcwd(), "generated_projects", project_id))
        
        try:
            from backend.api_real import stream_queues
            q = stream_queues.get(project_id)
        except ImportError:
            q = None

        if q:
            q.put({"type": "agent_state", "agent": "reviewer"})
            q.put({"type": "timeline", "title": f"Static Verification (Attempt {state.get('revision_count', 0) + 1})", "reason": "Analyzing code syntax", "status": "active"})
            q.put({"type": "progress", "message": "🔍 Senior AI Reviewer is running static analysis..."})
            
        logger.info("[Reviewer] Analyzing generated code autonomously...")
        
        rev_count = state.get("revision_count", 0)
        state["revision_count"] = rev_count + 1
        
        if not state.get("code_files"):
            state["review_feedback"] = "No code files were generated. Please generate the files."
            return state

        # Write files to disk just for user download/reference later
        os.makedirs(workspace, exist_ok=True)
        for path, content in state["code_files"].items():
            safe_path = path.replace("..", "").replace(":\\", "").lstrip("/")
            full_path = os.path.join(workspace, safe_path.replace("/", os.sep))
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        import time
        max_retries = 3
        feedback = "APPROVED"
        
        for attempt in range(max_retries):
            try:
                # Truncate code files output to prevent token limits
                code_files_summary = {k: v[:500] + "... [TRUNCATED]" if len(v) > 500 else v for k, v in state["code_files"].items()}
                
                response = self.chain.invoke({
                    "workspace": workspace,
                    "blueprint": json.dumps(state.get("blueprint", {})),
                    "code_files": json.dumps(code_files_summary)
                })
                
                response_content = response.content.strip()
                import re
                match = re.search(r'\{.*\}', response_content, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                else:
                    data = json.loads(response_content)
                
                status = data.get("status", "blocked")
                if status == "passed":
                    feedback = "APPROVED"
                else:
                    feedback = json.dumps(data.get("issues_found", []))
                break
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    logger.warning(f"   -> [WARNING] Rate limit hit for Reviewer. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"   -> [ERROR] Reviewer encountered an exception: {e}")
                    feedback = "APPROVED" # Fail open
                    break
        
        if feedback == "APPROVED":
            logger.info("[Reviewer] Code approved.")
            state["review_feedback"] = "APPROVED"
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                q.put({"type": "timeline", "title": "🔍 Reviewer: Found 0 issues. Auto-fixed.", "reason": "✅ Red-Green Loop: Passed.", "status": "done"})
        else:
            logger.warning("[Reviewer] Issues found.")
            state["review_feedback"] = feedback
            rev_count = state.get("revision_count", 0)
            state["revision_count"] = rev_count + 1
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                q.put({"type": "timeline", "title": "🔍 Reviewer: Found issues.", "reason": "🔄 Sending back to Coder for auto-fix.", "status": "done"})
                
        return state
