import os
from neo4j import GraphDatabase
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class MemoryAgent:
    """
    Enterprise Phase 1 Feature: Deeper Long-Term Project Memory.
    Connects to Neo4j to store and retrieve long-term contextual memories about projects,
    enabling the AI to recall architectural decisions from previous builds.
    """
    def __init__(self):
        # We default to the docker-compose neo4j credentials
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "aion_password123")
        self.driver = None
        
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            logger.info("[MemoryAgent] Connected to Neo4j Long-Term Memory.")
        except Exception as e:
            logger.warning(f"[MemoryAgent] Could not connect to Neo4j. Long-term memory is disabled. {e}")

    def close(self):
        if self.driver:
            self.driver.close()

    def memorize_project(self, project_id: str, goal: str, agent_role: str, blueprint: dict):
        """
        Stores the high-level architecture of a project in the graph database.
        """
        if not self.driver:
            return
            
        try:
            with self.driver.session() as session:
                session.execute_write(self._create_project_node, project_id, goal, agent_role, blueprint)
                logger.info(f"[MemoryAgent] Memorized project '{project_id}' successfully.")
        except Exception as e:
            logger.error(f"[MemoryAgent] Failed to memorize project: {e}")

    @staticmethod
    def _create_project_node(tx, project_id, goal, agent_role, blueprint):
        # Creates a Project node and links it to Module nodes based on the blueprint
        query = (
            "MERGE (p:Project {id: $project_id}) "
            "SET p.goal = $goal, p.agent_role = $agent_role "
            "RETURN p"
        )
        tx.run(query, project_id=project_id, goal=goal, agent_role=agent_role)
        
        modules = blueprint.get("modules", [])
        for mod in modules:
            mod_query = (
                "MATCH (p:Project {id: $project_id}) "
                "MERGE (m:Module {name: $module_name}) "
                "MERGE (p)-[:CONTAINS]->(m)"
            )
            tx.run(mod_query, project_id=project_id, module_name=mod)
