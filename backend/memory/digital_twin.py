import os
import json
import time
from backend.utils.logger import get_logger

logger = get_logger("AiON_DigitalTwin")

class DigitalTwinManager:
    """
    Manages the persistent project intelligence (Digital Twin) inside the generated repository.
    This prevents the AI from losing track of large projects over time.
    """
    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.aion_dir = os.path.join(project_dir, ".aion")
        self.blueprint_file = os.path.join(self.aion_dir, "blueprint.json")
        self.tasks_file = os.path.join(self.aion_dir, "tasks.json")
        
        # Ensure the .aion directory exists
        os.makedirs(self.aion_dir, exist_ok=True)
        
        # yAI Swarm Protocol: Neo4j Knowledge Graph
        self.neo4j_driver = None
        try:
            from neo4j import GraphDatabase
            # Connect to local Neo4j. If running in a swarm, agents share this graph.
            self.neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
            logger.info("[DigitalTwin] Connected to Neo4j Knowledge Graph.")
        except Exception:
            logger.warning("[DigitalTwin] Neo4j not available. Using local JSON fallback.")
        
    def _read_json(self, filepath: str) -> dict:
        if not os.path.exists(filepath):
            return {}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[DigitalTwin] Failed to read {filepath}: {e}")
            return {}
            
    def _write_json(self, filepath: str, data: dict):
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"[DigitalTwin] Failed to write {filepath}: {e}")

    # --- BLUEPRINT MANAGEMENT ---
    
    def save_blueprint(self, blueprint_data: dict):
        """Saves the high-level architecture decisions."""
        self._write_json(self.blueprint_file, blueprint_data)
        logger.info("[DigitalTwin] Blueprint saved.")
        
        # Sync to Neo4j if available
        if self.neo4j_driver:
            try:
                with self.neo4j_driver.session() as session:
                    session.run("MERGE (p:Project {id: $id}) SET p.blueprint = $bp", 
                                id=os.path.basename(self.project_dir), bp=json.dumps(blueprint_data))
            except Exception as e:
                logger.warning(f"[DigitalTwin] Neo4j sync failed: {e}")
        
    def get_blueprint(self) -> dict:
        return self._read_json(self.blueprint_file)

    def sync_agent_state(self, agent_role: str, file_path: str, code: str):
        """yAI Swarm Protocol: Real-time state syncing to Knowledge Graph"""
        if self.neo4j_driver:
            try:
                with self.neo4j_driver.session() as session:
                    session.run(
                        "MERGE (a:Agent {role: $role}) "
                        "MERGE (f:File {path: $path}) "
                        "MERGE (a)-[:WROTE]->(f) "
                        "SET f.code = $code",
                        role=agent_role, path=file_path, code=code[:2000] # truncating for safety
                    )
            except Exception as e:
                logger.warning(f"[DigitalTwin] Failed to sync agent state to Neo4j: {e}")

    # --- TASK (DAG) MANAGEMENT ---
    
    def initialize_tasks(self, dag_tasks: list):
        """
        Initializes the tasks.json with the given DAG.
        If a task already exists, it preserves its status.
        """
        existing_data = self._read_json(self.tasks_file)
        existing_tasks = existing_data.get("tasks", {})
        
        new_tasks_dict = {}
        for task in dag_tasks:
            t_id = task.get("id")
            if t_id in existing_tasks:
                new_tasks_dict[t_id] = existing_tasks[t_id]
            else:
                new_tasks_dict[t_id] = {
                    "id": t_id,
                    "name": task.get("name", t_id),
                    "depends_on": task.get("depends_on", []),
                    "status": "PENDING", # PENDING, IN_PROGRESS, DONE, FAILED
                    "logs": [],
                    "created_at": time.time(),
                    "updated_at": time.time()
                }
                
        self._write_json(self.tasks_file, {"tasks": new_tasks_dict})
        logger.info(f"[DigitalTwin] Initialized {len(new_tasks_dict)} tasks.")
        
    def get_tasks(self) -> dict:
        return self._read_json(self.tasks_file).get("tasks", {})
        
    def update_task(self, task_id: str, status: str, log_message: str = None):
        """Updates the status and logs of a specific task."""
        data = self._read_json(self.tasks_file)
        tasks = data.get("tasks", {})
        
        if task_id in tasks:
            tasks[task_id]["status"] = status
            tasks[task_id]["updated_at"] = time.time()
            if log_message:
                tasks[task_id]["logs"].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {log_message}")
            self._write_json(self.tasks_file, data)
            logger.info(f"[DigitalTwin] Task '{task_id}' updated to {status}.")
        else:
            logger.warning(f"[DigitalTwin] Task '{task_id}' not found for update.")
            
    def get_next_pending_task(self) -> dict:
        """
        Finds the next PENDING task whose dependencies are all DONE.
        Returns the task object or None.
        """
        tasks = self.get_tasks()
        
        for t_id, task in tasks.items():
            if task.get("status") == "PENDING":
                deps = task.get("depends_on", [])
                # Check if all dependencies are DONE
                can_run = True
                for dep_id in deps:
                    dep_task = tasks.get(dep_id)
                    if not dep_task or dep_task.get("status") != "DONE":
                        can_run = False
                        break
                
                if can_run:
                    return task
                    
        return None
