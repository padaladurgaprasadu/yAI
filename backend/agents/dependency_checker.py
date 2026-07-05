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
        
        if missing_files:
            print(f"   -> [FAILED] Found {len(missing_files)} missing dependencies!")
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                q.put({"type": "timeline", "title": f"Missing Files Detected", "reason": f"Need to generate {len(missing_files)} missing dependencies", "status": "done"})
        else:
            print("   -> [SUCCESS] All local dependencies exist.")
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                q.put({"type": "timeline", "title": "Verification Passed", "reason": "All local dependencies exist", "status": "done"})
                
        return state
