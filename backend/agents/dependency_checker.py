import re
import posixpath
from backend.orchestrator.state import AiONState

class DependencyCheckerAgent:
    """
    Deterministic Build Verification Agent.
    Scans generated React code for relative imports and ensures the targeted files actually exist
    in the generated bundle. If not, it flags them so the Coder can generate them.
    """
    
    def run(self, state: AiONState) -> AiONState:
        project_id = state.get("project_id")
        code_files = state.get("code_files", {})
        
        try:
            from backend.api_real import stream_queues
            q = stream_queues.get(project_id)
        except ImportError:
            q = None

        if q:
            q.put({"type": "agent_state", "agent": "reviewer"})
            q.put({"type": "timeline", "title": "Build Verification", "reason": "Scanning dependency graph for missing files", "status": "active"})
            q.put({"type": "progress", "message": "🔍 Verifying internal dependencies..."})
            
        print("[Dependency Checker] Scanning for missing local imports...")
        
        missing_files = set()
        
        # Regex to match `import ... from './local/path'` or `import './local/style.css'`
        import_regex = re.compile(r'import\s+(?:.*?\s+from\s+)?[\'"]([./].*?)[\'"]')
        
        for file_path, content in code_files.items():
            if not file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                continue
                
            dir_path = posixpath.dirname(file_path)
            
            # Find all local imports
            matches = import_regex.findall(content)
            for match in matches:
                # match is something like '../contexts/AuthContext' or './App.css'
                # Resolve the virtual path
                resolved_path = posixpath.normpath(posixpath.join(dir_path, match))
                
                # We need to check if resolved_path exists in code_files, 
                # but React imports often omit extensions (.jsx, .js, .css, .tsx, .ts)
                possible_paths = [
                    resolved_path,
                    f"{resolved_path}.jsx",
                    f"{resolved_path}.js",
                    f"{resolved_path}.tsx",
                    f"{resolved_path}.ts",
                    f"{resolved_path}.css",
                    f"{resolved_path}/index.jsx",
                    f"{resolved_path}/index.js"
                ]
                
                found = any(p in code_files for p in possible_paths)
                
                if not found:
                    print(f"   -> [Missing] '{file_path}' imports '{match}', but it does not exist!")
                    # The missing path is most likely a .jsx component if it doesn't have an extension
                    target_missing = resolved_path if '.' in match.split('/')[-1] else f"{resolved_path}.jsx"
                    missing_files.add(target_missing)

        state["missing_dependencies"] = list(missing_files)
        
        # --- PHASE 2: EXTERNAL DEPENDENCY INJECTION ---
        print("[Dependency Checker] Scanning for external NPM dependencies...")
        external_regex = re.compile(r'(?:import|require)\s*\(?.*?[\'"]([a-zA-Z@][^:\"\'\s]+)[\'"]\)?')
        
        external_deps = set()
        for file_path, content in code_files.items():
            if not file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                continue
                
            matches = external_regex.findall(content)
            for match in matches:
                # Get root package name. E.g., '@apollo/client/core' -> '@apollo/client', 'axios/lib' -> 'axios'
                parts = match.split('/')
                if match.startswith('@') and len(parts) >= 2:
                    pkg_name = f"{parts[0]}/{parts[1]}"
                else:
                    pkg_name = parts[0]
                    
                # Ignore built-in node modules (basic list)
                builtins = {'path', 'fs', 'http', 'https', 'os', 'crypto', 'stream', 'util', 'events', 'url'}
                if pkg_name not in builtins and not pkg_name.startswith('.'):
                    external_deps.add(pkg_name)
                    
        # Inject into package.json
        import json
        pkg_json_path = next((p for p in code_files.keys() if p.endswith('package.json')), None)
        injected_count = 0
        
        if pkg_json_path and external_deps:
            try:
                pkg_data = json.loads(code_files[pkg_json_path])
                if "dependencies" not in pkg_data:
                    pkg_data["dependencies"] = {}
                    
                for pkg in external_deps:
                    if pkg not in pkg_data["dependencies"]:
                        pkg_data["dependencies"][pkg] = "latest"
                        injected_count += 1
                        print(f"   -> [Auto-Heal] Injected missing NPM package '{pkg}' into {pkg_json_path}")
                        
                code_files[pkg_json_path] = json.dumps(pkg_data, indent=2)
                state["code_files"] = code_files
            except json.JSONDecodeError:
                print(f"   -> [WARNING] Failed to parse {pkg_json_path}. Cannot inject external dependencies.")
        
        # --- END PHASE 2 ---
        
        if missing_files:
            print(f"   -> [FAILED] Found {len(missing_files)} missing local dependencies!")
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                q.put({"type": "timeline", "title": f"Missing Files Detected", "reason": f"Need to generate {len(missing_files)} missing local files", "status": "done"})
        else:
            msg = "All local files exist." if injected_count == 0 else f"Injected {injected_count} missing NPM packages."
            print(f"   -> [SUCCESS] {msg}")
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                q.put({"type": "timeline", "title": "Dependencies Verified", "reason": msg, "status": "done"})
                
        return state
