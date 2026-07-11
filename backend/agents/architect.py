import json
from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
from backend.memory.neo4j_client import Neo4jClient
from backend.memory.chroma_client import ChromaClient
from backend.utils.logger import get_logger, measure_time

logger = get_logger(__name__)

class ArchitectAgent(BaseAgent):
    """
    The Architect Agent designs the tech stack and blueprint based on the goal and modules.
    Now equipped with Semantic Memory (RAG) to learn from past projects!
    """
    def __init__(self):
        super().__init__()
        # We will build the prompt dynamically in the run method to access state

    @measure_time(logger)
    def run(self, state: AiONState) -> AiONState:
        agent_role = state.get("agent_role", "Fullstack Web Developer")
        project_id = state.get("project_id")
        
        try:
            from backend.api_real import stream_queues
            q = stream_queues.get(project_id)
        except ImportError:
            q = None
            
        if q:
            q.put({"type": "agent_state", "agent": "architect"})
            q.put({"type": "timeline", "title": "Analyzing requirements...", "reason": f"Role selected: {agent_role}", "status": "active"})
            
        logger.info(f"[Architect] Designing system architecture for role: {agent_role}...")
        
        # Dynamically define architectural rules based on role
        if "Research" in agent_role:
            tech_rule = "CRITICAL ARCHITECTURE RULE: You MUST design a research document structure instead of software. Your 'tech_stack' should list the methodologies or research fields involved. Your 'file_structure' MUST only include markdown files (e.g., 'research_paper.md', 'literature_review.md', 'methodology.md'). Do NOT include code files like package.json or server.js."
        elif "Fullstack" in agent_role or "Web" in agent_role or "UI" in agent_role:
            framework_rules = "4. CRITICAL REACT REQUIREMENT: Do NOT include 'client/public/index.html', 'client/src/index.js', 'client/src/main.jsx', or 'client/package.json' in your file_structure! The backend will automatically scaffold the React app using Vite. You ONLY need to list the components you create (e.g., 'client/src/App.jsx', 'client/src/components/Dashboard.jsx') and the root 'package.json'.\n5. CRITICAL COMPONENT REQUIREMENT: Every single React component (e.g. Dashboard, Login, Navbar) you plan to use MUST be explicitly listed as a separate file with a '.jsx' extension in 'file_structure'. If you don't list it, it will never be generated and the app will crash with 'Module not found'.\n6. CRITICAL RUN REQUIREMENT: You MUST include a root 'package.json' with a 'dev' script that uses 'concurrently' to run the backend and the Vite frontend at the same time."
            tech_rule = f"CRITICAL ARCHITECTURE RULE: You MUST ALWAYS build a FULLSTACK application with a Node.js (Express) backend and a React frontend. \nCRITICAL DB RULE: You MUST use PostgreSQL for the database using the 'pg' library. IMPORTANT: Hardcode the database connection string or pool config to use user 'postgres', password 'postgres', host 'localhost', port 5432, database 'postgres' as a fallback if env vars are missing.\nCRITICAL PORT RULE: Your backend MUST run on PORT 5000. Your React frontend MUST run on PORT 3000. \n{framework_rules}"
        else:
            tech_rule = "CRITICAL ARCHITECTURE RULE: You MUST build a Python-based application using frameworks suitable for ML/Data Science (e.g., Streamlit, FastAPI, Flask). Do NOT use React or Express. The app must run on port 3000 for the iframe preview (e.g., streamlit run app.py --server.port=3000). You MUST include a 'requirements.txt' file and a 'start.sh' or 'start.bat' script to launch it."
            
        from backend.agents.base import GLOBAL_AGENT_RULES
        from backend.agents.orchestration_prompts import ARCHITECT_PROMPT
        system_prompt = GLOBAL_AGENT_RULES + "\\n\\n" + tech_rule + "\\n\\n" + ARCHITECT_PROMPT
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Goal: {goal}\nModules: {modules}\n\nPast Projects Context:\n{context}")
        ])
        chain = prompt | self.llm

        
        # Search ChromaDB for past projects
        try:
            vector_db = ChromaClient()
            past_projects = vector_db.find_similar_projects(state["goal"])
            
            if past_projects:
                print("   -> [Semantic Memory] Found similar past projects! Using them for inspiration.")
                context = "\n---\n".join(past_projects)
            else:
                context = "No past projects found."
        except Exception as e:
            print(f"   -> [WARNING] Could not connect to Semantic Memory: {e}")
            context = "No past projects found."
        
        # Ask the AI for the blueprint
        response = chain.invoke({
            "goal": state["goal"],
            "modules": ", ".join(state["modules"]),
            "context": context
        })
        
        content = response.content
        if isinstance(content, list):
            content = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
            
        try:
            # Parse the JSON response
            from backend.utils.json_parser import parse_json_robustly
            blueprint = parse_json_robustly(content)
            print(f"   -> Tech Stack Selected: {blueprint.get('tech_stack', [])}")
            state["blueprint"] = blueprint
            state["semantic_context"] = context
            
            project_dir = state.get("project_dir")
            if project_dir:
                try:
                    from backend.memory.digital_twin import DigitalTwinManager
                    twin = DigitalTwinManager(project_dir)
                    twin.save_blueprint(blueprint)
                except Exception as e:
                    logger.error(f"[Architect] Failed to save to Digital Twin: {e}")
            
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                tech_stack_str = ", ".join(blueprint.get('tech_stack', [])[:3])
                q.put({"type": "timeline", "title": f"🏗️ Architect: Selected {tech_stack_str}", "reason": "✅ Decision logged to memory.\n✅ Similar past project found.", "status": "done"})
            
            # Log decision to memory
            try:
                client = Neo4jClient()
                rationale = f"Selected tech stack: {', '.join(blueprint.get('tech_stack', []))}"
                client.log_decision(state['project_id'], "Architect", rationale)
                client.close()
                print("   -> [Memory] Architectural decision saved to brain.")
            except Exception as e:
                print(f"   -> [WARNING] Could not save to neo4j memory: {e}")
                
        except json.JSONDecodeError:
            print("   -> [WARNING] Failed to parse Architect's JSON. Using raw response.")
            state["blueprint"] = {"raw_response": response.content}
            
        return state
