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
        Background task that executes the entire mission sequentially.
        """
        logger.info(f"[MissionPlanner] Starting Autonomous Mission for {self.project_id}")
        
        # STEP 1: Planning Phase
        planner = PlannerAgent()
        initial_state = AiONState(
            goal=self.goal, 
            project_id=self.project_id, 
            project_dir=self.target_dir,
            agent_role=self.agent_role, 
            modules=[]
        )
        planned_state = await asyncio.to_thread(planner.run, initial_state)
        modules = planned_state.get("modules", [])
        
        logger.info(f"[MissionPlanner] Planned {len(modules)} modules/tasks.")

        # STEP 2: Architecture Phase
        architect = ArchitectAgent()
        sys_prompt = f"You are a Senior Systems Architect acting as a {self.agent_role}. Given a goal and a list of modules, design a technology stack and a blueprint.\n\nCRITICAL ARCHITECTURE RULE: You MUST ALWAYS build a FULLSTACK application with a Node.js (Express) backend and a React frontend.\n\nReturn ONLY valid JSON with three keys: 'tech_stack' (a list of strings), 'blueprint_notes' (a short string), and 'file_structure' (a list of 5 to 10 file paths needed for the app). Do not include markdown formatting or backticks, just the raw JSON."
        
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=f"Goal: {self.goal}\nModules: {','.join(modules)}\n")
        ]
        
        logger.info("[MissionPlanner] Running Architect...")
        arch_response = await asyncio.to_thread(architect.llm.invoke, messages)
        content = arch_response.content.strip().strip('`').replace('json\n', '')
        try:
            blueprint = json.loads(content)
            self.twin.save_blueprint(blueprint)
        except Exception as e:
            logger.warning(f"[MissionPlanner] Architect JSON failed to parse, using raw: {e}")
            blueprint = {"raw": content}
            self.twin.save_blueprint(blueprint)

        # STEP 3: Autonomous Execution Loop
        graph = build_generate_graph()
        
        while True:
            task = self.twin.get_next_pending_task()
            if not task:
                # Check if all are done, or if some are stuck
                all_tasks = self.twin.get_tasks()
                pending = [t for t in all_tasks.values() if t.get("status") in ["PENDING", "IN_PROGRESS"]]
                if not pending:
                    logger.info("[MissionPlanner] MISSION COMPLETE! All tasks finished.")
                    break
                else:
                    logger.warning("[MissionPlanner] Mission Deadlock! Dependencies unresolved.")
                    break
                    
            task_id = task["id"]
            task_name = task["name"]
            
            self.twin.update_task(task_id, "IN_PROGRESS", "Spawning swarm for task.")
            
            # Formulate the sub-goal for this task
            sub_goal = f"Mission Goal: {self.goal}\nCurrent Task: Build '{task_name}'.\nReview the architecture blueprint and integrate this module properly."
            
            task_state = AiONState(
                goal=sub_goal,
                project_id=self.project_id,
                project_dir=self.target_dir,
                agent_role=self.agent_role,
                blueprint=blueprint,
                modules=[task_name],
                code_files={}
            )
            
            logger.info(f"[MissionPlanner] Spawning agents for Task: {task_id}")
            
            try:
                # Run the LangGraph execution block synchronously in a thread
                final_state = await asyncio.to_thread(graph.invoke, task_state)
                
                # Check if execution passed or failed based on runtime errors
                if final_state.get("runtime_error"):
                    self.twin.update_task(task_id, "FAILED", f"Execution failed: {final_state['runtime_error']}")
                else:
                    self.twin.update_task(task_id, "DONE", "Task executed successfully via red-green loop.")
            except Exception as e:
                logger.error(f"[MissionPlanner] Task {task_id} crashed swarm: {e}")
                self.twin.update_task(task_id, "FAILED", str(e))
                
        logger.info("[MissionPlanner] Shutting down.")
