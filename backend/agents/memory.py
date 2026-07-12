import json
from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class MemoryAgent(BaseAgent):
    """
    The Memory Agent persists reusable architecture decisions and blueprint embeddings for future requests.
    """
    def __init__(self):
        super().__init__()
        from backend.agents.base import GLOBAL_AGENT_RULES
        from backend.agents.orchestration_prompts import MEMORY_PROMPT
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", GLOBAL_AGENT_RULES + "\n\n" + MEMORY_PROMPT),
            ("human", "Blueprint: {blueprint}\nDecisions: {decisions}")
        ])
        self.chain = self.prompt | self.llm

    def run(self, state: AiONState) -> AiONState:
        logger.info("[Memory] Persisting decisions...")
        
        goal = state.get("goal", "")
        project_id = state.get("project_id", "default_project")
        blueprint_data = state.get("blueprint", {})
        blueprint = json.dumps(blueprint_data)
        decisions = json.dumps(state.get("architect_decisions", []))
        
        try:
            response = self.chain.invoke({
                "blueprint": blueprint,
                "decisions": decisions
            })
            
            content = response.content.strip()
            from backend.utils.json_parser import parse_json_robustly
            memory_data = parse_json_robustly(content)
            
            # Adaptive Conversational Memory (Ruflo style)
            # Create a rolling summary of the memory for future workflow injections
            rolling_summary = memory_data.get("summary", "No summary generated.")
            existing_context = state.get("semantic_context", "")
            
            if existing_context:
                state["semantic_context"] = f"{existing_context}\n[Memory Summary]: {rolling_summary}"
            else:
                state["semantic_context"] = f"[Memory Summary]: {rolling_summary}"
                
            state["memory_persisted"] = memory_data
            
            # 1. Store in ChromaDB Vector Database for Semantic Cache & RAG
            try:
                from backend.memory.chroma_client import ChromaClient
                chroma = ChromaClient()
                chroma.store_blueprint(project_id, goal, blueprint)
                logger.info("[Memory] Blueprint saved to ChromaDB vector store.")
            except Exception as ve:
                logger.warning(f"[Memory] Failed to save to ChromaDB: {ve}")
                
            # 2. Store in Neo4j Graph Database
            try:
                from backend.memory.neo4j_client import Neo4jClient
                neo = Neo4jClient()
                query = """
                MERGE (p:Project {id: $project_id})
                SET p.goal = $goal, p.timestamp = timestamp()
                MERGE (d:Decision {id: $decision_id})
                SET d.content = $content, d.type = "architecture"
                MERGE (p)-[:HAS_DECISION]->(d)
                """
                neo.run_query(query, {
                    "project_id": project_id,
                    "goal": goal,
                    "decision_id": f"dec-{project_id[:6]}",
                    "content": json.dumps(memory_data)
                })
                logger.info("[Memory] Decision relations synchronized with Neo4j.")
            except Exception as ge:
                logger.warning(f"[Memory] Failed to sync to Neo4j graph database: {ge}")
                
            # 3. Store in Local SQLite Enterprise Knowledge Graph (Phase 4)
            try:
                from backend.memory.kg_store import KnowledgeGraphStore
                kg = KnowledgeGraphStore()
                kg.store_knowledge(project_id, "architecture_decisions", memory_data)
                kg.store_knowledge(project_id, "user_preferences", state.get("design_tokens", {}))
                logger.info("[Memory] Successfully persisted to Local SQLite Knowledge Graph.")
            except Exception as kg_err:
                logger.warning(f"[Memory] Failed to sync to Local Knowledge Graph: {kg_err}")
                
            logger.info("[Memory] Persisted decisions to state.")
            
        except Exception as e:
            logger.error(f"[Memory] Failed to run memory agent: {e}")
            
        return state
