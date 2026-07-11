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
        
        blueprint = json.dumps(state.get("blueprint", {}))
        # Depending on how the new pipeline runs, the architect's decisions should be in state
        decisions = json.dumps(state.get("architect_decisions", []))
        
        try:
            response = self.chain.invoke({
                "blueprint": blueprint,
                "decisions": decisions
            })
            
            content = response.content.strip()
            # Clean up potential markdown formatting
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            from backend.utils.json_parser import parse_json_robustly
            memory_data = parse_json_robustly(content)
            state["memory_persisted"] = memory_data
            logger.info("[Memory] Persisted decisions to state.")
            
        except Exception as e:
            logger.error(f"[Memory] Failed to run memory agent: {e}")
            
        return state
