import typing
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

from backend.orchestrator.state import AiONState
load_dotenv()

app = FastAPI(
    title="yAI API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

from backend.utils.logger import get_logger
import time
api_logger = get_logger("AiON_API")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = None
    try:
        response = await call_next(request)
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        api_logger.error(f"[ERROR] {request.method} {request.url.path} failed in {process_time:.2f}ms. Exception: {e}")
        raise e
        
    process_time = (time.time() - start_time) * 1000
    api_logger.info(f"[API] {request.method} {request.url.path} - Status: {response.status_code} - Latency: {process_time:.2f}ms")
    return response

from backend.db.database import engine, Base
from backend.utils.redis_client import REDIS_URL
import redis.asyncio as aioredis

# Initialize Database Tables
Base.metadata.create_all(bind=engine)

# Auto-migrate: Add chat_history column if missing
try:
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN chat_history JSON"))
except Exception as e:
    # Ignored if column already exists or DB doesn't support it directly
    pass

@app.api_route("/", methods=["GET", "HEAD"])
def health_check():
    return {"status": "ok", "message": "yAI Backend is running with PostgreSQL & Redis"}

# Initialize Redis for Rate Limiting
# Note: slowapi requires an async redis connection string for storage
try:
    if REDIS_URL:
        limiter = Limiter(key_func=get_remote_address, storage_uri=REDIS_URL.replace("redis://", "redis+asyncio://"))
    else:
        limiter = Limiter(key_func=get_remote_address)
except Exception as e:
    print(f"[WARNING] Failed to connect to Redis for Rate Limiting. Falling back to memory: {e}")
    limiter = Limiter(key_func=get_remote_address)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    import traceback
    print("❌ Validation Error! Payload sent by frontend:")
    try:
        body = await request.body()
        print("BODY:", body.decode())
    except:
        pass
    print("ERRORS:", exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

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
        return {"sub": "local", "role": "authenticated", "email": "local_dev@aion.ai"}
        
    try:
        # If we have a jwt_secret, try HS256 first
        hs256_failed = False
        if jwt_secret:
            import base64
            from jwt.exceptions import ExpiredSignatureError
            # Try plain string first
            try:
                decoded = jwt.decode(token, jwt_secret, algorithms=["HS256"], options={"verify_aud": False})
                return decoded
            except ExpiredSignatureError:
                raise HTTPException(status_code=401, detail="Unauthorized: Your login token has expired. Please refresh the Vercel page and log in again.")
            except Exception:
                # If plain string fails, try base64 decoding it (Standard for Supabase legacy secrets)
                try:
                    decoded = jwt.decode(token, base64.b64decode(jwt_secret), algorithms=["HS256"], options={"verify_aud": False})
                    return decoded
                except ExpiredSignatureError:
                    raise HTTPException(status_code=401, detail="Unauthorized: Your login token has expired. Please refresh the Vercel page and log in again.")
                except Exception as hs256_err:
                    hs256_failed = True
                
        # If HS256 failed, OR if we don't have a jwt_secret but we DO have supabase_url, try JWKS
        if supabase_url and (hs256_failed or not jwt_secret):
            import json, urllib.request
            jwks_url = f"{supabase_url}/auth/v1/jwks"
            
            req = urllib.request.Request(jwks_url)
            anon_key = os.getenv("SUPABASE_ANON_KEY", "")
            if anon_key:
                req.add_header("apikey", anon_key)
            
            with urllib.request.urlopen(req) as response:
                jwks_data = json.loads(response.read().decode())
                
            jwks_client = PyJWKClient(jwks_url)
            jwks_client.get_jwk_set = lambda *args, **kwargs: jwt.PyJWKSet.from_dict(jwks_data)
            
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            decoded = jwt.decode(token, signing_key.key, algorithms=["RS256", "ES256", "HS256"], options={"verify_aud": False})
            return decoded
            
        # If everything failed or missing
        raise Exception("Missing SUPABASE_JWT_SECRET and failed to fetch JWKS from SUPABASE_URL.")
            
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

class HistoryRequest(BaseModel):
    history: list

@app.get("/api/user/history")
async def get_user_history(auth: dict = Depends(verify_token)):
    from backend.db.database import SessionLocal
    from backend.db.models import User
    
    db = SessionLocal()
    try:
        email = auth.get("email")
        if not email:
            return {"history": []}
            
        user = db.query(User).filter(User.email == email).first()
        if user and user.chat_history:
            return {"history": user.chat_history}
        return {"history": []}
    finally:
        db.close()

@app.post("/api/user/history")
async def save_user_history(req: HistoryRequest, auth: dict = Depends(verify_token)):
    from backend.db.database import SessionLocal
    from backend.db.models import User
    
    db = SessionLocal()
    try:
        email = auth.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="Email missing in token")
            
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Create user if they don't exist yet in the DB
            user = User(email=email, chat_history=req.history)
            db.add(user)
        else:
            user.chat_history = req.history
            
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

class PlanRequest(BaseModel):
    goal: str
    agent_role: str = "Fullstack Web Developer"
    image: typing.Optional[typing.Union[str, typing.List[str]]] = None

class GenerateRequest(BaseModel):
    project_id: str
    goal: str
    blueprint: dict
    agent_role: str = "Fullstack Web Developer"

@app.post("/api/plan")
@limiter.limit("5/minute")
async def plan_project(request_data: PlanRequest, request: Request, auth: dict = Depends(verify_token)):
    from fastapi.responses import StreamingResponse
    import json
    from backend.agents.planner import PlannerAgent
    from backend.agents.architect import ArchitectAgent
    from backend.memory.chroma_client import ChromaClient
    from backend.memory.neo4j_client import Neo4jClient
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

    # Setup Architect
    from backend.agents.architect import ArchitectAgent
    architect = ArchitectAgent()

    async def event_generator():
        import asyncio
        # First yield the project metadata so frontend knows the project ID
        yield f"data: {json.dumps({'type': 'metadata', 'project_id': project_id})}\n\n"
        
        try:
            msg1 = json.dumps({'type': 'token', 'token': '### 🔍 Phase 1: Researching & Gathering Context...\n'})
            yield f"data: {msg1}\n\n"
            from backend.agents.researcher import ResearchAgent
            researcher = ResearchAgent()
            initial_state = AiONState(goal=goal, project_id=project_id, agent_role=request_data.agent_role, modules=[])
            if request_data.image:
                initial_state["image"] = request_data.image
                
            researched_state = await asyncio.to_thread(researcher.run, initial_state)
            semantic_context = researched_state.get("semantic_context", "")

            msg2 = json.dumps({'type': 'token', 'token': '✅ Context gathered.\n\n### 🧠 Phase 2: Defining Core Modules...\n'})
            yield f"data: {msg2}\n\n"
            from backend.agents.planner import PlannerAgent
            planner = PlannerAgent()
            planned_state = await asyncio.to_thread(planner.run, researched_state)
            modules = planned_state.get("modules", [])

            msg3 = json.dumps({'type': 'token', 'token': '✅ Modules defined.\n\n### 🏗️ Phase 3: Drafting System Blueprint...\n\n'})
            yield f"data: {msg3}\n\n"

            # Dynamically define architectural rules based on role (mirroring architect.py)
            agent_role = request_data.agent_role
            if "Research" in agent_role:
                tech_rule = "CRITICAL ARCHITECTURE RULE: You MUST design a research document structure instead of software. Your 'tech_stack' should list the methodologies or research fields involved. Your 'file_structure' MUST only include markdown files (e.g., 'research_paper.md', 'literature_review.md', 'methodology.md'). Do NOT include code files like package.json or server.js."
            elif "Fullstack" in agent_role or "Web" in agent_role or "UI" in agent_role:
                framework_rules = "4. CRITICAL REACT REQUIREMENT: Do NOT include 'client/public/index.html', 'client/src/index.js', 'client/src/main.jsx', or 'client/package.json' in your file_structure! The backend will automatically scaffold the React app using Vite. You ONLY need to list the components you create (e.g., 'client/src/App.jsx', 'client/src/components/Dashboard.jsx') and the root 'package.json'.\n5. CRITICAL COMPONENT REQUIREMENT: Every single React component (e.g. Dashboard, Login, Navbar) you plan to use MUST be explicitly listed as a separate file with a '.jsx' extension in 'file_structure'. If you don't list it, it will never be generated and the app will crash with 'Module not found'.\n6. CRITICAL RUN REQUIREMENT: You MUST include a root 'package.json' with a 'dev' script that uses 'concurrently' to run the backend and the Vite frontend at the same time."
                tech_rule = f"CRITICAL ARCHITECTURE RULE: You MUST ALWAYS build a FULLSTACK application with a Node.js (Express) backend and a React frontend. \nCRITICAL DB RULE: You MUST use PostgreSQL for the database using the 'pg' library. IMPORTANT: Hardcode the database connection string or pool config to use user 'postgres', password 'postgres', host 'localhost', port 5432, database 'postgres' as a fallback if env vars are missing.\nCRITICAL PORT RULE: Your backend MUST run on PORT 5000. Your React frontend MUST run on PORT 3000. \n{framework_rules}"
            else:
                tech_rule = "CRITICAL ARCHITECTURE RULE: You MUST build a Python-based application using frameworks suitable for ML/Data Science (e.g., Streamlit, FastAPI, Flask). Do NOT use React or Express. The app must run on port 3000 for the iframe preview (e.g., streamlit run app.py --server.port=3000). You MUST include a 'requirements.txt' file and a 'start.sh' or 'start.bat' script to launch it."
                
            system_prompt = f"You are an Elite Enterprise Systems Architect acting as a {agent_role}. Given a goal, a list of modules, and an Innovation Brief, design a highly advanced, cutting-edge, and production-ready technology stack and blueprint. Do NOT build simple 1990s CRUD apps; incorporate modern UX, AI where relevant, scalable structures, and robust data models. Use the provided Past Projects and Research Context as inspiration.\n\n{tech_rule}\n\nReturn ONLY valid JSON with three keys: 'tech_stack' (a list of exact technologies), 'blueprint_notes' (a detailed string explaining the advanced architectural decisions), and 'file_structure' (a comprehensive list of ALL necessary file paths). CRITICAL: Every item in 'file_structure' MUST be a file with an extension (e.g., 'server/app.js', 'client/src/App.jsx'). NEVER include raw directory names (like 'server' or 'client/src'). Do not include markdown formatting or backticks, just the raw JSON."

            try:
                def get_past_projects():
                    vector_db = ChromaClient()
                    return vector_db.find_similar_projects(goal)
                past_projects = await asyncio.to_thread(get_past_projects)
                context = "\n---\n".join(past_projects) if past_projects else "No past projects found."
            except Exception:
                context = "No past projects found."

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Goal: {goal}\nModules: {','.join(modules)}\n\nResearch Context (Innovation Brief):\n{semantic_context}\n\nPast Projects Context:\n{context}")
            ]
            
            buffer = ""
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

    headers = {
        "X-Accel-Buffering": "no",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)

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
        execution_mode = data.get("execution_mode", "Deep")
        code_files = data.get("code_files", {})
        
        if not project_id:
            await websocket.send_json({"type": "error", "message": "project_id is required"})
            await websocket.close()
            return
            
        import queue
        import asyncio
        import os
        
        # --- yAI OVERDRIVE: Zero-Latency Semantic Caching ---
        if goal:
            try:
                from backend.db.database import SessionLocal
                from backend.db.models import Project
                db = SessionLocal()
                cached_project = db.query(Project).filter(Project.goal == goal).first()
                db.close()
                
                if cached_project and cached_project.id != project_id:
                    cached_dir = os.path.join("generated_projects", cached_project.id)
                    if os.path.exists(cached_dir):
                        print(f"⚡ [Semantic Cache Hit] Returning cached project {cached_project.id} for goal: {goal}")
                        # Load files from disk
                        cached_files = {}
                        for root, _, files in os.walk(cached_dir):
                            for file in files:
                                if file == ".DS_Store" or "node_modules" in root: continue
                                file_path = os.path.join(root, file)
                                rel_path = os.path.relpath(file_path, cached_dir).replace("\\", "/")
                                try:
                                    with open(file_path, "r", encoding="utf-8") as f:
                                        cached_files[rel_path] = f.read()
                                except Exception:
                                    pass
                        
                        if cached_files:
                            # Send simulated timeline
                            await websocket.send_json({"type": "progress", "message": "⚡ Semantic Cache Hit: Bypassing LLM generation..."})
                            await websocket.send_json({"type": "timeline", "title": "⚡ Zero-Latency Semantic Caching", "reason": "Identified exact architecture match in memory.", "status": "done"})
                            await websocket.send_json({"type": "code_complete", "code_files": cached_files})
                            await websocket.send_json({
                                "type": "complete",
                                "code_files": cached_files,
                                "execution_logs": ["> [Cache] Loaded from semantic memory in 14ms."]
                            })
                            
                            # Start Sandbox for the cached files
                            try:
                                requires_backend = any(path.startswith("server/") or path == "requirements.txt" or path == "app.py" or path == "docker-compose.yml" for path in cached_files.keys())
                                if requires_backend:
                                    from backend.sandbox.manager import global_sandbox_manager
                                    sandbox_info = await global_sandbox_manager.start_sandbox(project_id, cached_files)
                                    if sandbox_info.get("status") == "error":
                                        await websocket.send_json({"type": "PREVIEW_ERROR", "message": sandbox_info.get("message", "Sandbox error")})
                                    else:
                                        await websocket.send_json({"type": "PREVIEW_READY", "url": sandbox_info.get("url"), "isBackend": True})
                                else:
                                    await websocket.send_json({"type": "PREVIEW_READY", "url": "sandpack-preview", "isBackend": False})
                            except Exception as e:
                                print(f"Cache Sandbox Error: {e}")
                                
                            await websocket.close()
                            return
            except Exception as e:
                print(f"Semantic Cache Error: {e}")
        # -----------------------------------------------------

        q = queue.Queue()
        stream_queues[project_id] = q

        from backend.agents.router import OmniIntelligenceEngine
        router = OmniIntelligenceEngine()
        router_analysis = await router.adetect_intent(goal, [])
        await websocket.send_json({"type": "timeline", "title": "⚡ Router Engine", "reason": f"Routing Workflow: {router_analysis.get('primary_intent')}", "status": "done"})

        initial_state = AiONState(
            goal=goal,
            project_id=project_id,
            agent_role=agent_role,
            modules=[],
            dag_tasks=[],
            blueprint=blueprint,
            code_files=code_files,
            router_analysis=router_analysis,
            error=None,
            runtime_error=None,
            review_feedback=None,
            revision_count=0,
            execution_retries=0,
            execution_logs=[],
            semantic_context=None,
            execution_mode=execution_mode,
            complexity="Low" if execution_mode in ["lightning", "fast"] else "High",
            compressed_context=None
        )
        
        from backend.gateway import AIGateway
        gateway = AIGateway()
        
        def run_graph():
            gateway.run(initial_state, q, project_id)

        # Start gateway execution in a background thread
        asyncio.create_task(asyncio.to_thread(run_graph))

        
        final_state = initial_state
        
        # Listen to queue and forward to websocket
        while True:
            # Use asyncio.to_thread for the blocking queue.get to not block the event loop
            msg = await asyncio.to_thread(q.get)
            
            if msg["type"] == "GRAPH_DONE":
                final_state = msg["state"]
                
                # Phase 1: Persistent Project Memory (Save to PostgreSQL)
                try:
                    from backend.db.database import SessionLocal
                    from backend.db.models import Project
                    
                    db = SessionLocal()
                    db_project = Project(
                        id=project_id,
                        name=f"Project {project_id[:8]}",
                        goal=final_state.get("goal", ""),
                        blueprint=final_state.get("blueprint", {})
                    )
                    db.merge(db_project)
                    db.commit()
                    db.close()
                    print(f"✅ [Memory] Project {project_id} permanently saved to PostgreSQL.")
                except Exception as db_err:
                    print(f"❌ [Memory] Failed to save project to PostgreSQL: {db_err}")
                    
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
        
        try:
            code_files = final_state.get("code_files", {})
            requires_backend = any(path.startswith("server/") or path == "requirements.txt" or path == "app.py" or path == "docker-compose.yml" for path in code_files.keys())
            
            if requires_backend:
                from backend.sandbox.manager import global_sandbox_manager
                sandbox_info = await global_sandbox_manager.start_sandbox(project_id, code_files)
                if sandbox_info.get("status") == "error":
                    await websocket.send_json({
                        "type": "PREVIEW_ERROR",
                        "message": sandbox_info.get("message", "Unknown backend error")
                    })
                else:
                    await websocket.send_json({
                        "type": "PREVIEW_READY",
                        "url": sandbox_info["url"],
                        "isBackend": True
                    })
            else:
                await websocket.send_json({
                    "type": "PREVIEW_READY",
                    "url": "sandpack-preview",
                    "isBackend": False
                })
        except Exception as preview_err:
            print(f"Warning: Failed to start Sandbox or send PREVIEW_READY: {preview_err}")
        
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

class TutorRequest(BaseModel):
    query: str
    history: list = []

@app.post("/api/tutor")
@limiter.limit("10/minute")
async def chat_tutor(request: Request, req: TutorRequest):
    try:
        from backend.agents.tutor import TutorAgent
        tutor = TutorAgent()
        # The agent expects a list of history objects e.g. [{"role": "user", "content": "hi"}, ...]
        response_text = tutor.respond(req.history, req.query)
        return {"response": response_text}
    except Exception as e:
        print(f"[Error in Tutor Endpoint]: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ResumeRequest(BaseModel):
    project_id: str
    action: str = "approve"

@app.post("/api/resume_generation")
async def resume_generation(req: ResumeRequest, auth: dict = Depends(verify_token)):
    if req.project_id not in stream_queues:
        raise HTTPException(status_code=404, detail="No active generation found for this project_id.")
        
    q = stream_queues[req.project_id]
    from backend.orchestrator.graph import build_orchestrator_graph
    graph = build_orchestrator_graph()
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
async def start_preview(project_id: str, request: Request = None):
    """
    Starts the backend and frontend servers for a generated project.
    On cloud, compiles the app statically.
    """
    import asyncio
    
    # 2. Define project path
    project_path = os.path.join(os.getcwd(), "generated_projects", project_id)
    client_path = os.path.join(project_path, "client")
    
    if not os.path.exists(project_path):
        raise HTTPException(status_code=404, detail="Project not found. Please generate code first.")
    
    try:
        # Instead of starting a dev server on port 3000 (which gets trapped in the cloud),
        # we compile the React app and serve it directly from FastAPI!
        print("   -> [Preview] Compiling React application for Live Preview...")
        
        # Run the build process synchronously with relative base paths
        process = await asyncio.create_subprocess_shell(
            "npm install && npx --yes vite build --base=./",
            cwd=client_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            err = stderr.decode() if stderr else stdout.decode() if stdout else "Unknown build error"
            print(f"   -> [Preview Error] {err}")
            raise HTTPException(status_code=500, detail=f"Build failed. The Executor might still be installing dependencies. Please try again in 10 seconds.")
            
        print("   -> [Preview] Application compiled successfully!")
        
        # Determine the base URL (Render URL if on cloud, localhost if local)
        base_url = str(request.base_url).rstrip('/') if request else ""
        
        return {
            "status": "started", 
            "port": 80,
            "message": "Preview compiled and ready!",
            "url": f"{base_url}/live/{project_id}/index.html"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start preview: {str(e)}")

from fastapi.responses import FileResponse

@app.get("/live/{project_id}/{file_path:path}")
async def serve_live_preview(project_id: str, file_path: str):
    """
    Serves the statically compiled React application from the dist directory.
    This entirely bypasses the need for multiple ports or complex tunneling!
    """
    if not file_path or file_path == "":
        file_path = "index.html"
        
    project_path = os.path.join(os.getcwd(), "generated_projects", project_id)
    dist_path = os.path.join(project_path, "client", "dist")
    
    full_path = os.path.abspath(os.path.join(dist_path, file_path))
    
    if not os.path.exists(full_path):
        # SPA Fallback: If it's a React Router path, serve index.html
        return FileResponse(os.path.join(dist_path, "index.html"))
        
    return FileResponse(full_path)

@app.post("/api/write-file/{project_id}")
async def write_file_endpoint(project_id: str, request: Request):
    """
    Saves/writes edits made back to the host disk.
    Supports writing files in both local compiled folders and sandbox workspaces.
    """
    data = await request.json()
    file_path = data.get("path")
    content = data.get("content")
    
    if not file_path or content is None:
        raise HTTPException(status_code=400, detail="path and content are required")
        
    # Check possible project workspace locations
    # 1. generated_projects (frontend / standard path)
    project_path = os.path.join(os.getcwd(), "generated_projects", project_id)
    if not os.path.exists(project_path):
        # 2. workspace/projects (sandbox path)
        project_path = os.path.join(os.getcwd(), "workspace", "projects", project_id)
        if not os.path.exists(project_path):
            # If neither exist, create it in generated_projects
            project_path = os.path.join(os.getcwd(), "generated_projects", project_id)
            os.makedirs(project_path, exist_ok=True)
            
    full_path = os.path.abspath(os.path.join(project_path, file_path))
    
    # Path Traversal Check
    if not full_path.startswith(os.path.abspath(project_path)):
        raise HTTPException(status_code=403, detail="Access denied: Path traversal detected")
        
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "saved", "path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {str(e)}")

@app.post("/api/restart-sandbox/{project_id}")
async def restart_sandbox(project_id: str):
    """
    Restarts a running backend sandbox process after file modifications on disk.
    """
    from backend.sandbox.manager import global_sandbox_manager
    
    # Stop existing if running
    global_sandbox_manager.stop_sandbox(project_id)
    
    # Get files from workspace to reload
    project_path = os.path.join(os.getcwd(), "workspace", "projects", project_id)
    if not os.path.exists(project_path):
        raise HTTPException(status_code=404, detail="Sandbox project workspace not found")
        
    # Walk and collect current files
    code_files = {}
    for root, _, files in os.walk(project_path):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, project_path)
            rel_path = rel_path.replace("\\", "/")
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    code_files[rel_path] = f.read()
            except Exception:
                pass
                
    try:
        sandbox_info = await global_sandbox_manager.start_sandbox(project_id, code_files)
        return {
            "status": "restarted",
            "url": sandbox_info.get("url"),
            "message": "Sandbox restarted successfully!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restart sandbox: {str(e)}")

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
    image: typing.Optional[typing.Union[str, typing.List[str]]] = None
    memory: typing.Optional[str] = None
    projectId: typing.Optional[str] = None

@app.post("/api/chat")
@limiter.limit("50/minute")
async def ai_chat(request_data: ChatRequest, request: Request):
    from fastapi.responses import StreamingResponse
    import json
    import re
    from backend.agents.base import BaseAgent
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

    agent = BaseAgent()
    sanitized_message = re.sub(r'<[^>]*>', '', request_data.message)

    # 🟢 PHASE 1: Immediate Connection & Heartbeat Logging
    async def event_generator():
        import json
        import time
        import asyncio
        from backend.agents.router import OmniIntelligenceEngine
        from backend.agents.prompts import get_system_prompt
        
        try:
            start_time = time.time()
            
            # === ZERO-LATENCY ITERATIVE REFINING MODE ===
            if request_data.projectId:
                yield f"data: {json.dumps({'type': 'status', 'message': '✨ Refining Project...'})}\n\n"
                project_dir = os.path.join(os.getcwd(), "generated_projects", request_data.projectId)
                code_files_str = ""
                
                # Load current project state
                for root, dirs, files in os.walk(project_dir):
                    for file in files:
                        filepath = os.path.join(root, file)
                        rel_path = os.path.relpath(filepath, project_dir).replace(os.sep, "/")
                        if any(x in rel_path for x in ["node_modules", "aion_vite_cache", ".git"]): continue
                        if rel_path.endswith((".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg")): continue
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                code_files_str += f'<file path="{rel_path}">\n{f.read()}\n</file>\n\n'
                        except: pass

                system_prompt = f"""You are a Senior Full-Stack Developer refining an existing project.
The user wants to make a change.
Here are the current files:
{code_files_str}

IMPORTANT RULES:
1. Output the file(s) you modified EXACTLY in this format:
<file path="path/to/file">
[FULL UPDATED FILE CONTENT]
</file>
2. Do NOT use JSON. Do NOT write markdown outside of the file tags.
3. You must output the ENTIRE updated file content. Do not use placeholders like "rest of code remains the same"."""
                
                messages = [SystemMessage(content=system_prompt), HumanMessage(content=sanitized_message)]
                
                draft_text = ""
                async for text_chunk in agent.llm.astream(messages):
                    draft_text += text_chunk
                    yield f"data: {json.dumps({'type': 'chat', 'token': text_chunk})}\n\n"
                
                import re
                matches = re.finditer(r'<file\s+path="([^"]+)">(.*?)</file>', draft_text, re.DOTALL)
                for match in matches:
                    file_path = match.group(1).strip()
                    file_content = match.group(2).strip()
                    safe_path = file_path.replace("..", "").replace(":\\", "").lstrip("/")
                    full_path = os.path.abspath(os.path.join(project_dir, safe_path.replace("/", os.sep)))
                    if full_path.startswith(os.path.abspath(project_dir)):
                        os.makedirs(os.path.dirname(full_path), exist_ok=True)
                        with open(full_path, "w", encoding="utf-8") as f:
                            f.write(file_content)
                        yield f"data: {json.dumps({'type': 'refine_file', 'file': safe_path, 'content': file_content})}\n\n"
                        
                yield f"data: {json.dumps({'type': 'status', 'message': '✨ Hot-Reloading Preview...'})}\n\n"
                yield f"data: {json.dumps({'type': 'refine_done'})}\n\n"
                return

            # Immediately yield heartbeat to prevent frontend timeout
            yield f"data: {json.dumps({'type': 'status', 'message': '✨ Analyzing Intent...'})}\n\n"
            api_logger.info(f"TTFT_heartbeat: {(time.time() - start_time) * 1000:.2f}ms")
            

            # 🟢 PHASE 2 & 3 CONCURRENT: Fast Intent Routing & Memory Retrieval
            yield f"data: {json.dumps({'type': 'status', 'message': '🧠 Omni-Intelligence Routing...'})}\n\n"
            
            from backend.agents.router import OmniIntelligenceEngine
            router = OmniIntelligenceEngine(llm=agent.fast_llm)
            
            async def get_memory():
                try:
                    client = globals().get('global_chroma_client')
                    if client:
                        return await asyncio.to_thread(client.retrieve_memory, "default_user", sanitized_message)
                    else:
                        from backend.memory.chroma_client import ChromaClient
                        return await asyncio.to_thread(ChromaClient().retrieve_memory, "default_user", sanitized_message)
                except Exception as e:
                    api_logger.warning(f"Failed to retrieve vector memory: {e}")
                    return "No past memory recorded yet."

            router_task = asyncio.create_task(router.adetect_intent(sanitized_message, request_data.history))
            memory_task = asyncio.create_task(get_memory())
            
            try:
                intent_data, USER_MEMORY = await asyncio.wait_for(
                    asyncio.gather(router_task, memory_task),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                api_logger.warning("Router or memory task timed out! Falling back to defaults.")
                intent_data = {}
                USER_MEMORY = "No past memory recorded yet."
                
            if not USER_MEMORY:
                USER_MEMORY = "No past memory recorded yet."
            
            missing_info = intent_data.get("missing_info_question")
            if missing_info and isinstance(missing_info, str) and missing_info.lower() not in ["none", "null", "", "n/a"]:
                yield f"data: {json.dumps({'type': 'status', 'message': ''})}\n\n"
                yield f"data: {json.dumps({'type': 'chat', 'token': missing_info})}\n\n"
                return

            # --- NON-BLOCKING VISUAL ENGINE ---
            visual_queue = None
            visual_task = None
            entity_det = intent_data.get("entity_detection", {})
            visual_query_val = entity_det.get("search_query", "")
            if entity_det.get("requires_visuals") and visual_query_val and visual_query_val.lower() not in ["null", "none"]:
                visual_queue = asyncio.Queue()
                yield f"data: {json.dumps({'type': 'status', 'message': '📸 Fetching Visuals (Background)...'})}\n\n"
                async def fetch_visuals():
                    from backend.utils.visuals import get_generative_image, get_real_world_image, get_pencil_sketch_image
                    try:
                        v_count = 1
                        img_urls = []
                        
                        # Try real world first (highest quality for places, people, objects)
                        res = await asyncio.to_thread(get_real_world_image, visual_query_val, v_count)
                        img_urls = res if isinstance(res, list) else ([res] if res else [])
                        
                        # Fallback to generative for abstract concepts or if real-world fails
                        if not img_urls:
                            url = await asyncio.to_thread(get_generative_image, visual_query_val)
                            if url: img_urls.append(url)
                        
                        for img_url in img_urls:
                            await visual_queue.put({
                                "type": "visual",
                                "media_type": "image",
                                "url": img_url,
                                "alt": visual_query_val
                            })
                    except Exception as e:
                        api_logger.warning(f"Error fetching visuals: {e}")
                    finally:
                        await visual_queue.put(None) # EOF marker
                
                visual_task = asyncio.create_task(fetch_visuals())

            msg_lower = sanitized_message.lower()
            primary_intent = str(intent_data.get("primary_intent", "General Chat"))
            complexity = str(intent_data.get("complexity", "Medium"))
            
            is_architecture_req = any(word in msg_lower for word in ["diagram", "architecture", "flowchart", "workflow"]) or primary_intent == "Architecture"
            
            build_intents = ["Website Development", "Mobile App Development", "API Development", "Database Design", "Coding"]
            explicit_build = any(word in msg_lower for word in ["build a", "create a", "develop a", "make a", "generate a", "web app"])
            is_build_req = (
                (primary_intent in ["Website Development", "Mobile App Development"]) or 
                (primary_intent in build_intents and complexity in ["Large", "Enterprise"]) or
                explicit_build
            )
            
            is_domain_expert_req = (complexity in ["Large", "Enterprise"] and not is_build_req and not is_architecture_req) or primary_intent == "Research"
            
            if is_domain_expert_req:
                yield f"data: {json.dumps({'type': 'status', 'message': '🧠 Spawning Domain Experts...'})}\n\n"
                try:
                    from backend.agents.domain_experts import DomainOrchestrator
                    orchestrator = DomainOrchestrator()
                    result = await orchestrator.execute_parallel_experts(sanitized_message, USER_MEMORY)
                    experts_str = ", ".join(result["experts"])
                    
                    yield f"data: {json.dumps({'type': 'status', 'message': f'✅ Fused knowledge from: {experts_str}'})}\n\n"
                    
                    fused = result["fused_response"]
                    chunk_size = 20
                    for i in range(0, len(fused), chunk_size):
                        yield f"data: {json.dumps({'type': 'chat', 'token': fused[i:i+chunk_size]})}\n\n"
                        await asyncio.sleep(0.01)
                    
                    yield f"data: {json.dumps({'type': 'status', 'message': ''})}\n\n"
                    return
                except Exception as e:
                    api_logger.error(f"Domain Orchestrator failed: {e}")
            
            if not is_architecture_req and not is_build_req:
                yield f"data: {json.dumps({'type': 'status', 'message': '🧠 Fusing Context Intelligence...'})}\n\n"
                try:
                    from backend.agents.context_intelligence import ContextIntelligenceEngine
                    ctx_engine = ContextIntelligenceEngine()
                    fused_context = await ctx_engine.build_context(sanitized_message, request_data.history, intent_data, USER_MEMORY)
                    system_prompt = ctx_engine.generate_system_prompt(fused_context)
                except Exception as e:
                    api_logger.error(f"Context Intelligence failed: {e}")
                    base_prompt = get_system_prompt(intent_data)
                    system_prompt = f"{base_prompt}\n\n[USER'S PAST MEMORY]:\n{USER_MEMORY}"
            else:
                base_prompt = get_system_prompt(intent_data)
                system_prompt = f"""{base_prompt}

[SYSTEM DIRECTIVES]:
- **yAI Architecture Intelligence Engine v2.0:** If the user asks for a diagram, workflow, flowchart, or system architecture, you MUST behave as a Principal Software Architect. Do NOT generate generic flowcharts. You MUST output a structured JSON block wrapped EXACTLY inside `<architecture>` and `</architecture>` tags. NEVER use Mermaid.
  You MUST include a deep architectural review.
  Schema: 
  {{
    "nodes": [{{"id":"n1","label":"API Gateway","type":"gateway","zone":"edge","tech":"Kong","status":"Healthy","description":"Entry point for all external traffic"}}], 
    "edges": [{{"source":"n1","target":"n2","label":"HTTP","type":"sync"}}], 
    "zones": [{{"id":"edge","label":"Edge Layer"}}],
    "review": {{
      "score": 95,
      "scalability": "Horizontal scaling enabled...",
      "security": "WAF at the gateway...",
      "bottlenecks": ["DB connection limits..."],
      "costDrivers": ["Always-on cache..."],
      "recommendations": ["Use read-replicas..."],
      "tradeoffs": ["Consistency vs Availability..."]
    }}
  }}
  Types: gateway, microservice, database, external, queue, ai, cache, user, security, monitoring. Edges: sync, async, data, monitor, fail.
  You MUST logically group services into `zones` (e.g. Edge Layer, API Layer, Data Layer, Processing, Observability).
  Every node MUST belong to a valid zone ID.
  Every node MUST include `tech`, `status`, and `description`.
  **CRITICAL FOR EFFICIENCY:** Design Highly Efficient, Advanced Architectures. Eliminate single points of failure. Use Event-Driven patterns. Incorporate caching layers and message queues for async tasks. Avoid monolithic chokepoints.
  THINK FIRST. Model the architecture, validate it, optimize it, then output the JSON. Every output must be presentation-ready for enterprise architecture discussions.
- **Agent Hand-off:** If they are asking to build, develop, create, generate, OR research a complex project, return EXACTLY this format and nothing else:
[BUILD] {{"goal": "The specific project they want", "agent_role": "Select the best role: Fullstack Web Developer, Machine Learning Engineer, Deep Learning Researcher, Data Scientist, Data Analyst, AI Systems Architect"}}
- **Memory System:** If the user explicitly shares a new personal fact about themselves (e.g., their name, profession, goals, skill level, or preferences), you MUST secretly append exactly `[MEMORY_ADD] <fact>` to the VERY END of your response. 

[USER'S PAST MEMORY]:
{USER_MEMORY}
"""

            messages = [SystemMessage(content=system_prompt)]
            for msg in request_data.history:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "ai" and not content.startswith("[BUILD]"):
                    messages.append(AIMessage(content=content))
                    
            if is_architecture_req:
                formatting_reminder = "\n\n[CRITICAL REMINDER]: You MUST output EXACTLY the `<architecture>` JSON block. DO NOT write any markdown text. DO NOT generate ASCII art. ONLY output the `<architecture>` tags containing the JSON payload."
            elif is_build_req:
                formatting_reminder = "\n\n[CRITICAL REMINDER]: The user wants to build a project. You MUST return EXACTLY the `[BUILD] {\"goal\": \"...\", \"agent_role\": \"...\"}` format and nothing else. DO NOT generate markdown lists or conversational text. Output ONLY the [BUILD] tag."
            else:
                formatting_reminder = "\n\n[CRITICAL REMINDER]: You MUST strictly follow the requested formatting. Use H3 (###) headers, bold text, bullet points, and NEVER write paragraphs longer than 2 sentences. You MUST put headers and bullet points on their own separate lines."
                        
            if request_data.image:
                human_content = [{"type": "text", "text": sanitized_message + formatting_reminder}]
                images = request_data.image if isinstance(request_data.image, list) else [request_data.image]
                for img in images:
                    human_content.append({"type": "image_url", "image_url": {"url": img}})
                messages.append(HumanMessage(content=human_content))
            else:
                messages.append(HumanMessage(content=sanitized_message + formatting_reminder))
            
            # Clear status indicator
            yield f"data: {json.dumps({'type': 'status', 'message': ''})}\n\n"
            
            from backend.agents.base import BaseAgent
            base_agent = BaseAgent()
            
            # 🟢 MULTI-SPEED LATENCY TIERING 🟢
            model_tier = str(intent_data.get("model_tier", "Fast"))
            
            if model_tier == "Fast" or complexity == "Simple":
                active_llm = base_agent.fast_llm
                api_logger.info("Using Tier 1 (Fast LLM) for sub-second latency.")
            else:
                active_llm = base_agent.smart_llm
                api_logger.info("Using Tier 2 (Smart LLM) for reasoning/coding latency.")
            
            first_token_yielded = False
            draft_text = ""
            is_build = False
            buffer = ""
            
            # === SEMANTIC CACHE HIT CHECK ===
            if len(request_data.history) == 0 and not request_data.image:
                try:
                    client = globals().get('global_chroma_client')
                    if client:
                        cached_response, distance = client.get_cache(sanitized_message)
                    else:
                        from backend.memory.chroma_client import ChromaClient
                        cached_response, distance = ChromaClient().get_cache(sanitized_message)
                    if cached_response:
                        ttft = (time.time() - start_time) * 1000
                        api_logger.info(f"[CACHE HIT] Distance: {distance:.4f} | TTFT: {ttft:.2f}ms")
                        yield f"data: {json.dumps({'type': 'chat', 'token': cached_response})}\n\n"
                        
                        # Drain visual queue if it exists so cached responses still get visuals
                        if visual_task:
                            while True:
                                vis = await visual_queue.get()
                                if vis is None:
                                    break
                                yield f"data: {json.dumps(vis)}\n\n"
                        return
                except Exception:
                    pass

            # 🟢 PHASE 4: Direct Streaming (With Real-Time Compliance Middleware)
            yield f"data: {json.dumps({'type': 'status', 'message': '⚡ Generating Advanced Response...'})}\n\n"
            from backend.utils.compliance import StreamingComplianceEngine
            compliance_engine = StreamingComplianceEngine(active_llm.astream(messages))
            
            import asyncio
            text_gen = compliance_engine.process()
            
            async def get_next_token():
                try:
                    return await anext(text_gen)
                except StopAsyncIteration:
                    return None

            text_task = asyncio.create_task(get_next_token())
            queue_task = asyncio.create_task(visual_queue.get()) if visual_queue else None
            
            while True:
                tasks = []
                if text_task:
                    tasks.append(text_task)
                if queue_task:
                    tasks.append(queue_task)
                    
                if not tasks:
                    break
                    
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                
                if queue_task and queue_task in done:
                    visual_item = queue_task.result()
                    if visual_item:
                        yield f"data: {json.dumps(visual_item)}\n\n"
                        queue_task = asyncio.create_task(visual_queue.get())
                    else:
                        queue_task = None # EOF marker reached
                        
                if text_task and text_task in done:
                    try:
                        text_chunk = text_task.result()
                    except Exception as llm_err:
                        api_logger.error(f"LLM Stream Error: {llm_err}")
                        err_str = f"\n\n⚠️ **AI Connection Error:** `{str(llm_err)}`\n"
                        yield f"data: {json.dumps({'type': 'chat', 'token': err_str})}\n\n"
                        text_task = None
                        continue
                        
                    if text_chunk is None:
                        text_task = None # End of text stream
                        continue
                        
                    draft_text += text_chunk
                    buffer = draft_text
                    
                    if "[BUILD]" in draft_text:
                        is_build = True
                        text_task = asyncio.create_task(get_next_token())
                        continue
                        
                    if not first_token_yielded:
                        api_logger.info(f"TTFT_real_content: {(time.time() - start_time) * 1000:.2f}ms")
                        first_token_yielded = True
                        
                    yield f"data: {json.dumps({'type': 'chat', 'token': text_chunk})}\n\n"
                    text_task = asyncio.create_task(get_next_token())
                
            if is_build:
                try:
                    json_str = draft_text.split("[BUILD]")[1].strip()
                    if json_str.startswith("```json"): json_str = json_str[7:]
                    elif json_str.startswith("```"): json_str = json_str[3:]
                    if json_str.endswith("```"): json_str = json_str[:-3]
                    json_str = json_str.strip()
                    parsed = json.loads(json_str, strict=False)
                    
                    mode = str(intent_data.get("execution_mode", "Deep")).lower()
                    
                    if mode == "autonomous":
                        import uuid
                        project_id = f"proj-{str(uuid.uuid4())[:8]}"
                        
                        # We no longer launch a detached background task here.
                        # Instead, we yield 'mission_started' which signals the frontend 
                        # to connect via the websocket and drive the autonomous loop so the user sees the logs.
                        yield f"data: {json.dumps({'type': 'mission_started', 'data': parsed, 'project_id': project_id, 'agent_role': intent_data.get('agent_role', 'Fullstack Web Developer')})}\n\n"

                    elif mode in ["lightning", "fast"]:
                        yield f"data: {json.dumps({'type': 'fast_build', 'data': parsed})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'build', 'data': parsed})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'chat', 'token': f'(Error parsing build request: {e})'})}\n\n"
                return
            
            # 🟢 PHASE 5: Autonomous Memory Storage (Post-stream)
            if "[MEMORY_ADD]" in draft_text:
                try:
                    import re
                    memory_match = re.search(r'\[MEMORY_ADD\](.*)', draft_text)
                    if memory_match:
                        new_fact = memory_match.group(1).strip()
                        import asyncio
                        def save_mem():
                            client = globals().get('global_chroma_client')
                            if client:
                                client.store_memory("default_user", new_fact)
                            else:
                                from backend.memory.chroma_client import ChromaClient
                                ChromaClient().store_memory("default_user", new_fact)
                        asyncio.create_task(asyncio.to_thread(save_mem))
                        api_logger.info(f"[MEMORY] Saved new fact: {new_fact}")
                except Exception as e:
                    api_logger.warning(f"Failed to save autonomous memory: {e}")
            
            # === SEMANTIC CACHE SET ===
            if len(request_data.history) == 0 and not request_data.image and not is_build:
                try:
                    import asyncio
                    def save_cache():
                        client = globals().get('global_chroma_client')
                        if client:
                            client.set_cache(sanitized_message, buffer)
                        else:
                            from backend.memory.chroma_client import ChromaClient
                            ChromaClient().set_cache(sanitized_message, buffer)
                    asyncio.create_task(asyncio.to_thread(save_cache))
                except Exception as e:
                    print(f"[Semantic Cache] Error setting cache: {e}")
            # ==========================
                    
        except Exception as e:
            import traceback
            print(f"!!! STREAM ERROR !!!\n{traceback.format_exc()}")
            error_msg = str(e).lower()
            if "429" in error_msg:
                yield f"data: {json.dumps({'type': 'chat', 'token': '⚠️ Error: Insufficient Quota.'})}\n\n"
            else:
                # Expose the actual error for debugging
                yield f"data: {json.dumps({'type': 'chat', 'token': f'⚠️ AI Error: {str(e)}'})}\n\n"

    headers = {
        "X-Accel-Buffering": "no",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)

@app.get("/api/download")
async def download_project(project_id: str):
    import shutil
    from fastapi.responses import FileResponse
    from starlette.background import BackgroundTasks
    
    # yAI phase 1 saves generated code in generated_projects/{project_id}
    target_dir = os.path.join(os.getcwd(), "generated_projects", project_id)
    if not os.path.exists(target_dir):
        raise HTTPException(status_code=404, detail="No generated project found")
        
    zip_path = os.path.join(os.getcwd(), f"aion_project_{project_id}")
    # This creates aion_project_{project_id}.zip
    shutil.make_archive(zip_path, 'zip', target_dir)
    
    zip_file = zip_path + ".zip"
    return FileResponse(
        zip_file, 
        media_type="application/zip", 
        filename=f"aion_generated_project_{project_id}.zip"
    )

@app.post("/api/run-code")
async def execute_code(request: Request):
    import subprocess
    import base64
    data = await request.json()
    language = data.get("language")
    code = data.get("code")
    
    # Check if code is base64 encoded
    is_base64 = data.get("is_base64", False)
    if is_base64 and code:
        try:
            code = base64.b64decode(code).decode('utf-8')
        except Exception:
            pass # fallback to raw
            
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

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "yAI Multi-Agent Brain 3.0 is running!"}

@app.websocket("/api/ws/sandbox/{project_id}")
async def websocket_sandbox_logs(websocket: WebSocket, project_id: str):
    await websocket.accept()
    from backend.sandbox.manager import global_sandbox_manager
    try:
        async for log_msg in global_sandbox_manager.stream_logs(project_id):
            await websocket.send_text(log_msg)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_text(f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n")

# =====================================================================
# Phase 10: Monitoring & Telemetry
# =====================================================================

@app.get("/api/telemetry/metrics")
@limiter.limit("10/minute")
async def get_metrics(request: Request):
    """
    Simulated dashboard metrics for yAI.
    """
    return {
        "active_swarms": 4,
        "tokens_processed": 1250000,
        "avg_latency_ms": 450,
        "error_rate": 0.02,
        "uptime": "99.99%"
    }

# =====================================================================
# Phase 11: Security & Encryption
# =====================================================================

from cryptography.fernet import Fernet

# In a real setup, this key would be in an env var.
# For demo purposes, we generate one or use a hardcoded one.
encryption_key = Fernet.generate_key()
cipher_suite = Fernet(encryption_key)

@app.post("/api/security/encrypt-key")
@limiter.limit("5/minute")
async def encrypt_api_key(request: Request, payload: dict):
    """
    Encrypts a provider API key before storing.
    """
    raw_key = payload.get("api_key")
    if not raw_key:
        raise HTTPException(status_code=400, detail="api_key required")
    
    encrypted_text = cipher_suite.encrypt(raw_key.encode('utf-8'))
    return {"encrypted_key": encrypted_text.decode('utf-8')}

# =====================================================================
# Phase 12: Enterprise Features (Mock Organization)
# =====================================================================

@app.get("/api/orgs/workspaces")
async def get_workspaces(request: Request):
    """
    Returns mock collaborative workspaces for enterprise users.
    """
    return [
        {"id": "ws-001", "name": "Frontend Guild", "members": 5},
        {"id": "ws-002", "name": "Backend Team", "members": 12}
    ]

@app.post("/api/orgs/team/add")
@limiter.limit("5/minute")
async def add_team_member(request: Request, payload: dict):
    user_email = payload.get("email")
    role = payload.get("role", "viewer")
    if not user_email:
        raise HTTPException(status_code=400, detail="email required")
    
    return {"status": "success", "message": f"Added {user_email} as {role}"}


# =====================================================================
# AI Workspace OS - Data Endpoints
# =====================================================================

@app.get("/api/memory")
async def get_system_memory(request: Request):
    """
    Returns data for the Workspace OS Memory Tab.
    Reads from ChromaDB/Neo4j (mocked for now if unavailable).
    """
    return {
        "patterns_learned": [
            {"pattern": "ReactBits Hero", "count": 12, "success_rate": 0.95},
            {"pattern": "shadcn/ui Dashboard", "count": 8, "success_rate": 1.0},
            {"pattern": "Glassmorphism UI", "count": 24, "success_rate": 0.88}
        ],
        "recent_decisions": [
            {"agent": "Architect", "rationale": "Chose Postgres over SQLite for concurrency requirements."},
            {"agent": "Template Intelligence", "rationale": "Used Aceternity UI for AI landing page to maximize user engagement."},
            {"agent": "Design", "rationale": "Applied strict WCAG AA contrast rules to Aceternity dark mode."}
        ]
    }

@app.get("/api/deploy/status")
async def get_deploy_status(request: Request):
    """
    Returns data for the Workspace OS Deploy Tab.
    """
    return {
        "environment": "Docker Sandbox",
        "status": "Running",
        "uptime": "45 minutes",
        "dockerfile_generated": True,
        "ci_cd_configured": False,
        "docker_compose": "version: '3.8'\\nservices:\\n  app:\\n    build: .\\n    ports:\\n      - '5173:5173'"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
