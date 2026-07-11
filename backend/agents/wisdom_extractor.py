import json
from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
from backend.utils.logger import get_logger, measure_time

logger = get_logger(__name__)

class WisdomExtractorAgent(BaseAgent):
    """
    yAI Swarm Protocol: The Self-Learning Module.
    Extracts root causes and solutions from resolved bugs and stores them
    in ChromaDB as 'Wisdom Vectors' for future swarms to learn from.
    """
    def __init__(self):
        super().__init__()
        try:
            from backend.memory.chroma_client import ChromaClient
            self.chroma = ChromaClient()
            self.chroma_client = self.chroma.client
            self.collection = self.chroma_client.get_or_create_collection(
                name="aion_wisdom_store", 
                embedding_function=self.chroma.embedding_fn
            )
            logger.info("[WisdomExtractor] Connected to ChromaDB Wisdom Store.")
        except Exception as e:
            logger.warning(f"[WisdomExtractor] ChromaDB initialization failed: {e}. Self-learning disabled.")

    @measure_time(logger)
    def run(self, state: AiONState, q=None) -> AiONState:
        if not self.chroma_client:
            return state
            
        runtime_error = state.get("runtime_error")
        audit_feedback = state.get("audit_feedback")
        
        # If there were errors that were eventually resolved (we reached the end of the graph)
        if runtime_error or (audit_feedback and "APPROVED" not in audit_feedback):
            logger.info("[WisdomExtractor] Extracting Wisdom from resolved errors...")
            
            from backend.agents.base import GLOBAL_AGENT_RULES
            prompt = ChatPromptTemplate.from_messages([
                ("system", GLOBAL_AGENT_RULES + """
ROLE: Wisdom Extractor
GOAL: Extract root causes and solutions from resolved bugs and store them as 'Wisdom Vectors'.

OUTPUT SCHEMA:
{
  "root_cause": "...",
  "solution_rule": "..."
}

RULES:
- Only return valid JSON.
"""),
                ("human", "Error encountered: {error}\n\nExtract the core rule to prevent this in the future.")
            ])
            
            try:
                # We combine errors for context
                combined_errors = f"Runtime Error: {runtime_error}\nAudit Feedback: {audit_feedback}"
                messages = prompt.format_messages(error=combined_errors)
                
                response = self.fast_llm.invoke(messages)
                content = response.content.replace("```json", "").replace("```", "").strip()
                wisdom = json.loads(content)
                
                # Store in ChromaDB
                doc_id = f"wisdom_{state.get('project_id', 'unknown')}_{hash(combined_errors)}"
                self.collection.add(
                    documents=[wisdom["solution_rule"]],
                    metadatas=[{"root_cause": wisdom["root_cause"], "project": state.get("project_id", "")}],
                    ids=[doc_id]
                )
                logger.info(f"[WisdomExtractor] Stored new wisdom rule: {wisdom['solution_rule']}")
                
                if q:
                    q.put({"type": "timeline", "title": "Self-Learning Triggered", "reason": f"Learned: {wisdom['solution_rule'][:50]}...", "status": "success"})
                    
            except Exception as e:
                logger.warning(f"[WisdomExtractor] Failed to extract wisdom: {e}")
                
        return state
