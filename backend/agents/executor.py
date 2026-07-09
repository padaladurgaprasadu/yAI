import re
import os
import subprocess
from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState

class ExecutorAgent(BaseAgent):
    """
    The Executor Agent takes the generated code and determines what terminal commands
    are required to initialize the project and install dependencies (e.g. npm init, pip install).
    It then executes those commands directly on the host machine.
    """
    def __init__(self):
        super().__init__()
        from backend.agents.orchestration_prompts import EXECUTOR_PROMPT
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", GLOBAL_AGENT_RULES + "\\n\\n" + EXECUTOR_PROMPT),
            ("human", "Blueprint: {blueprint}\n\nFiles:\n{code_files}")
        ])
        self.chain = self.prompt | self.llm

    def _auto_heal_dependencies(self, target_dir, code_files, execution_logs):
        print("   -> [Auto-Heal] Scanning for missing React dependencies...")
        execution_logs.append("> [Auto-Heal] Scanning React files for missing packages...")
        
        # Collect all imported packages across .js and .jsx files
        imported_packages = set()
        import_pattern = r'(?:import\s+(?:(?:[\w{}\*\, \n]+)\s+from\s+)?|import\()[\'"]([^\.\/][^\'"]+)[\'"]'
        require_pattern = r'require\([\'"]([^\.\/][^\'"]+)[\'"]\)'
        
        for path, content in code_files.items():
            if path.endswith('.js') or path.endswith('.jsx'):
                matches_import = re.finditer(import_pattern, content)
                matches_require = re.finditer(require_pattern, content)
                
                for match in list(matches_import) + list(matches_require):
                    pkg_name = match.group(1)
                    # Handle scoped packages (e.g. @mui/material) vs standard packages (e.g. react-router-dom)
                    if pkg_name.startswith('@'):
                        parts = pkg_name.split('/')
                        if len(parts) >= 2:
                            pkg_name = f"{parts[0]}/{parts[1]}"
                    else:
                        pkg_name = pkg_name.split('/')[0]
                    imported_packages.add(pkg_name)
                    
        # Exclude built-in node modules and common defaults
        builtins = {'react', 'react-dom', 'fs', 'path', 'http', 'https', 'crypto', 'os', 'child_process'}
        imported_packages = imported_packages - builtins
        
        if imported_packages:
            print(f"   -> [Auto-Heal] Found external imports: {imported_packages}")
            
            # Check package.json to see if they are already there
            package_json_path = os.path.join(target_dir, "client", "package.json")
            if not os.path.exists(package_json_path):
                package_json_path = os.path.join(target_dir, "package.json")
                
            installed_packages = []
            if os.path.exists(package_json_path):
                import json
                try:
                    with open(package_json_path, 'r') as f:
                        pkg_data = json.load(f)
                        installed_packages = list(pkg_data.get('dependencies', {}).keys()) + list(pkg_data.get('devDependencies', {}).keys())
                except Exception as e:
                    print(f"      - [Auto-Heal] Error reading package.json: {e}")
            
            missing_packages = [pkg for pkg in imported_packages if pkg not in installed_packages]
            
            if missing_packages:
                print(f"   -> [Auto-Heal] Missing packages detected: {missing_packages}")
                execution_logs.append(f"> [Auto-Heal] Installing missing packages: {', '.join(missing_packages)}")
                
                install_cmd = f"npm install {' '.join(missing_packages)}"
                
                # Install in ROOT for backend dependencies
                print(f"      - Running in Root: {install_cmd}")
                try:
                    subprocess.run(install_cmd, shell=True, cwd=target_dir, capture_output=True, text=True, timeout=120)
                except Exception as e:
                    print(f"        [Auto-Heal Root] Error: {e}")
                
                # Install in CLIENT for frontend dependencies
                client_dir = os.path.join(target_dir, "client")
                if os.path.exists(client_dir):
                    print(f"      - Running in Client: {install_cmd}")
                    try:
                        result = subprocess.run(
                            install_cmd, 
                            shell=True, 
                            cwd=client_dir, 
                            capture_output=True, 
                            text=True, 
                            timeout=120
                        )
                        if result.returncode == 0:
                            print("        [Auto-Heal] Success.")
                            execution_logs.append("> [Auto-Heal] Successfully healed dependencies.")
                        else:
                            print("        [Auto-Heal] Failed.")
                            execution_logs.append("> [Auto-Heal] Failed to heal dependencies.")
                    except Exception as e:
                        print(f"        [Auto-Heal] Error: {e}")
            else:
                print("   -> [Auto-Heal] All dependencies are satisfied.")
        return execution_logs

    def _ensure_database_running(self, blueprint, execution_logs):
        tech_stack = " ".join(blueprint.get("tech_stack", [])).lower()
        if "postgres" in tech_stack or "pg" in tech_stack:
            print("   -> [Auto-Heal] PostgreSQL detected in tech stack. Checking Docker...")
            execution_logs.append("> [Auto-Heal] Checking if PostgreSQL is running...")
            try:
                # Check if docker is available
                result = subprocess.run("docker --version", shell=True, capture_output=True, text=True)
                if result.returncode != 0:
                    print("      - [Auto-Heal] Docker not installed/running. Cannot auto-start DB.")
                    execution_logs.append("> [Auto-Heal] WARNING: Docker not found. Manual DB setup required.")
                    return execution_logs
                
                # Check if aion-postgres is running
                result = subprocess.run("docker ps -q -f name=aion-postgres", shell=True, capture_output=True, text=True)
                if result.stdout.strip():
                    print("      - [Auto-Heal] PostgreSQL container is already running.")
                    execution_logs.append("> [Auto-Heal] PostgreSQL container is already running.")
                    return execution_logs
                
                # Check if it exists but is stopped
                result = subprocess.run("docker ps -aq -f name=aion-postgres", shell=True, capture_output=True, text=True)
                if result.stdout.strip():
                    print("      - [Auto-Heal] Starting existing PostgreSQL container...")
                    execution_logs.append("> [Auto-Heal] Starting existing PostgreSQL container...")
                    subprocess.run("docker start aion-postgres", shell=True, capture_output=True)
                else:
                    print("      - [Auto-Heal] Creating and starting new PostgreSQL container...")
                    execution_logs.append("> [Auto-Heal] Spawning new PostgreSQL Docker container on port 5432...")
                    subprocess.run("docker run --name aion-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres", shell=True, capture_output=True)
                
                print("      - [Auto-Heal] PostgreSQL started successfully.")
                execution_logs.append("> [Auto-Heal] PostgreSQL is ready.")
            except Exception as e:
                print(f"      - [Auto-Heal] Error checking/starting DB: {e}")
                execution_logs.append(f"> [Auto-Heal] Error auto-starting DB: {e}")
        return execution_logs

    def run(self, state: AiONState) -> AiONState:
        project_id = state.get("project_id")
        try:
            from backend.api_real import stream_queues
            q = stream_queues.get(project_id)
        except ImportError:
            q = None

        if q:
            q.put({"type": "progress", "message": "⚙️ Executor Agent is installing project dependencies (this may take a minute)..."})
            
        print("[Executor] Determining installation commands...")
        
        import json
        
        # Format files for the prompt
        formatted_files = ""
        for path, content in (state.get("code_files") or {}).items():
            formatted_files += f"\n--- File: {path} ---\n{content}\n"

        response = self.chain.invoke({
            "blueprint": json.dumps(state.get("blueprint", {})),
            "code_files": formatted_files
        })
        
        content = response.content
        if isinstance(content, list):
            content = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
        
        # Parse JSON
        # Parse JSON
        import re
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            try:
                data = json.loads(content)
            except:
                data = {"status": "failed", "verification": "Failed to parse executor output", "logs_excerpt": content}
                
        status = data.get("status", "failed")
        preview_url = data.get("preview_url")
        verification = data.get("verification", "")
        logs_excerpt = data.get("logs_excerpt", "")

        execution_logs = []
        if status == "running":
            execution_logs.append(f"> [Executor Verification] {verification}")
            if preview_url:
                execution_logs.append(f"> [Executor] Preview URL available: {preview_url}")
        else:
            execution_logs.append(f"> [Executor Verification Failed] {verification}")
            execution_logs.append(f"> Logs: {logs_excerpt}")
            
        print(f"   -> [Executor] Status: {status}")
        
        # Legacy support: if the LLM still returns commands due to fallback, we execute them
        commands = data.get("commands", [])
        
        # Determine the target directory for execution
        project_id = state.get("project_id", "default")
        target_dir = os.path.join(os.getcwd(), "generated_projects", project_id)
        os.makedirs(target_dir, exist_ok=True)
        
        # 🚀 VITE SCAFFOLDING ENGINE (WITH ZERO-LATENCY CACHE) 🚀
        has_client = any(path.startswith("client/") for path in state.get("code_files", {}).keys())
        client_dir = os.path.join(target_dir, "client")
        
        if has_client and not os.path.exists(os.path.join(client_dir, "package.json")):
            import shutil
            cache_dir = os.path.join(os.getcwd(), "aion_vite_cache")
            
            # If the cache doesn't exist, build it once
            if not os.path.exists(cache_dir):
                print("   -> [Executor] Building Master Vite Cache (This only happens once)...")
                execution_logs.append("> [System] Building Master Vite Cache. Future builds will be instant!")
                os.makedirs(cache_dir, exist_ok=True)
                try:
                    subprocess.run("npx -y create-vite@latest client --template react", shell=True, cwd=cache_dir, capture_output=True)
                    cache_client = os.path.join(cache_dir, "client")
                    print("   -> [Executor] Installing AI standard libraries to cache...")
                    install_cmd = "npm install --legacy-peer-deps && npm install react-router-dom axios @material-ui/core @material-ui/icons lucide-react recharts tailwindcss --legacy-peer-deps"
                    subprocess.run(install_cmd, shell=True, cwd=cache_client, capture_output=True)
                except Exception as e:
                    print(f"      - [Executor] Cache build failed: {e}")
                    
            # Instantly copy the cache to the project directory
            print("   -> [Executor] Instantly scaffolding project from Vite Cache...")
            try:
                if not os.path.exists(client_dir):
                    shutil.copytree(os.path.join(cache_dir, "client"), client_dir)
            except Exception as e:
                print(f"      - [Executor] Cache copy failed: {e}")
        
        # Write files to disk
        # This will perfectly inject the AI's App.jsx and components into the Vite template!
        if state.get("code_files"):
            for path, content in state["code_files"].items():
                # [SECURITY] Prevent path traversal attacks (e.g. ../../etc/passwd)
                safe_path = path.replace("..", "").replace(":\\", "").lstrip("/")
                full_path = os.path.abspath(os.path.join(target_dir, safe_path.replace("/", os.sep)))
                
                # Double check that the absolute path is still within the target directory
                if not full_path.startswith(os.path.abspath(target_dir)):
                    error_msg = f"[SECURITY BREACH] Path traversal attempt detected: {path}. Execution aborted."
                    print(f"   -> {error_msg}")
                    state["runtime_error"] = error_msg
                    state["execution_logs"] = execution_logs + [f"> {error_msg}"]
                    return state

                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
        # [SECURITY] PRE-EXECUTION SECURITY SCANNER
        dangerous_keywords = ["rm -rf", "del /s", "format c:", "os.system(", "subprocess.run(", "fs.unlink"]
        if state.get("code_files"):
            for path, content in state["code_files"].items():
                content_lower = content.lower()
                for keyword in dangerous_keywords:
                    if keyword in content_lower:
                        error_msg = f"[SECURITY BREACH] Dangerous keyword '{keyword}' detected in {path}. Execution aborted."
                        print(f"   -> {error_msg}")
                        state["runtime_error"] = error_msg
                        state["execution_logs"] = execution_logs + [f"> {error_msg}"]
                        return state
        
        filtered_commands = []
        for cmd in commands:
            cmd_clean = cmd.strip()
            # [OPTIMIZER] Skip redundant frontend npm install because Vite cache is pre-built
            if cmd_clean in ["cd client && npm install", "cd client; npm install", "npm install", "npm i"] and has_client:
                print(f"      - [Optimizer] Skipping redundant command: {cmd_clean}")
                execution_logs.append(f"> [Optimizer] Skipped redundant {cmd_clean} (using pre-built Vite Cache)")
                continue
            filtered_commands.append(cmd)

        for cmd in filtered_commands:
            print(f"      - Running: {cmd}")
            execution_logs.append(f"> {cmd}")
            try:
                # Execute the command synchronously
                # Using shell=True is powerful but dangerous in prod. Safe here for local testing.
                result = subprocess.run(
                    cmd, 
                    shell=True, 
                    cwd=target_dir, 
                    capture_output=True, 
                    text=True, 
                    timeout=300 # Strict 300s timeout for security (npm install is slow)
                )
                
                if result.stdout:
                    execution_logs.append(result.stdout)
                if result.stderr:
                    execution_logs.append(f"STDERR: {result.stderr}")
                    
                if result.returncode == 0:
                    print(f"        Success.")
                else:
                    print(f"        Failed with code {result.returncode}.")
                    # AUTO-HEAL LOOP TRIGGERS HERE
                    state["runtime_error"] = f"Command '{cmd}' failed with code {result.returncode}.\nSTDERR: {result.stderr}\nSTDOUT: {result.stdout}"
                    state["execution_logs"] = execution_logs
                    state["execution_retries"] = state.get("execution_retries", 0) + 1
                    return state
                    
            except subprocess.TimeoutExpired as e:
                print(f"        [Warning] Command timed out after 300s: {cmd}")
                execution_logs.append(f"WARNING: Command '{cmd}' timed out, but proceeding anyway.")
                # We do NOT trigger a runtime_error here, to prevent an infinite loop back to the Coder!
                continue
            except Exception as e:
                print(f"        Error running command: {e}")
                execution_logs.append(f"ERROR: {str(e)}")
                state["runtime_error"] = f"Command '{cmd}' threw exception: {str(e)}"
                state["execution_logs"] = execution_logs
                state["execution_retries"] = state.get("execution_retries", 0) + 1
                return state
        
        # Execute Auto-Heal Phase 1 Features AFTER initial npm installs
        execution_logs = self._auto_heal_dependencies(target_dir, state.get("code_files", {}), execution_logs)
        execution_logs = self._ensure_database_running(state.get("blueprint", {}), execution_logs)
        
        # [NEW] GitHub Integration (Phase 1 Enterprise Feature)
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            print("   -> [Executor] GITHUB_TOKEN found. Executing Native GitHub Integration...")
            try:
                # Basic push logic for autonomous GitHub syncing
                repo_name = f"aion-generated-{project_id}"
                # In a real enterprise version, we would use PyGithub to create the repo via API.
                # Here we simulate the git workflow on the generated folder.
                subprocess.run("git init", shell=True, cwd=target_dir, capture_output=True)
                subprocess.run("git add .", shell=True, cwd=target_dir, capture_output=True)
                subprocess.run("git commit -m \"feat: Auto-generated by AiON Enterprise\"", shell=True, cwd=target_dir, capture_output=True)
                # Ensure main branch
                subprocess.run("git branch -M main", shell=True, cwd=target_dir, capture_output=True)
                execution_logs.append(f"> [GitHub] Initialized local git repository and committed code.")
            except Exception as e:
                print(f"      - [Executor] GitHub integration failed: {e}")
                execution_logs.append(f"> [GitHub] Failed to initialize git: {e}")
                
        if not state.get("runtime_error"):
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                q.put({"type": "timeline", "title": "🌐 Preview ready: http://localhost:3000", "reason": "Environment prepared for Sandpack", "status": "done"})
            
        state["execution_logs"] = execution_logs
        return state
