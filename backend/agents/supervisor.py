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
            q.put({"type": "progress", "message": "🧠 Swarm Supervisor is analyzing the optimal workflow..."})
            
        sys_prompt = """You are the Swarm Supervisor for yAI.
Analyze the user's goal and decide the next best agent to handle the task.
Available Agents:
- planner (Breaks down requirements)
- mcp_client (Connects to external tools/servers if needed)
- coder (Directly writes code if requirements are simple)

Return your response in EXACTLY this JSON schema:
{
  "next_agent": "planner" | "mcp_client" | "coder",
  "reasoning": "Why you chose this agent"
}
Do not output markdown.
"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", sys_prompt),
            ("human", "Goal: {goal}")
        ])
        
        chain = prompt | self.smart_llm
        
        try:
            response = chain.invoke({"goal": state.get("goal", "")})
            content = response.content
            if isinstance(content, list):
                content = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
            
            from backend.utils.json_parser import parse_json_robustly
            data = parse_json_robustly(content)
            
            next_agent = data.get("next_agent", "planner")
            if next_agent not in ["planner", "mcp_client", "coder"]:
                next_agent = "planner"
                
            state["swarm_tasks"] = [{"next_agent": next_agent}] # Store routing decision
            
            if q:
                q.put({"type": "progress", "message": f"🤖 Supervisor delegated task to: {next_agent}"})
                
        except Exception as e:
            logger.error(f"   -> [Supervisor] Error: {e}")
            state["swarm_tasks"] = [{"next_agent": "planner"}] # Default fallback
            
        return state
