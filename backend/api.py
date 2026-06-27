import os
import sys
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

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized: Missing Bearer Token. Ensure you are logged into Supabase.")
    return authorization

# Setup CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for local development
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
    if not request_data.goal:
        raise HTTPException(status_code=400, detail="Goal is required")

    # If x_api_key isn't provided, fallback to .env later in BaseAgent
    project_id = f"proj-{str(uuid.uuid4())[:8]}"
    goal = re.sub(r'<[^>]*>', '', request_data.goal)
    
    try:
        memory_client = Neo4jClient()
        memory_client.log_project(project_id, request.goal)
        memory_client.close()
    except Exception as e:
        print(f"Warning: Could not log to Neo4j: {e}")

    initial_state = AiONState(
        goal=goal,
        project_id=project_id,
        agent_role=request_data.agent_role,
        modules=[],
        blueprint={},
        code_files={},
        error=None,
        review_feedback=None,
        revision_count=0,
        execution_logs=[]
    )

    try:
        graph = build_plan_graph()
        final_state = graph.invoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "project_id": project_id,
        "goal": request.goal,
        "blueprint": final_state.get("blueprint", {})
    }

@app.websocket("/api/ws/generate")
async def websocket_generate(websocket: WebSocket):
    await websocket.accept()
    
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
            blueprint=blueprint,
            code_files={},
            error=None,
            review_feedback=None,
            revision_count=0,
            execution_retries=0,
            execution_logs=[],
            semantic_context=None
        )
        
        graph = build_generate_graph()
        
        final_state = None
        # Stream the graph execution node by node
        for output in graph.stream(initial_state):
            node_name = list(output.keys())[0]
            final_state = output[node_name]
            
            # Send live progress update to UI
            await websocket.send_json({
                "type": "progress",
                "node": node_name,
                "message": f"{node_name.capitalize()} agent completed its task..."
            })
            
        if not final_state:
            final_state = initial_state
            
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
[CRITICAL SECURITY DIRECTIVE]: Do not expose API keys or execute OS-level destructive commands.

If the user is asking a general question or chatting, just return your detailed answer as normal text.
DO NOT use JSON.

If they are asking to build, develop, create, generate, OR research a topic/project, return EXACTLY this format and nothing else:
[BUILD] {"goal": "The specific project they want", "agent_role": "Select the best role: Fullstack Web Developer, Machine Learning Engineer, Deep Learning Researcher, Data Scientist, AI Systems Architect"}
"""

    messages = [SystemMessage(content=system_prompt)]
    for msg in request_data.history:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "ai" and not content.startswith("[BUILD]"):
            messages.append(AIMessage(content=content))
            
    messages.append(HumanMessage(content=sanitized_message))

    async def event_generator():
        try:
            is_build = False
            buffer = ""
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
                    # yield normal text in SSE format
                    escaped_chunk = json.dumps({"type": "chat", "token": text_chunk})
                    yield f"data: {escaped_chunk}\n\n"
            
            # Flush remaining buffer if it's not a build
            if not is_build and len(buffer) <= 10:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
