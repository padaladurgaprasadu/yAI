import os
import sys

# Patch sqlite3 for ChromaDB on Render (older Ubuntu bases have sqlite < 3.35)
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import subprocess
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import re
from dotenv import load_dotenv
from fastapi import Request, Depends
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Make sure Python can find our backend module when running from the CLI
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.orchestrator.graph import build_plan_graph, build_generate_graph
from backend.orchestrator.state import AiONState
from backend.memory.neo4j_client import Neo4jClient
from backend.memory.chroma_client import ChromaClient

load_dotenv()

app = FastAPI(title="AiON API")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "AiON Backend is running"}

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

import jwt

import jwt
from jwt import PyJWKClient

def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized: Missing Bearer Token.")
    
    token = authorization.split(" ")[1]
    
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    supabase_url = os.getenv("SUPABASE_URL")
    
    # If no keys are provided, we assume local development mode 
    if not jwt_secret and not supabase_url:
        if len(token) < 10:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid Token.")
        return token
        
    try:
        # The easiest and most common way: Decode using the HS256 JWT secret
        if jwt_secret:
            try:
                decoded = jwt.decode(token, jwt_secret, algorithms=["HS256"], options={"verify_aud": False})
                return decoded
            except Exception as hs256_err:
                # If HS256 fails (e.g. because they use RS256/ES256), fallback to JWKS if possible
                if supabase_url:
                    # Note: Supabase requires apikey header for /auth/v1/jwks in some setups
                    import json, urllib.request
                    jwks_url = f"{supabase_url}/auth/v1/jwks"
                    
                    req = urllib.request.Request(jwks_url)
                    anon_key = os.getenv("SUPABASE_ANON_KEY", "")
                    if anon_key:
                        req.add_header("apikey", anon_key)
                    
                    with urllib.request.urlopen(req) as response:
                        jwks_data = json.loads(response.read().decode())
                        
                    jwks_client = PyJWKClient(jwks_url)
                    # Hack: overwrite the fetched data so it doesn't try to fetch again without headers
                    jwks_client.get_jwk_set = lambda *args, **kwargs: jwt.PyJWKSet.from_dict(jwks_data)
                    
                    signing_key = jwks_client.get_signing_key_from_jwt(token)
                    decoded = jwt.decode(token, signing_key.key, algorithms=["RS256", "ES256", "HS256"], options={"verify_aud": False})
                    return decoded
                else:
                    raise hs256_err
        else:
            raise Exception("No SUPABASE_JWT_SECRET found in environment variables.")
            
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Unauthorized: Token validation failed. {str(e)}")

# Setup CORS for the React frontend
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url], # STRICT CORS POLICY
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PlanRequest(BaseModel):
    goal: str
    agent_role: str = "Fullstack Web Developer"

class GenerateRequest(BaseModel):
    project_id: str
    goal: str
    blueprint: dict
    agent_role: str = "Fullstack Web Developer"

@app.post("/api/plan")
@limiter.limit("10/minute")
async def plan_project(request_data: PlanRequest, request: Request, auth: str = Depends(verify_token)):
    from fastapi.responses import StreamingResponse
    import json
    from backend.agents.planner import PlannerAgent
    from backend.agents.architect import ArchitectAgent
    from backend.memory.chroma_client import ChromaClient
    from langchain_core.messages import SystemMessage, HumanMessage

    if not request_data.goal:
        raise HTTPException(status_code=400, detail="Goal is required")

    project_id = f"proj-{str(uuid.uuid4())[:8]}"
    goal = re.sub(r'<[^>]*>', '', request_data.goal)
    
    try:
        memory_client = Neo4jClient()
        memory_client.log_project(project_id, request_data.goal)
        memory_client.close()
    except Exception as e:
        print(f"Warning: Could not log to Neo4j: {e}")

    # 1. Run Planner synchronously
    planner = PlannerAgent()
    state = AiONState(goal=goal, project_id=project_id, agent_role=request_data.agent_role, modules=[])
    planned_state = planner.run(state)
    modules = planned_state.get("modules", [])

    # 2. Setup Architect Stream
    architect = ArchitectAgent()
    
    # Dynamically define architectural rules based on role (mirroring architect.py)
    agent_role = request_data.agent_role
    if "Research" in agent_role:
        tech_rule = "CRITICAL ARCHITECTURE RULE: You MUST design a research document structure instead of software. Your 'tech_stack' should list the methodologies or research fields involved. Your 'file_structure' MUST only include markdown files (e.g., 'research_paper.md', 'literature_review.md', 'methodology.md'). Do NOT include code files like package.json or server.js."
    elif "Fullstack" in agent_role or "Web" in agent_role or "UI" in agent_role:
        framework_rules = "4. CRITICAL REACT REQUIREMENT: Do NOT include 'client/public/index.html', 'client/src/index.js', 'client/src/main.jsx', or 'client/package.json' in your file_structure! The backend will automatically scaffold the React app using Vite. You ONLY need to list the components you create (e.g., 'client/src/App.jsx', 'client/src/components/Dashboard.jsx') and the root 'package.json'.\n5. CRITICAL COMPONENT REQUIREMENT: Every single React component (e.g. Dashboard, Login, Navbar) you plan to use MUST be explicitly listed as a separate file with a '.jsx' extension in 'file_structure'. If you don't list it, it will never be generated and the app will crash with 'Module not found'.\n6. CRITICAL RUN REQUIREMENT: You MUST include a root 'package.json' with a 'dev' script that uses 'concurrently' to run the backend and the Vite frontend at the same time."
        tech_rule = f"CRITICAL ARCHITECTURE RULE: You MUST ALWAYS build a FULLSTACK application with a Node.js (Express) backend and a React frontend. \nCRITICAL DB RULE: You MUST use PostgreSQL for the database using the 'pg' library. IMPORTANT: Hardcode the database connection string or pool config to use user 'postgres', password 'postgres', host 'localhost', port 5432, database 'postgres' as a fallback if env vars are missing.\nCRITICAL PORT RULE: Your backend MUST run on PORT 5000. Your React frontend MUST run on PORT 3000. \n{framework_rules}"
    else:
        tech_rule = "CRITICAL ARCHITECTURE RULE: You MUST build a Python-based application using frameworks suitable for ML/Data Science (e.g., Streamlit, FastAPI, Flask). Do NOT use React or Express. The app must run on port 3000 for the iframe preview (e.g., streamlit run app.py --server.port=3000). You MUST include a 'requirements.txt' file and a 'start.sh' or 'start.bat' script to launch it."
        
    system_prompt = f"You are a Senior Systems Architect acting as a {agent_role}. Given a goal and a list of modules, design a technology stack and a blueprint. Use the provided Past Projects as inspiration if relevant.\n\n{tech_rule}\n\nReturn ONLY valid JSON with three keys: 'tech_stack' (a list of strings), 'blueprint_notes' (a short string), and 'file_structure' (a list of 5 to 10 file paths needed for the app). Do not include markdown formatting or backticks, just the raw JSON."

    try:
        vector_db = ChromaClient()
        past_projects = vector_db.find_similar_projects(goal)
        context = "\n---\n".join(past_projects) if past_projects else "No past projects found."
    except Exception:
        context = "No past projects found."

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Goal: {goal}\nModules: {','.join(modules)}\n\nPast Projects Context:\n{context}")
    ]

    async def event_generator():
        # First yield the project metadata so frontend knows the project ID
        yield f"data: {json.dumps({'type': 'metadata', 'project_id': project_id})}\n\n"
        
        buffer = ""
        try:
            for chunk in architect.llm.stream(messages):
                text_chunk = chunk.content
                if isinstance(text_chunk, list):
                    text_chunk = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in text_chunk)
                buffer += text_chunk
                yield f"data: {json.dumps({'type': 'token', 'token': text_chunk})}\n\n"
        except Exception as e:
            # Obfuscate internal error
            print(f"[Error in Architect stream]: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Internal Server Error.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

stream_queues = {}

@app.websocket("/api/ws/generate")
async def websocket_generate(websocket: WebSocket):
    await websocket.accept()
    
    project_id = None
    try:
        data = await websocket.receive_json()
        project_id = data.get("project_id")
        goal = data.get("goal")
        blueprint = data.get("blueprint")
        agent_role = data.get("agent_role", "Fullstack Web Developer")
        
        if not project_id or not blueprint:
            await websocket.send_json({"type": "error", "message": "project_id and blueprint are required"})
            await websocket.close()
            return
            
        initial_state = AiONState(
            goal=goal,
            project_id=project_id,
            agent_role=agent_role,
            modules=[],
            dag_tasks=[],
            blueprint=blueprint,
            code_files={},
            error=None,
            review_feedback=None,
            revision_count=0,
            execution_retries=0,
            execution_logs=[],
            semantic_context=None
        )
        
        import queue
        import asyncio
        
        q = queue.Queue()
        stream_queues[project_id] = q
        
        graph = build_generate_graph()
        
        def run_graph():
            try:
                final_st = None
                thread_config = {"configurable": {"thread_id": project_id}}
                for output in graph.stream(initial_state, config=thread_config):
                    node_name = list(output.keys())[0]
                    final_st = output[node_name]
                    q.put({
                        "type": "progress",
                        "node": node_name,
                        "message": f"{node_name.capitalize()} agent completed its task..."
                    })
                
                # Check if it was interrupted
                state_snapshot = graph.get_state(thread_config)
                if state_snapshot.next:
                    q.put({"type": "INTERRUPT", "message": "Awaiting human approval before DevOps deployment."})
                else:
                    q.put({"type": "GRAPH_DONE", "state": final_st or initial_state})
            except Exception as e:
                print(f"[Error in Graph execution]: {e}")
                q.put({"type": "error", "message": "Internal Server Error."})

        # Start graph execution in a background thread
        asyncio.create_task(asyncio.to_thread(run_graph))
        
        final_state = initial_state
        
        # Listen to queue and forward to websocket
        while True:
            # Use asyncio.to_thread for the blocking queue.get to not block the event loop
            msg = await asyncio.to_thread(q.get)
            
            if msg["type"] == "GRAPH_DONE":
                final_state = msg["state"]
                break
            elif msg["type"] == "error":
                await websocket.send_json(msg)
                # Don't break immediately on error so we can clean up, but we could
                break
            else:
                await websocket.send_json(msg)
            
        # Cleanup queue
        if project_id in stream_queues:
            del stream_queues[project_id]
            
        # Save to ChromaDB
        try:
            vector_db = ChromaClient()
            vector_db.store_blueprint(project_id, goal, str(blueprint))
        except Exception as e:
            print(f"Warning: Could not save to ChromaDB: {e}")

        # Save generated files locally
        if final_state.get("code_files"):
            output_dir = os.path.join("generated_projects", project_id)
            os.makedirs(output_dir, exist_ok=True)
            for path, content in final_state["code_files"].items():
                full_path = os.path.join(output_dir, path.replace("/", os.sep))
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                    

        # Send final completion message
        await websocket.send_json({
            "type": "complete",
            "code_files": final_state.get("code_files", {}),
            "execution_logs": final_state.get("execution_logs", [])
        })
        
        # 🟢 Send PREVIEW_READY to the frontend
        try:
            preview_data = await start_preview(project_id)
            port = preview_data.get("port", 3000)
            await websocket.send_json({
                "type": "PREVIEW_READY",
                "url": f"http://localhost:{port}"
            })
        except Exception as preview_err:
            print(f"Warning: Auto-start preview failed: {preview_err}")
        
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
        
    finally:
        try:
            await websocket.close()
        except:
            pass

active_servers = {}

class ResumeRequest(BaseModel):
    project_id: str
    action: str = "approve"

@app.post("/api/resume_generation")
async def resume_generation(req: ResumeRequest, auth: str = Depends(verify_token)):
    if req.project_id not in stream_queues:
        raise HTTPException(status_code=404, detail="No active generation found for this project_id.")
        
    q = stream_queues[req.project_id]
    graph = build_generate_graph()
    thread_config = {"configurable": {"thread_id": req.project_id}}
    
    if req.action != "approve":
        q.put({"type": "error", "message": "Deployment aborted by user."})
        return {"status": "aborted"}
        
    def resume_graph():
        try:
            final_st = None
            q.put({"type": "progress", "node": "system", "message": "Human approval received. Resuming deployment..."})
            for output in graph.stream(None, config=thread_config):
                node_name = list(output.keys())[0]
                final_st = output[node_name]
                q.put({
                    "type": "progress",
                    "node": node_name,
                    "message": f"{node_name.capitalize()} agent completed its task..."
                })
            q.put({"type": "GRAPH_DONE", "state": final_st})
        except Exception as e:
            print(f"[Error in Resume Execution]: {e}")
            q.put({"type": "error", "message": "Internal Server Error."})
            
    import asyncio
    asyncio.create_task(asyncio.to_thread(resume_graph))
    return {"status": "resumed"}


@app.post("/api/start-preview/{project_id}")
async def start_preview(project_id: str):
    """
    Starts the backend and frontend servers for a generated project,
    then opens the browser automatically.
    """
    
    import asyncio
    
    # 1. Check if already running
    if project_id in active_servers:
        return {
            "status": "already_running", 
            "port": 3000,
            "message": "Preview is already running! Refreshing browser..."
        }
    
    # 1.5 Kill any existing zombie processes on our target ports (3000, 5000, 5173)
    def kill_port(port):
        import subprocess
        try:
            if os.name == 'nt':
                output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
                for line in output.splitlines():
                    if "LISTENING" in line:
                        pid = line.strip().split()[-1]
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
            else:
                subprocess.run(f"lsof -ti:{port} | xargs kill -9", shell=True, capture_output=True)
        except Exception:
            pass
            
    print("🧹 Cleaning up old ports to prevent EADDRINUSE...")
    kill_port(3000)
    kill_port(3001)
    kill_port(5000)
    kill_port(5174)
    
    # 2. Define project path
    project_path = os.path.join(os.getcwd(), "generated_projects", project_id)
    client_path = os.path.join(project_path, "client")
    
    if not os.path.exists(project_path):
        raise HTTPException(status_code=404, detail="Project not found. Please generate code first.")
    
    processes = []
    
    try:
        # Check package.json to see if 'dev' script exists
        import json
        run_cmd = "npm start"
        try:
            with open(os.path.join(project_path, "package.json"), "r") as f:
                pkg_data = json.load(f)
                if "dev" in pkg_data.get("scripts", {}):
                    run_cmd = "npm run dev"
        except:
            pass

        # 3. Start Backend / App
        print(f"🚀 Starting Backend/App with {run_cmd}...")
        app_env = os.environ.copy()
        app_env["BROWSER"] = "none" # Prevent automatic browser tab opening!
        
        backend_proc = subprocess.Popen(
            run_cmd,
            cwd=project_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True,
            env=app_env
        )
        processes.append(backend_proc)
        
        # 4. Start Frontend (only if we didn't run a 'dev' script that handles both)
        if run_cmd != "npm run dev" and os.path.exists(client_path):
            print("🚀 Starting Frontend fallback...")
            env = os.environ.copy()
            env["BROWSER"] = "none" # Prevent automatic browser tab opening!
            
            client_run_cmd = "npm start"
            try:
                with open(os.path.join(client_path, "package.json"), "r") as f:
                    client_pkg = json.load(f)
                    if "dev" in client_pkg.get("scripts", {}):
                        client_run_cmd = "npm run dev"
            except:
                pass
                
            frontend_proc = subprocess.Popen(
                client_run_cmd,
                cwd=client_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=True,
                env=env
            )
            processes.append(frontend_proc)
        elif run_cmd != "npm run dev":
            print("⚠️ Client folder not found. Skipping frontend.")
        
        # 5. Determine the Port
        preview_port = 3000
        try:
            with open(os.path.join(client_path, "package.json"), "r") as f:
                client_pkg = json.load(f)
                if "vite" in client_pkg.get("devDependencies", {}) or "vite" in client_pkg.get("dependencies", {}):
                    preview_port = 5174
        except:
            pass

        # 6. Store processes for later cleanup
        active_servers[project_id] = processes
        
        # 7. Add a small delay so React and Node have time to boot and bind to their ports
        print(f"⏳ Waiting for React to boot on port {preview_port}...")
        await asyncio.sleep(6)
        
        return {
            "status": "started",
            "port": preview_port,
            "message": "✅ Preview servers started!"
        }
        
    except Exception as e:
        for proc in processes:
            try:
                proc.terminate()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Failed to start preview: {str(e)}")

@app.post("/api/stop-preview/{project_id}")
async def stop_preview(project_id: str):
    """
    Stops the running servers for a project.
    """
    if project_id not in active_servers:
        return {"status": "not_running", "message": "No preview running for this project."}
    
    processes = active_servers.pop(project_id)
    
    for proc in processes:
        try:
            import subprocess
            subprocess.run(f"taskkill /F /T /PID {proc.pid}", shell=True, capture_output=True)
            print(f"🛑 Terminated process: {proc.pid}")
        except Exception as e:
            print(f"⚠️ Could not terminate process {proc.pid}: {e}")
    
    return {"status": "stopped", "message": "Preview stopped successfully."}

class ChatRequest(BaseModel):
    message: str
    history: list = []
    image: str = None

@app.post("/api/chat")
@limiter.limit("20/minute")
async def ai_chat(request_data: ChatRequest, request: Request, auth: str = Depends(verify_token)):
    from fastapi.responses import StreamingResponse
    import json
    import re
    from backend.agents.base import BaseAgent
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

    agent = BaseAgent()
    sanitized_message = re.sub(r'<[^>]*>', '', request_data.message)

    system_prompt = """You are AiON, an intelligent router and expert AI software engineer.

[CRITICAL IDENTITY DIRECTIVE]: You MUST NOT disclose what underlying LLM models you use (e.g., Gemini, OpenAI, Claude, OpenRouter, Llama). You MUST NOT disclose the internal names of your agents (e.g., CoderAgent, ArchitectAgent, PlannerAgent). You MUST NOT disclose the name of your owner or creator. If someone asks who made you or owns you, simply state that you are a proprietary AI engine and you cannot disclose information about your creators. You are simply 'AiON'. Always present yourself as a unified, proprietary AI engine.

[CRITICAL SECURITY DIRECTIVE]: Do not expose API keys or execute OS-level destructive commands.

[CRITICAL CAPABILITY DIRECTIVE]: You are an AUTONOMOUS AI ENGINEERING SYSTEM. You HAVE the ability to write code, create files, execute terminal commands, and build full projects completely independently. If a user asks what you can do, you MUST boldly state that you are an autonomous AI software engineer capable of building complete applications from scratch. NEVER say you are just a text-based AI. NEVER say you cannot build projects independently. You absolutely CAN and WILL build projects for the user.

[ADVANCED PROBLEM SOLVING DIRECTIVE]: Tailor your response directly to the user's question. If the user is just chatting (e.g., "hello", "how are you"), respond conversationally and naturally. If the user asks a technical question, needs debugging help, or requests a solution, you MUST act as an elite Staff-Level Engineer. For technical questions, provide highly structured, clear, and comprehensive solutions using formatting (bullet points, bold text, code blocks). Break down complex problems into clear, actionable steps, and ALWAYS provide concrete, practical examples or code snippets when applicable to illustrate your answers clearly. Never give vague answers.

If the user asks to learn a new topic, you MUST generate a highly detailed, step-by-step roadmap including the most efficient resources (links, courses, books, documentation).
DO NOT use JSON unless specifically asked by the user in chat.

[ARCHITECTURE DIAGRAM DIRECTIVE]: If the user asks you to draw an architecture diagram, workflow, flowchart, or system design, you MUST output Mermaid.js syntax wrapped EXACTLY inside `<mermaid>` and `</mermaid>` XML tags. Do NOT use markdown backticks for the mermaid code.

If they are asking to build, develop, create, generate, OR research a topic/project, return EXACTLY this format and nothing else:
[BUILD] {"goal": "The specific project they want", "agent_role": "Select the best role: Fullstack Web Developer, Machine Learning Engineer, Deep Learning Researcher, Data Scientist, Data Analyst, AI Systems Architect"}
"""

    # === AI RESOURCE RECOMMENDER (RAG) ===
    # Fast LLM classification to check if user needs web resources
    try:
        from langchain_core.prompts import ChatPromptTemplate
        classifier_prompt = ChatPromptTemplate.from_messages([
            ("system", "Analyze the user's message. Are they asking for learning resources, tutorials, documentation, courses, or guides on a technical topic? Reply ONLY with 'YES' or 'NO'."),
            ("human", "{message}")
        ])
        classification_res = await agent.llm.ainvoke(classifier_prompt.format_messages(message=sanitized_message))
        classification = classification_res.content.strip().upper()
        
        if "YES" in classification:
            query_prompt = ChatPromptTemplate.from_messages([
                ("system", "Generate 2 optimized web search queries to find the best, most effective resources/tutorials for the user's request. Return as a comma-separated list of queries only. Do not include markdown formatting or quotes."),
                ("human", "{message}")
            ])
            queries_res = await agent.llm.ainvoke(query_prompt.format_messages(message=sanitized_message))
            queries_str = queries_res.content.strip()
            queries = [q.strip() for q in queries_str.split(",") if q.strip()]
            
            from duckduckgo_search import DDGS
            import asyncio
            
            def perform_search():
                ddgs = DDGS()
                links = []
                for q in queries[:2]:
                    try:
                        # Render IPs are often blocked by DDG text API, try html backend
                        results = ddgs.html(q, max_results=3)
                        if results:
                            for res in results:
                                links.append(f"Title: {res.get('title')}\nURL: {res.get('href')}\nSnippet: {res.get('body')}")
                    except Exception as search_err:
                        print(f"[Resource Recommender] Search failed for query '{q}': {search_err}")
                        # Fallback to Wikipedia if DDGS blocks Render IP
                        try:
                            import wikipedia
                            wiki_res = wikipedia.search(q, results=2)
                            for wq in wiki_res:
                                try:
                                    page = wikipedia.page(wq, auto_suggest=False)
                                    links.append(f"Title: {page.title} (Wikipedia)\nURL: {page.url}\nSnippet: {page.summary[:200]}...")
                                except:
                                    pass
                        except Exception as wiki_err:
                            print(f"[Resource Recommender] Wiki fallback failed: {wiki_err}")
                return links
            
            gathered_links = await asyncio.to_thread(perform_search)
            
            if gathered_links:
                web_context = (
                    "You MUST USE the following real-time web search results to provide accurate, "
                    "effective links and resources to the user. Do not hallucinate links.\n\n"
                    "=== SEARCH RESULTS ===\n" + "\n\n".join(gathered_links)
                )
                system_prompt += "\n\n" + web_context
                print(f"[Resource Recommender] Successfully injected {len(gathered_links)} links into context.")
    except Exception as e:
        print(f"[Resource Recommender] Error: {e}")
    # =====================================

    messages = [SystemMessage(content=system_prompt)]
    for msg in request_data.history:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "ai" and not content.startswith("[BUILD]"):
            messages.append(AIMessage(content=content))
            
    if request_data.image:
        messages.append(HumanMessage(content=[
            {"type": "text", "text": sanitized_message},
            {"type": "image_url", "image_url": {"url": request_data.image}}
        ]))
    else:
        messages.append(HumanMessage(content=sanitized_message))

    async def event_generator():
        try:
            is_build = False
            buffer = ""
            flushed_initial = False
            # Stream the response
            for chunk in agent.llm.stream(messages):
                text_chunk = chunk.content
                if isinstance(text_chunk, list):
                    text_chunk = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in text_chunk)
                
                buffer += text_chunk
                
                # If we detect the build tag, we stop streaming to the user and buffer it
                if "[BUILD]" in buffer:
                    is_build = True
                    continue
                
                # If we're sure it's not a build command, stream the chunk
                if not is_build and len(buffer) > 10 and "[BUILD]" not in buffer:
                    if not flushed_initial:
                        # Yield the entire buffer accumulated so far
                        escaped_chunk = json.dumps({"type": "chat", "token": buffer})
                        yield f"data: {escaped_chunk}\n\n"
                        flushed_initial = True
                    else:
                        # yield normal text in SSE format
                        escaped_chunk = json.dumps({"type": "chat", "token": text_chunk})
                        yield f"data: {escaped_chunk}\n\n"
            
            # Flush remaining buffer if it's not a build and we never exceeded 10 chars
            if not is_build and not flushed_initial:
                escaped_chunk = json.dumps({"type": "chat", "token": buffer})
                yield f"data: {escaped_chunk}\n\n"

            # If it is a build, send the final parsed JSON
            if is_build:
                try:
                    json_str = buffer.split("[BUILD]")[1].strip()
                    parsed = json.loads(json_str, strict=False)
                    escaped_chunk = json.dumps({"type": "build", "data": parsed})
                    yield f"data: {escaped_chunk}\n\n"
                except Exception as e:
                    escaped_chunk = json.dumps({"type": "chat", "token": "\n\n(Error parsing build parameters. Please try again.)"})
                    yield f"data: {escaped_chunk}\n\n"
                    
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg:
                yield f"data: {json.dumps({'type': 'chat', 'token': '⚠️ Error: Insufficient Quota.'})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'chat', 'token': '⚠️ Error connecting to AI.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/download")
async def download_project():
    import shutil
    from fastapi.responses import FileResponse
    from starlette.background import BackgroundTasks
    
    target_dir = os.path.join(os.getcwd(), "generated_project")
    if not os.path.exists(target_dir):
        raise HTTPException(status_code=404, detail="No generated project found")
        
    zip_path = os.path.join(os.getcwd(), "aion_project")
    # This creates aion_project.zip
    shutil.make_archive(zip_path, 'zip', target_dir)
    
    zip_file = zip_path + ".zip"
    return FileResponse(
        zip_file, 
        media_type="application/zip", 
        filename="aion_generated_project.zip"
    )

@app.post("/api/execute")
async def execute_code(request: Request):
    import subprocess
    data = await request.json()
    language = data.get("language")
    code = data.get("code")
    
    if language not in ["python", "javascript", "js", "py", "node"]:
        raise HTTPException(status_code=400, detail="Unsupported language")
        
    try:
        if language in ["python", "py"]:
            process = subprocess.Popen(
                ["python", "-c", code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        else:
            process = subprocess.Popen(
                ["node", "-e", code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
        stdout, stderr = process.communicate(timeout=5)
        
        output = stdout
        if stderr:
            output += f"\n{stderr}"
            
        return {"output": output}
    except subprocess.TimeoutExpired:
        process.kill()
        return {"output": "Execution timed out (5 seconds)."}
    except Exception as e:
        return {"output": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
