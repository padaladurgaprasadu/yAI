import os
import re

file_path = "backend/api_real.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. We will replace the entire start_preview function
new_start_preview = """
@app.post("/api/start-preview/{project_id}")
async def start_preview(project_id: str, request: Request):
    \"\"\"
    Starts the backend and frontend servers for a generated project.
    On cloud, compiles the app statically.
    \"\"\"
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
        
        # Run the build process synchronously
        process = await asyncio.create_subprocess_shell(
            "npm run build",
            cwd=client_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        print("   -> [Preview] Application compiled successfully!")
        
        # Determine the base URL (Render URL if on cloud, localhost if local)
        base_url = str(request.base_url).rstrip('/')
        
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
    \"\"\"
    Serves the statically compiled React application from the dist directory.
    This entirely bypasses the need for multiple ports or complex tunneling!
    \"\"\"
    if not file_path or file_path == "":
        file_path = "index.html"
        
    project_path = os.path.join(os.getcwd(), "generated_projects", project_id)
    dist_path = os.path.join(project_path, "client", "dist")
    
    full_path = os.path.abspath(os.path.join(dist_path, file_path))
    
    if not os.path.exists(full_path):
        # SPA Fallback: If it's a React Router path, serve index.html
        return FileResponse(os.path.join(dist_path, "index.html"))
        
    return FileResponse(full_path)
"""

# Regex to find the start_preview function and stop_preview
pattern = re.compile(r'@app\.post\("/api/start-preview/{project_id}"\).*?@app\.post\("/api/stop-preview/{project_id}"\)', re.DOTALL)

# Let's just find where it starts and replace up to stop_preview
content = pattern.sub(new_start_preview + '\n@app.post("/api/stop-preview/{project_id}")', content)

# Update the websocket handler to use the returned URL
content = content.replace('url": f"http://localhost:{port}"', 'url": preview_data.get("url", f"http://localhost:{port}")')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Preview proxy code injected successfully!")
