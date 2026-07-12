import os
import json
from langchain_core.prompts import ChatPromptTemplate
from backend.utils.model_registry import AIModelRegistry
from backend.orchestrator.state import AiONState
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class RepositoryIntelligenceAgent:
    def __init__(self):
        # We use the Architecture capability (GLM-5.2/GPT-OSS equivalent) for deep repository understanding
        self.llm = AIModelRegistry.get_llm_chain(capability="architecture", temperature=0.1)
        
        self.ignore_dirs = {
            "node_modules", "venv", ".venv", "env", ".git", ".next", 
            "dist", "build", "__pycache__", ".vscode", ".idea", "coverage"
        }
        self.max_files = 150
        self.max_depth = 4

    def _scan_directory(self, root_path: str) -> dict:
        """Scans the directory and builds a tree representation."""
        tree = {}
        file_count = 0
        
        for dirpath, dirnames, filenames in os.walk(root_path):
            # Prune ignored directories
            dirnames[:] = [d for d in dirnames if d not in self.ignore_dirs]
            
            rel_path = os.path.relpath(dirpath, root_path)
            if rel_path == ".":
                depth = 0
            else:
                depth = rel_path.count(os.sep) + 1
                
            if depth > self.max_depth:
                continue
                
            current_level = tree
            if rel_path != ".":
                parts = rel_path.split(os.sep)
                for part in parts:
                    if part not in current_level:
                        current_level[part] = {}
                    current_level = current_level[part]
            
            for f in filenames:
                if file_count >= self.max_files:
                    current_level["..."] = "[Truncated due to size]"
                    break
                current_level[f] = "file"
                file_count += 1
                
            if file_count >= self.max_files:
                break
                
        return tree

    def _extract_dependencies(self, root_path: str) -> dict:
        """Extracts dependencies from package.json or requirements.txt if present."""
        deps = {}
        
        # Check Node.js
        package_json = os.path.join(root_path, "package.json")
        if os.path.exists(package_json):
            try:
                with open(package_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    deps["npm"] = {
                        "dependencies": data.get("dependencies", {}),
                        "devDependencies": data.get("devDependencies", {})
                    }
            except Exception as e:
                logger.warning(f"[Repository Agent] Failed to read package.json: {e}")
                
        # Check Python
        req_txt = os.path.join(root_path, "requirements.txt")
        if os.path.exists(req_txt):
            try:
                with open(req_txt, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    deps["pip"] = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
            except Exception as e:
                logger.warning(f"[Repository Agent] Failed to read requirements.txt: {e}")
                
        return deps

    def run(self, state: AiONState) -> AiONState:
        project_id = state.get("project_id", "unknown")
        goal = state.get("goal", "")
        
        workspace_path = os.path.abspath(os.path.join("workspace", "projects", project_id))
        
        print(f"\n--- Repository Intelligence Layer: Indexing Project ---")
        if not os.path.exists(workspace_path):
            print(f"   -> No existing repository found at {workspace_path}. Skipping.")
            state["repository_context"] = "No existing repository. Starting fresh."
            return state
            
        print(f"   -> Scanning folder structure and dependencies...")
        
        tree = self._scan_directory(workspace_path)
        deps = self._extract_dependencies(workspace_path)
        
        if not tree and not deps:
            print("   -> Repository is empty.")
            state["repository_context"] = "Repository exists but is currently empty."
            return state
            
        system_prompt = """
        You are the Repository Intelligence Layer of the yAI Engineering OS.
        Your job is to analyze an existing software repository and generate a concise 'Internal Knowledge Graph'.
        
        You will be provided with:
        1. The user's new goal.
        2. The current directory tree of the repository.
        3. The extracted dependencies (e.g., from package.json or requirements.txt).
        
        Generate a clear, markdown-formatted architecture summary that explains:
        - Tech Stack & Dependencies
        - Core Architecture (Frontend, Backend, Database)
        - Key files and what they likely do based on their names.
        
        This summary will be injected into the Planner and Architect agents. It must be highly accurate so they do not hallucinate file paths or rewrite existing working code.
        Never invent files that are not in the tree.
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Goal: {goal}\n\nDirectory Tree:\n{tree}\n\nDependencies:\n{deps}")
        ])
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({
                "goal": goal,
                "tree": json.dumps(tree, indent=2),
                "deps": json.dumps(deps, indent=2)
            })
            
            repo_context = response.content.strip()
            state["repository_context"] = repo_context
            print("   -> Built Internal Knowledge Graph successfully.")
            
        except Exception as e:
            logger.error(f"[Repository Agent] Analysis failed: {e}")
            state["repository_context"] = f"Failed to analyze repository: {str(e)}\n\nRaw Tree:\n{json.dumps(tree)}"
            
        return state
