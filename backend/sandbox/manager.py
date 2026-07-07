import os
import subprocess
import asyncio
import json
import socket
import threading
from typing import Dict, Optional

class SandboxManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SandboxManager, cls).__new__(cls)
            cls._instance.active_sandboxes = {}
            cls._instance.workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace", "projects"))
            os.makedirs(cls._instance.workspace_root, exist_ok=True)
        return cls._instance

    def _find_available_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    async def start_sandbox(self, project_id: str, code_files: Dict[str, str], framework: str = "node") -> dict:
        """
        Writes files to disk and starts the backend server in a subprocess.
        """
        # 1. Save files
        project_dir = os.path.join(self.workspace_root, project_id)
        os.makedirs(project_dir, exist_ok=True)
        
        for file_path, content in code_files.items():
            full_path = os.path.join(project_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        # 2. Determine port and command
        port = self._find_available_port()
        env = os.environ.copy()
        env["PORT"] = str(port)
        
        # Check if we need to install dependencies first
        has_root_package_json = "package.json" in code_files
        has_root_requirements = "requirements.txt" in code_files
        has_server_package_json = "server/package.json" in code_files
        has_server_requirements = "server/requirements.txt" in code_files
        
        cmd = ""
        if has_server_package_json:
            cmd = "cd server && npm install --legacy-peer-deps && npm run dev"
        elif has_server_requirements:
            cmd = "cd server && pip install -r requirements.txt && python app.py"
        elif has_root_package_json:
            cmd = "npm install --legacy-peer-deps && npm run dev"
        elif has_root_requirements:
            cmd = "pip install -r requirements.txt && python app.py"
        else:
            # Fallback based on files present
            if any(k.startswith("server/") and k.endswith(".py") for k in code_files):
                cmd = "cd server && python app.py"
            else:
                cmd = "python app.py"
            
        print(f"[Sandbox] Starting project {project_id} on port {port} with cmd: {cmd}")
        
        # 3. Start subprocess
        process = subprocess.Popen(
            cmd,
            shell=True,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1, # Line buffered
            universal_newlines=True
        )
        
        # 4. Setup log queue
        log_queue = asyncio.Queue()
        
        # Background thread to read stdout and put into asyncio queue
        def reader_thread(proc, q, loop):
            try:
                for line in iter(proc.stdout.readline, ''):
                    if not line: break
                    asyncio.run_coroutine_threadsafe(q.put(line), loop)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(q.put(f"[Sandbox Error] {str(e)}\n"), loop)
            finally:
                asyncio.run_coroutine_threadsafe(q.put(None), loop) # EOF marker
                
        loop = asyncio.get_running_loop()
        thread = threading.Thread(target=reader_thread, args=(process, log_queue, loop), daemon=True)
        thread.start()
        
        self.active_sandboxes[project_id] = {
            "process": process,
            "port": port,
            "queue": log_queue,
            "url": f"http://localhost:{port}"
        }
        
        # 5. HEALTH CHECK POLLING LOOP
        # Wait until the port actually accepts connections before returning success.
        # Timeout after 45 seconds to prevent hanging forever.
        import time
        start_time = time.time()
        timeout = 45
        
        while time.time() - start_time < timeout:
            # Check if process died prematurely
            if process.poll() is not None:
                return {
                    "status": "error",
                    "message": f"Server crashed during startup with exit code {process.returncode}"
                }
                
            try:
                # Try to connect to the port
                with socket.create_connection(('localhost', port), timeout=1):
                    # If we can connect, the web server is bound and ready!
                    return {
                        "status": "running",
                        "port": port,
                        "url": f"http://localhost:{port}"
                    }
            except (ConnectionRefusedError, TimeoutError, OSError):
                # Port not open yet, wait and try again
                await asyncio.sleep(2)
                
        # If we exit the loop, we timed out
        return {
            "status": "error",
            "message": "Backend failed to start within 45s. Check terminal logs."
        }

    async def stream_logs(self, project_id: str):
        """
        Async generator to stream logs from the sandbox queue.
        """
        if project_id not in self.active_sandboxes:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Sandbox not found'})}\n\n"
            return
            
        queue = self.active_sandboxes[project_id]["queue"]
        while True:
            line = await queue.get()
            if line is None:
                break
            yield f"data: {json.dumps({'type': 'log', 'data': line})}\n\n"
            
    def stop_sandbox(self, project_id: str):
        if project_id in self.active_sandboxes:
            proc = self.active_sandboxes[project_id]["process"]
            try:
                proc.terminate()
            except:
                pass
            del self.active_sandboxes[project_id]
            print(f"[Sandbox] Stopped project {project_id}")

global_sandbox_manager = SandboxManager()
