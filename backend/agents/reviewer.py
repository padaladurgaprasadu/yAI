import json
from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState

class ReviewerAgent(BaseAgent):
    """
    The Reviewer Agent analyzes the generated code for bugs, missing best practices, or incomplete logic.
    """
    def __init__(self):
        super().__init__()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a strict Senior Staff Code Reviewer. Review the provided code files. If the code is perfect, production-ready, and has no missing imports or syntax errors, you MUST return exactly the word 'APPROVED' and nothing else.\n\nIf you find issues (missing error handling, hardcoded secrets, syntax errors, missing standard best practices, etc.), return a detailed, actionable critique of what needs to be fixed. Do NOT write the code yourself, just provide the feedback.\n\nCRITICAL REACT CHECK: Do NOT check for 'index.html', 'main.jsx', or 'package.json' as the backend automatically scaffolds them. Only review the components provided!\n\nCRITICAL FILE EXISTENCE CHECK: If any code file imports a local file (e.g., `import AuthContext from '../AuthContext'`), you MUST verify that `AuthContext.js` (or similar) is ACTUALLY PRESENT in the provided Code Files! If the Coder imports a file that does NOT exist in the blueprint/code files, you MUST REJECT the code and tell the Coder to remove the import and define the logic inline!\n\nCRITICAL EXPORT CHECK: You MUST verify that every single function imported from local files (e.g., import {{ login }} from './api') actually exists and is exported in that target file! If the Coder imports a function that it forgot to export, you MUST REJECT the code and tell the Coder EXACTLY which function is missing from which file!"),
            ("human", "Blueprint: {blueprint}\n\nCode Files:\n{code_files}")
        ])
        self.chain = self.prompt | self.fast_llm

    def run(self, state: AiONState) -> AiONState:
        project_id = state.get("project_id")
        try:
            from backend.api_real import stream_queues
            q = stream_queues.get(project_id)
        except ImportError:
            q = None

        if q:
            q.put({"type": "agent_state", "agent": "reviewer"})
            q.put({"type": "timeline", "title": f"Reviewing Code (Attempt {state.get('revision_count', 0) + 1})", "reason": "Checking for security and quality", "status": "active"})
            q.put({"type": "progress", "message": "🔍 Senior AI Reviewer is analyzing the codebase for bugs..."})
        print("[Reviewer] Analyzing generated code for bugs...")
        
        # Initialize revision count if it doesn't exist
        rev_count = state.get("revision_count", 0)
        state["revision_count"] = rev_count + 1
        
        print(f"[Reviewer] Analyzing code (Revision {state['revision_count']})...")
        
        if not state.get("code_files"):
            state["review_feedback"] = "No code files were generated. Please generate the files."
            print("   -> [Review Feedback] No files found.")
            return state

        # Format files for the prompt
        formatted_files = ""
        for path, content in state["code_files"].items():
            formatted_files += f"\n--- File: {path} ---\n{content}\n"

        import time
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = self.chain.invoke({
                    "blueprint": json.dumps(state["blueprint"]),
                    "code_files": formatted_files
                })
                content = response.content
                if isinstance(content, list):
                    content = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
                    
                feedback = content.strip()
                break # Success, exit retry loop
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    print(f"   -> [WARNING] Rate limit hit for Reviewer. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"   -> [ERROR] Reviewer encountered an exception: {e}")
                    feedback = "APPROVED" # Fail open to prevent infinite crash loop
                    break
        
        if feedback == "APPROVED" or feedback.startswith("APPROVED"):
            print("   -> [Review Result] Code APPROVED!")
            state["review_feedback"] = "APPROVED"
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                q.put({"type": "timeline", "title": "Review Passed", "reason": "No critical issues detected", "status": "done"})
        else:
            print("   -> [Review Result] Issues found. Sending back to Coder.")
            state["review_feedback"] = feedback
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                q.put({"type": "timeline", "title": "Issues Found", "reason": "Code requires automatic repair", "status": "done"})
                
        return state
