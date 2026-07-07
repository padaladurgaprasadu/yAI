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
    def run(self, state: AiONState, q=None) -> AiONState:
        agent_role = state.get("agent_role", "Fullstack Web Developer")
        logger.info(f"[Planner] Breaking down goal for role: {agent_role}...")
        
        from backend.agents.base import GLOBAL_AGENT_RULES
        sys_prompt = GLOBAL_AGENT_RULES + f"""
ROLE: Planner
GOAL: Break the goal into 3-8 functional modules a senior engineer would recognize as a complete MVP scope for this request — not more, not less. Right-size the scope. Over-scoping is a junior-agent failure mode.

OUTPUT SCHEMA:
{{
  "tasks": [
    {{"id": "string (no spaces)", "name": "string", "why_needed": "string", "priority": "core" | "nice_to_have", "depends_on": ["string (ids)"]}}
  ],
  "explicit_assumptions": ["state anything you inferred that wasn't asked for directly"],
  "out_of_scope": ["things a user might expect but you're deliberately excluding, and why"]
}}

RULES:
- Every module must map to something the Coder agent can actually build in this pass — no vague modules like "scalability".
- Ensure tasks can form a valid DAG via depends_on.
- Output ONLY valid JSON, no markdown.
"""
        goal = state["goal"]
        image_url = state.get("image", None)
        
        from langchain_core.messages import SystemMessage, HumanMessage
        
        if image_url:
            sys_prompt += "\n\nCRITICAL UI ARCHITECT RULE: The user has provided an image screenshot of a UI they want to build. You MUST analyze this screenshot visually. In your generated tasks/modules, explicitly include frontend components that match the layout, features, and interactive elements visible in the screenshot (e.g. 'HeroSection', 'SidebarNav', 'ProductGrid')."
            human_content = [{"type": "text", "text": f"Goal: {goal}"}]
            
            # image_url might be a single string or a list of strings
            if isinstance(image_url, list):
                for img in image_url:
                    human_content.append({"type": "image_url", "image_url": {"url": img}})
            else:
                human_content.append({"type": "image_url", "image_url": {"url": image_url}})
            
            semantic_context = state.get("semantic_context", "")
            if semantic_context:
                human_content.append({"type": "text", "text": f"\n\nInnovation Brief & Research Context:\n{semantic_context}"})
        else:
            semantic_context = state.get("semantic_context", "")
            if semantic_context:
                human_content = f"Goal: {goal}\n\nInnovation Brief & Research Context:\n{semantic_context}"
            else:
                human_content = f"Goal: {goal}"
            
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=human_content)
        ]
        
        # Ask the AI to generate the DAG
        response = self.llm.invoke(messages)
        
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
            print(f"   -> [Planner] Failed to parse JSON: {e}")
            modules_list = ["Core System"]
            dag_tasks = [{"id": "core", "name": "Core System", "depends_on": []}]
            
        if q:
            modules_str = "\n".join([f"✅ {m}" for m in modules_list[:5]])
            q.put({"type": "timeline", "title": f"🧠 Planner: {len(modules_list)} modules identified.", "reason": modules_str, "status": "active"})
        
        # Update and return the state
        state["modules"] = modules_list
        state["dag_tasks"] = dag_tasks
        
        project_dir = state.get("project_dir")
        if project_dir:
            try:
                from backend.memory.digital_twin import DigitalTwinManager
                twin = DigitalTwinManager(project_dir)
                twin.initialize_tasks(dag_tasks)
            except Exception as e:
                logger.error(f"[Planner] Failed to initialize Digital Twin: {e}")
                
        return state
