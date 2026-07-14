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
        
        # Extract past knowledge from Phase 4 Graph
        project_id = state.get("project_id", "default_project")
        try:
            from backend.memory.kg_store import KnowledgeGraphStore
            kg = KnowledgeGraphStore()
            past_knowledge = kg.get_knowledge(project_id)
            if past_knowledge:
                logger.info(f"[Planner] Loaded Knowledge Graph context for {project_id}")
                kg_context = "PAST ENTERPRISE KNOWLEDGE:\n"
                import json
                for key, val in past_knowledge.items():
                    kg_context += f"[{key}]: {json.dumps(val)}\n"
                state["semantic_context"] = state.get("semantic_context", "") + "\n\n" + kg_context
                
                if q:
                    q.put({"type": "progress", "message": "🧠 Loaded past project knowledge graph context!"})
        except Exception as e:
            logger.warning(f"[Planner] Failed to query Knowledge Graph: {e}")
            
        from backend.agents.base import GLOBAL_AGENT_RULES
        from backend.agents.orchestration_prompts import PLANNER_PROMPT
        sys_prompt = GLOBAL_AGENT_RULES + "\n\n" + PLANNER_PROMPT
        goal = state["goal"]
        image_url = state.get("image", None)
        
        from langchain_core.messages import SystemMessage, HumanMessage
        
        semantic_context = state.get("semantic_context", "")
        repo_context = state.get("repository_context", "")
        if repo_context and "No existing repository" not in repo_context:
            semantic_context += f"\n\nREPOSITORY INTELLIGENCE (Internal Knowledge Graph):\n{repo_context}"
            
        if image_url:
            sys_prompt += "\n\nCRITICAL UI ARCHITECT RULE: The user has provided an image screenshot of a UI they want to build. You MUST analyze this screenshot visually. In your generated tasks/modules, explicitly include frontend components that match the layout, features, and interactive elements visible in the screenshot (e.g. 'HeroSection', 'SidebarNav', 'ProductGrid')."
            human_content = [{"type": "text", "text": f"Goal: {goal}"}]
            
            # image_url might be a single string or a list of strings
            if isinstance(image_url, list):
                for img in image_url:
                    human_content.append({"type": "image_url", "image_url": {"url": img}})
            else:
                human_content.append({"type": "image_url", "image_url": {"url": image_url}})
            
            if semantic_context:
                human_content.append({"type": "text", "text": f"\n\nInnovation Brief & Research Context:\n{semantic_context}"})
                
        else:
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
        
        from backend.utils.json_parser import parse_json_robustly
        try:
            dag_data = parse_json_robustly(content)
            dag_tasks = dag_data.get("tasks", [])
            # Extract just the names for the legacy 'modules' field so Architect still works
            modules_list = [task.get("name", task.get("id")) for task in dag_tasks]
            print(f"   -> [Planner] DAG generated with {len(dag_tasks)} nodes.")
        except Exception as e:
            print(f"   -> [Planner] Failed to parse JSON: {e}")
            modules_list = []
            dag_tasks = []

        # ⚡ SMART FALLBACK: If 0 modules returned, auto-generate from goal keywords
        if not modules_list:
            print("   -> [Planner] 0 modules detected — using smart keyword fallback...")
            goal_lower = state["goal"].lower()
            # Map common project types to sensible module sets
            if any(w in goal_lower for w in ["restaurant", "food", "menu", "order"]):
                modules_list = ["Menu Management", "Order Processing", "Table Booking", "User Auth", "Kitchen Dashboard", "Reports"]
            elif any(w in goal_lower for w in ["library", "book", "borrow", "catalog"]):
                modules_list = ["Book Catalog", "User Management", "Borrowing System", "Search & Filter", "Admin Dashboard", "Reports"]
            elif any(w in goal_lower for w in ["ecommerce", "e-commerce", "shop", "store", "product"]):
                modules_list = ["Product Catalog", "Shopping Cart", "User Auth", "Payment Gateway", "Order Tracking", "Admin Panel"]
            elif any(w in goal_lower for w in ["hospital", "clinic", "doctor", "patient", "medical"]):
                modules_list = ["Patient Records", "Appointment Booking", "Doctor Management", "Billing", "Medical Reports", "Admin"]
            elif any(w in goal_lower for w in ["school", "college", "student", "course", "education"]):
                modules_list = ["Student Management", "Course Management", "Attendance", "Grades", "Fee Management", "Reports"]
            elif any(w in goal_lower for w in ["crm", "customer", "sales", "lead"]):
                modules_list = ["Contact Management", "Lead Tracking", "Sales Pipeline", "Reports", "User Auth", "Dashboard"]
            elif any(w in goal_lower for w in ["blog", "cms", "content", "post", "article"]):
                modules_list = ["Content Editor", "Post Management", "User Auth", "Categories & Tags", "Comments", "SEO"]
            elif any(w in goal_lower for w in ["task", "todo", "project management", "kanban"]):
                modules_list = ["Task Management", "Project Board", "Team Management", "Notifications", "User Auth", "Dashboard"]
            else:
                # Generic fullstack app modules
                modules_list = ["User Authentication", "Core Features", "Dashboard", "Data Management", "API Layer", "UI Components"]
            dag_tasks = [{"id": f"mod_{i}", "name": m, "depends_on": []} for i, m in enumerate(modules_list)]
            print(f"   -> [Planner] Smart fallback generated {len(modules_list)} modules: {modules_list}")

            
        if q:
            modules_str = "\n".join([f"✅ {m}" for m in modules_list[:5]])
            q.put({"type": "timeline", "title": f"yAI Template Intelligence: {len(modules_list)} modules mapped", "reason": modules_str, "status": "active"})
        
        # Update and return the state
        state["modules"] = modules_list
        state["dag_tasks"] = dag_tasks

        # Auto-detect complexity so Architect can choose fast vs Enterprise mode
        n = len(modules_list)
        if n <= 3:
            state["complexity"] = "Simple"
        elif n <= 6:
            state["complexity"] = "Large"
        else:
            state["complexity"] = "Enterprise"
        print(f"   -> [Planner] Complexity detected: {state['complexity']} ({n} modules)")
        
        project_dir = state.get("project_dir")
        if project_dir:
            try:
                from backend.memory.digital_twin import DigitalTwinManager
                twin = DigitalTwinManager(project_dir)
                twin.initialize_tasks(dag_tasks)
            except Exception as e:
                logger.error(f"[Planner] Failed to initialize Digital Twin: {e}")
                
        return state
