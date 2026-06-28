from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
from backend.utils.logger import get_logger, measure_time

logger = get_logger(__name__)

class PlannerAgent(BaseAgent):
    """
    The Planner Agent breaks down the user's high-level goal into smaller, manageable modules.
    """
    def __init__(self):
        super().__init__()

    @measure_time(logger)
    def run(self, state: AiONState) -> AiONState:
        agent_role = state.get("agent_role", "Fullstack Web Developer")
        logger.info(f"[Planner] Breaking down goal for role: {agent_role}...")
        
        if "Research" in agent_role:
            sys_prompt = "You are an AI {agent_role}. The user has a research goal. You MUST provide a NOVEL APPROACH to this research. Return a JSON object with a key 'tasks' which is a list of objects. Each object should have 'id' (string, no spaces), 'name' (string), and 'depends_on' (list of string ids it depends on). Do not write software code."
        else:
            sys_prompt = "You are an AI {agent_role} Planner. Given a user's goal, break it down into a logical DAG (Directed Acyclic Graph) of tasks. Return ONLY valid JSON with a key 'tasks' which is a list of objects. Each object should have 'id' (string, e.g. 'auth'), 'name' (string, e.g. 'Authentication'), and 'depends_on' (list of string ids it depends on, e.g. [] or ['db']). E.g. {{\"tasks\": [{{\"id\": \"db\", \"name\": \"Database\", \"depends_on\": []}}, {{\"id\": \"auth\", \"name\": \"Authentication\", \"depends_on\": [\"db\"]}}]}}"
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", sys_prompt),
            ("human", "Goal: {goal}")
        ])
        chain = prompt | self.llm
        
        goal = state["goal"]
        
        # Ask the AI to generate the DAG
        response = chain.invoke({
            "goal": goal,
            "agent_role": agent_role
        })
        
        content = response.content
        if isinstance(content, list):
            content = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
                
        # Parse the JSON DAG
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        import json
        try:
            dag_data = json.loads(content)
            dag_tasks = dag_data.get("tasks", [])
            # Extract just the names for the legacy 'modules' field so Architect still works
            modules_list = [task.get("name", task.get("id")) for task in dag_tasks]
            print(f"   -> [Planner] DAG generated with {len(dag_tasks)} nodes.")
        except Exception as e:
            print(f"   -> [Planner] Failed to parse DAG JSON: {e}")
            modules_list = ["Core System"]
            dag_tasks = [{"id": "core", "name": "Core System", "depends_on": []}]
        
        # Update and return the state
        state["modules"] = modules_list
        state["dag_tasks"] = dag_tasks
        return state
