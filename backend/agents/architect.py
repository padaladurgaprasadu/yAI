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
        logger.info(f"[Architect] Designing system architecture for role: {agent_role}...")
        
        # Dynamically define architectural rules based on role
        if "Research" in agent_role:
            tech_rule = "CRITICAL ARCHITECTURE RULE: You MUST design a research document structure instead of software. Your 'tech_stack' should list the methodologies or research fields involved. Your 'file_structure' MUST only include markdown files (e.g., 'research_paper.md', 'literature_review.md', 'methodology.md'). Do NOT include code files like package.json or server.js."
        elif "Fullstack" in agent_role or "Web" in agent_role or "UI" in agent_role:
            framework_rules = "4. CRITICAL REACT REQUIREMENT: Do NOT include 'client/public/index.html', 'client/src/index.js', 'client/src/main.jsx', or 'client/package.json' in your file_structure! The backend will automatically scaffold the React app using Vite. You ONLY need to list the components you create (e.g., 'client/src/App.jsx', 'client/src/components/Dashboard.jsx') and the root 'package.json'.\n5. CRITICAL COMPONENT REQUIREMENT: Every single React component (e.g. Dashboard, Login, Navbar) you plan to use MUST be explicitly listed as a separate file with a '.jsx' extension in 'file_structure'. If you don't list it, it will never be generated and the app will crash with 'Module not found'.\n6. CRITICAL RUN REQUIREMENT: You MUST include a root 'package.json' with a 'dev' script that uses 'concurrently' to run the backend and the Vite frontend at the same time.\n7. TEMPLATE INTELLIGENCE ENGINE: You MUST extract the desired website theme, UI style, primary colors, and specific styling instructions based on the user's domain and input. Compose a unique design approach. You MUST include a 'designSystem' object containing 'domain', 'theme', 'style', 'primaryColor', 'typography', and 'instructions' in your JSON."
            tech_rule = f"CRITICAL ARCHITECTURE RULE: You MUST ALWAYS build a FULLSTACK application with a Node.js (Express) backend and a React frontend. \nCRITICAL DB RULE: You MUST use PostgreSQL for the database using the 'pg' library. IMPORTANT: Hardcode the database connection string or pool config to use user 'postgres', password 'postgres', host 'localhost', port 5432, database 'postgres' as a fallback if env vars are missing.\nCRITICAL PORT RULE: Your backend MUST run on PORT 5000. Your React frontend MUST run on PORT 3000. \n{framework_rules}"
        else:
            tech_rule = "CRITICAL ARCHITECTURE RULE: You MUST build a Python-based application using frameworks suitable for ML/Data Science (e.g., Streamlit, FastAPI, Flask). Do NOT use React or Express. The app must run on port 3000 for the iframe preview (e.g., streamlit run app.py --server.port=3000). You MUST include a 'requirements.txt' file and a 'start.sh' or 'start.bat' script to launch it."
            
        system_prompt = f"You are a Senior Systems Architect acting as a {agent_role}. Given a goal and a list of modules, design a technology stack and a blueprint. Use the provided Past Projects as inspiration if relevant.\n\n{tech_rule}\n\nMULTILINGUAL CAPABILITY: Any notes, descriptions, or comments you generate in the blueprint MUST be written in the same language as the user's Goal.\n\nReturn ONLY valid JSON with four keys: 'tech_stack' (a list of strings), 'designSystem' (a dictionary with style tokens, ONLY if Web/UI project), 'blueprint_notes' (a short string), and 'file_structure' (a list of 5 to 10 file paths needed for the app). Do not include markdown formatting or backticks, just the raw JSON."
        
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
            blueprint = json.loads(content.strip().strip('`').replace('json\n', ''))
            print(f"   -> Tech Stack Selected: {blueprint.get('tech_stack', [])}")
            state["blueprint"] = blueprint
            state["semantic_context"] = context
            
            # Log decision to memory
            try:
                client = Neo4jClient()
                rationale = f"Selected tech stack: {', '.join(blueprint.get('tech_stack', []))}"
                client.log_decision(state['project_id'], "Architect", rationale)
                client.close()
                print("   -> [Memory] Architectural decision saved to brain.")
            except Exception as e:
                print(f"   -> [WARNING] Could not save to memory: {e}")
                
        except json.JSONDecodeError:
            print("   -> [WARNING] Failed to parse Architect's JSON. Using raw response.")
            state["blueprint"] = {"raw_response": response.content}
            
        return state
