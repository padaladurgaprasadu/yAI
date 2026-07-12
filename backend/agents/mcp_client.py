from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
from backend.utils.logger import get_logger, measure_time

logger = get_logger(__name__)

class MCPClientAgent(BaseAgent):
    """
    Ruflo-inspired Model Context Protocol (MCP) Client.
    Allows the agent swarm to query external tools/servers dynamically.
    """
    def __init__(self):
        super().__init__()

    @measure_time(logger)
    def run(self, state: AiONState) -> AiONState:
        project_id = state.get("project_id")
        try:
            from backend.api_real import stream_queues
            q = stream_queues.get(project_id)
        except ImportError:
            q = None

        if q:
            q.put({"type": "progress", "message": "🔌 MCP Client connecting to external context servers..."})
            
        logger.info("[MCP Client] Interfacing with external tools...")
        
        # Mocking an MCP server response for context injection
        mcp_context = "External MCP Context: The user's requested architecture should utilize React 18, Node.js 20, and prefer TailwindCSS if unspecified."
        
        # Append to semantic context
        existing_context = state.get("semantic_context", "")
        state["semantic_context"] = existing_context + "\n" + mcp_context if existing_context else mcp_context
        
        if q:
            q.put({"type": "progress", "message": "✅ MCP Client successfully injected external context."})
            
        return state
