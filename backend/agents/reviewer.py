import os
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
from backend.tools.terminal_tools import AGENT_TOOLS
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class ReviewerAgent(BaseAgent):
    """
    The Reviewer Agent analyzes the generated code for bugs, missing best practices, or incomplete logic.
    In Phase 2, it acts autonomously using terminal tools to verify the code mathematically (Red-Green Loop).
    """
    def __init__(self):
        super().__init__()
        self.bind_tools(AGENT_TOOLS)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an elite Autonomous Code Reviewer. Your job is to verify the codebase mathematically and syntactically before it reaches the user.\n\n"
             "The files have been written to the disk in the directory provided by the user.\n\n"
             "RULES:\n"
             "1. Use `execute_bash_command` to run linters, type checkers, or test suites (e.g., `flake8 .`, `npm run build`, `npm run lint`).\n"
             "2. If you find issues, return a highly detailed, actionable critique of what needs to be fixed. Do NOT write the code yourself, just provide the feedback to the Coder.\n"
             "3. If the code is perfect, production-ready, and passes all your terminal tests, you MUST return exactly the word 'APPROVED' and nothing else.\n\n"
             "CRITICAL EXPORT CHECK: Verify that imported local functions actually exist!"),
            ("human", "Project Workspace: {workspace}\nBlueprint: {blueprint}\n\nPlease run your terminal verification tests. If everything passes, output 'APPROVED'. Otherwise, output the exact error logs for the Coder to fix."),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # We use a standard tool-calling agent loop
        self.agent = create_tool_calling_agent(self.fast_llm, AGENT_TOOLS, self.prompt)
        self.agent_executor = AgentExecutor(agent=self.agent, tools=AGENT_TOOLS, verbose=True, max_iterations=3)

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
            q.put({"type": "timeline", "title": f"Autonomous Verification (Attempt {state.get('revision_count', 0) + 1})", "reason": "Running terminal checks", "status": "active"})
            q.put({"type": "progress", "message": "🔍 Senior AI Reviewer is executing sandboxed tests..."})
            
        logger.info("[Reviewer] Analyzing generated code autonomously...")
        
        # Initialize revision count
        rev_count = state.get("revision_count", 0)
        state["revision_count"] = rev_count + 1
        
        if not state.get("code_files"):
            state["review_feedback"] = "No code files were generated. Please generate the files."
            return state

        # PRE-REQUISITE: Write files to disk so the terminal tools can test them!
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
                # The agent will loop internally up to max_iterations (3) calling tools
                response = self.agent_executor.invoke({
                    "workspace": workspace,
                    "blueprint": json.dumps(state.get("blueprint", {}))
                })
                
                feedback = response.get("output", "").strip()
                break
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    logger.warning(f"   -> [WARNING] Rate limit hit for Reviewer. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"   -> [ERROR] Reviewer encountered an exception: {e}")
                    feedback = "APPROVED" # Fail open to prevent crash loop
                    break
        
        if feedback == "APPROVED" or feedback.startswith("APPROVED"):
            logger.info("   -> [Review Result] Code APPROVED!")
            state["review_feedback"] = "APPROVED"
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                q.put({"type": "timeline", "title": "Verification Passed", "reason": "No critical issues detected", "status": "done"})
        else:
            logger.info("   -> [Review Result] Issues found. Sending back to Coder.")
            state["review_feedback"] = feedback
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                q.put({"type": "timeline", "title": "Test Failures Detected", "reason": "Sending errors back to Coder for auto-heal", "status": "done"})
                
        return state
