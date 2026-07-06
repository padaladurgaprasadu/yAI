import re
import posixpath
import json
from backend.orchestrator.state import AiONState

class DependencyCheckerAgent:
    """
    Runtime Guardian Agent (formerly Dependency Checker).
    Performs a deterministic virtual compilation check:
    1. Parses all generated React code for relative imports.
    2. Uses a Virtual File System to resolve paths.
    3. AUTONOMOUSLY REWRITES incorrect import paths if the file exists elsewhere in the project.
    4. Automatically injects missing external NPM dependencies into package.json.
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
            q.put({"type": "timeline", "title": "Runtime Guardian", "reason": "Simulating Node.js compilation and auto-healing imports", "status": "active"})
            q.put({"type": "progress", "message": "🛡️ Runtime Guardian is verifying the abstract syntax tree..."})
            
        print("[Runtime Guardian] Scanning for missing local imports and resolving virtual paths...")
        
        missing_files = set()
        
        # Regex to match `import ... from './local/path'` or `import './local/style.css'`
        import_regex = re.compile(r'import\s+(?:.*?\s+from\s+)?[\'"]([./].*?)[\'"]')
        
        # Build a Virtual File System Lookup
        basename_to_paths = {}
        for fp in code_files.keys():
            basename = posixpath.basename(fp).split('.')[0]
            if basename not in basename_to_paths:
                basename_to_paths[basename] = []
            basename_to_paths[basename].append(fp)
        
        # Phase 1: Virtual Path Resolution & Auto-Healing
        healed_imports_count = 0
        
        for file_path in list(code_files.keys()):
            content = code_files[file_path]
            if not file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                continue
                
            dir_path = posixpath.dirname(file_path)
            
            matches = import_regex.findall(content)
            for match in matches:
                # e.g., '../contexts/AuthContext'
                resolved_path = posixpath.normpath(posixpath.join(dir_path, match))
                
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
                    # HEAL ATTEMPT: Check if the file exists elsewhere by basename
                    target_basename = posixpath.basename(match).split('.')[0]
                    candidates = basename_to_paths.get(target_basename, [])
                    
                    if candidates:
                        best_candidate = candidates[0]
                        # Compute new relative path from dir_path to best_candidate
                        new_rel_path = posixpath.relpath(best_candidate, dir_path)
                        if not new_rel_path.startswith('.'):
                            new_rel_path = './' + new_rel_path
                            
                        # Strip extension for React imports if it was .jsx or .js
                        if new_rel_path.endswith('.jsx') or new_rel_path.endswith('.js'):
                            new_rel_path = new_rel_path.rsplit('.', 1)[0]
                            
                        # Safely replace the import strings
                        old_import_single = f"'{match}'"
                        new_import_single = f"'{new_rel_path}'"
                        old_import_double = f'"{match}"'
                        new_import_double = f'"{new_rel_path}"'
                        
                        if old_import_single in content or old_import_double in content:
                            content = content.replace(old_import_single, new_import_single)
                            content = content.replace(old_import_double, new_import_double)
                            code_files[file_path] = content
                            healed_imports_count += 1
                            print(f"   -> [Guardian Healed] Rewrote import in '{file_path}': {match} -> {new_rel_path}")
                        else:
                            # If exact match failed due to spacing, fallback to reporting missing
                            target_missing = resolved_path if '.' in match.split('/')[-1] else f"{resolved_path}.jsx"
                            missing_files.add(target_missing)
                    else:
                        print(f"   -> [Missing] '{file_path}' imports '{match}', but no candidate exists.")
                        target_missing = resolved_path if '.' in match.split('/')[-1] else f"{resolved_path}.jsx"
                        missing_files.add(target_missing)

        state["missing_dependencies"] = list(missing_files)
        
        # Phase 2: External Dependency Injection
        print("[Runtime Guardian] Verifying external NPM dependencies...")
        external_regex = re.compile(r'(?:import|require)\s*\(?.*?[\'"]([a-zA-Z@][^:\"\'\s]+)[\'"]\)?')
        
        external_deps = set()
        for file_path, content in code_files.items():
            if not file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                continue
                
            matches = external_regex.findall(content)
            for match in matches:
                parts = match.split('/')
                if match.startswith('@') and len(parts) >= 2:
                    pkg_name = f"{parts[0]}/{parts[1]}"
                else:
                    pkg_name = parts[0]
                    
                builtins = {'path', 'fs', 'http', 'https', 'os', 'crypto', 'stream', 'util', 'events', 'url'}
                # Strict filter for @types which cause sandbox crashes
                if pkg_name not in builtins and not pkg_name.startswith('.') and not pkg_name.startswith('@types/'):
                    external_deps.add(pkg_name)
                    
        # Find client package.json
        pkg_json_path = next((p for p in code_files.keys() if p.endswith('package.json') and 'client' in p), None)
        if not pkg_json_path:
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
                        print(f"   -> [Guardian Injected] Added missing NPM package '{pkg}' to {pkg_json_path}")
                        
                code_files[pkg_json_path] = json.dumps(pkg_data, indent=2)
                state["code_files"] = code_files
            except json.JSONDecodeError:
                print(f"   -> [WARNING] Failed to parse {pkg_json_path}. Cannot inject external dependencies.")
        
        if missing_files:
            print(f"   -> [FAILED] Found {len(missing_files)} completely missing files.")
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                q.put({"type": "timeline", "title": f"Files Missing", "reason": f"Routing to Swarm for {len(missing_files)} files", "status": "done"})
        else:
            msg = f"Compiled virtually. Healed {healed_imports_count} paths, injected {injected_count} packages."
            print(f"   -> [SUCCESS] {msg}")
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                q.put({"type": "timeline", "title": "Runtime Guardian Passed", "reason": msg, "status": "done"})
                
        return state
