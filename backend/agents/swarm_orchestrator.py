import json
from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
from backend.utils.logger import get_logger, measure_time

logger = get_logger(__name__)

class SwarmOrchestratorAgent(BaseAgent):
    """
    yAI Swarm Protocol: The Hive Mind Leader.
    Instead of generating code sequentially, this agent analyzes the blueprint
    and spins up dynamic sub-tasks (mapped to LangGraph 'Send' nodes) for 
    parallel, multi-agent code generation.
    """
    def __init__(self):
        super().__init__()

    @measure_time(logger)
    def run(self, state: AiONState, q=None) -> AiONState:
        logger.info("[SwarmOrchestrator] Deconstructing blueprint into parallel swarm tasks...")
        
        blueprint = state.get("blueprint", {})
        files_to_generate = blueprint.get("file_structure", [])
        num_files = len(files_to_generate) if files_to_generate else 13
        
        if q:
            q.put({"type": "agent_state", "agent": "swarm_orchestrator"})
            q.put({"type": "timeline", "title": f"💻 Coder: Generating {num_files} files in parallel...", "reason": "13 parallel sub-agents spawned", "status": "active"})
            
        blueprint = state.get("blueprint", {})
        files_to_generate = blueprint.get("file_structure", [])
        
        if not files_to_generate:
            logger.warning("[SwarmOrchestrator] No files to generate. Skipping swarm.")
            state["swarm_tasks"] = []
            return state

        # If we have auto-healing missing dependencies, only spawn tasks for those!
        missing_deps = state.get("missing_dependencies", [])
        if missing_deps:
            logger.info(f"[SwarmOrchestrator] Auto-heal triggered. Spawning swarm for missing files: {missing_deps}")
            files_to_generate = missing_deps
            state["missing_dependencies"] = []
            
        # Optional: We could use the LLM to cluster files into tasks (e.g. "Database Schema", "Frontend Components")
        # For speed and safety against API rate limits on free tiers, we'll create one task per file,
        # but LangGraph will map them dynamically.
        
        swarm_tasks = []
        for file_path in files_to_generate:
            # Determine specialized role based on file type
            if "client/" in file_path and file_path.endswith(".jsx"):
                role = "React UI/UX Specialist"
            elif "server/models" in file_path:
                role = "Database Architecture Expert"
            elif "server/" in file_path:
                role = "Node.js Backend Engineer"
            else:
                role = "Fullstack Web Developer"
                
            swarm_tasks.append({
                "target_file": file_path,
                "assigned_role": role,
                "project_id": state.get("project_id"),
                "semantic_context": state.get("semantic_context", ""),
                "blueprint_str": json.dumps(blueprint),
                "review_feedback": state.get("review_feedback"),
                "runtime_error": state.get("runtime_error")
            })
            
        state["swarm_tasks"] = swarm_tasks
        state["swarm_results"] = state.get("swarm_results", [])
        
        logger.info(f"[SwarmOrchestrator] Spawned {len(swarm_tasks)} tasks for the Hive Mind.")
        
        return state
