import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

class Neo4jClient:
    def __init__(self):
        # We will load these from the .env file
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "aion_password123")
        
        if password == "your_neo4j_password_here":
            print("[WARNING] Please update your NEO4J_PASSWORD in the .env file!")
            
        try:
            # Set a fast timeout so if Aura is paused, it fails instantly instead of hanging
            self.driver = GraphDatabase.driver(uri, auth=(user, password), connection_timeout=3.0)
        except Exception as e:
            print(f"[Neo4j WARNING] Could not connect to Neo4j Aura (is it paused?). Memory logging disabled. Error: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def run_query(self, query, parameters=None):
        if not self.driver:
            return []
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters)
                return [record.data() for record in result]
        except Exception as e:
            print(f"[Neo4j WARNING] Query failed (Aura might be paused): {e}")
            return []

    def log_project(self, project_id, goal):
        """Creates a Project node in the database."""
        query = """
        MERGE (p:Project {id: $project_id})
        SET p.goal = $goal, p.created_at = timestamp()
        RETURN p
        """
        self.run_query(query, {"project_id": project_id, "goal": goal})

    def log_decision(self, project_id, agent_name, rationale):
        """Logs a decision made by an agent and links it to the project."""
        query = """
        MATCH (p:Project {id: $project_id})
        CREATE (d:Decision {
            agent: $agent_name, 
            rationale: $rationale, 
            timestamp: timestamp()
        })
        CREATE (p)-[:HAS_DECISION]->(d)
        RETURN d
        """
        self.run_query(query, {
            "project_id": project_id,
            "agent_name": agent_name,
            "rationale": rationale
        })

    def get_project_decisions(self, project_id):
        """Retrieves all decisions for a specific project."""
        query = """
        MATCH (p:Project {id: $project_id})-[:HAS_DECISION]->(d:Decision)
        RETURN d.agent AS agent, d.rationale AS rationale
        ORDER BY d.timestamp ASC
        """
        return self.run_query(query, {"project_id": project_id})
