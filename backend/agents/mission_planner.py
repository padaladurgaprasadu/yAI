import os
import asyncio
from backend.utils.logger import get_logger
from backend.memory.digital_twin import DigitalTwinManager
from backend.orchestrator.state import AiONState
from backend.agents.planner import PlannerAgent
from backend.agents.architect import ArchitectAgent
from backend.orchestrator.graph import build_generate_graph
import json

logger = get_logger("AiON_MissionPlanner")

class MissionPlanner:
    """
    The Mission Planner orchestrates the Autonomous execution loop for Extreme Complexity tasks.
    It relies entirely on the Digital Twin to maintain state across a multi-stage project build.
    """
    def __init__(self, project_id: str, goal_data: dict, agent_role: str = "Fullstack Web Developer"):
        self.project_id = project_id
        self.goal = goal_data.get("goal", "Unknown Goal")
        self.agent_role = agent_role
        
        # Determine target directory
        self.target_dir = os.path.join(os.getcwd(), "generated_project", self.project_id)
        os.makedirs(self.target_dir, exist_ok=True)
        
        self.twin = DigitalTwinManager(self.target_dir)

    async def execute_mission(self):
        """
        Background task that executes the entire mission sequentially using the new Orchestrator Core Loop.
        """
        logger.info(f"[MissionPlanner] Starting Autonomous Mission for {self.project_id}")
        
        from backend.orchestrator.graph import build_orchestrator_graph
        graph = build_orchestrator_graph()
        
        initial_state = AiONState(
            goal=self.goal, 
            project_id=self.project_id, 
            project_dir=self.target_dir,
            agent_role=self.agent_role, 
            modules=[],
            revision_count=0,
            visual_revision_count=0,
            execution_retries=0
        )
        
        try:
            # Run the unified LangGraph execution block synchronously in a thread
            final_state = await asyncio.to_thread(graph.invoke, initial_state, {"recursion_limit": 50})
            
            # Save the final blueprint and code to the Digital Twin
            if final_state.get("blueprint"):
                self.twin.save_blueprint(final_state["blueprint"])
            if final_state.get("code_files"):
                self.twin.state["code_files"] = final_state["code_files"]
                self.twin._save_state()
                
            # Check if execution passed or failed based on runtime errors
            if final_state.get("runtime_error"):
                logger.error(f"[MissionPlanner] Mission failed: {final_state['runtime_error']}")
                self.twin.state["status"] = "FAILED"
            else:
                logger.info(f"[MissionPlanner] MISSION COMPLETE! Project {self.project_id} built successfully.")
                self.twin.state["status"] = "DONE"
                
            self.twin._save_state()
            
        except Exception as e:
            logger.error(f"[MissionPlanner] Mission {self.project_id} crashed: {e}")
            self.twin.state["status"] = "CRASHED"
            self.twin.state["error"] = str(e)
            self.twin._save_state()
            
        logger.info("[MissionPlanner] Shutting down.")
