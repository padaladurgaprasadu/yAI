import json
from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
from backend.utils.logger import get_logger, measure_time

logger = get_logger(__name__)

class SwarmSupervisorAgent(BaseAgent):
    """
    Ruflo-inspired Swarm Supervisor.
    Analyzes the goal and dynamically decides which agents to route to next,
    breaking away from the rigid linear pipeline.
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
            q.put({"type": "progress", "message": "🧠 Swarm Supervisor is analyzing intent for optimal workflow..."})
            
        goal = state.get("goal", "")
        
        # Instantiate Omni Intelligence Engine for fast intent detection
        from backend.agents.router import OmniIntelligenceEngine
        omni = OmniIntelligenceEngine()
        intent_data = omni.detect_intent(goal)
        
        intent_category = intent_data.get("specific_intent", "Unknown")
        complexity = intent_data.get("complexity", "Intermediate")
        
        # Fast Track logic: Bypass heavy engineering loop for simple questions
        if "chat" in intent_category.lower() or complexity.lower() == "fast" or "simple" in complexity.lower():
            logger.info(f"   -> [Supervisor] Detected Fast Track eligible intent: {intent_category}")
            state["is_fast_track"] = True
            next_agent = "coder" # Will execute code generation quickly
        else:
            state["is_fast_track"] = False
            # Heavy pipeline
            next_agent = "mcp_client"
            
        state["swarm_tasks"] = [{"next_agent": next_agent}]
        state["complexity"] = complexity
        
        if q:
            q.put({"type": "progress", "message": f"🤖 Supervisor delegated task to: {next_agent} (Fast Track: {state['is_fast_track']})"})
                
        return state
