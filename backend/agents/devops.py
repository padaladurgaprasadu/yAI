import json
import re
from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState

class DevOpsAgent(BaseAgent):
    """
    The DevOps Agent analyzes the completed codebase and automatically generates
    production-ready deployment infrastructure, including Dockerfiles,
    Docker Compose orchestration (with Prometheus/Grafana observability),
    and GitHub Actions CI/CD pipelines.
    """
    def __init__(self):
        super().__init__()
        from backend.agents.base import GLOBAL_AGENT_RULES
        from backend.agents.orchestration_prompts import DEVOPS_PROMPT
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", GLOBAL_AGENT_RULES + "\\n\\n" + DEVOPS_PROMPT),
            ("human", "Blueprint:\n{blueprint}\n\nFiles:\n{code_files}")
        ])
        self.chain = self.prompt | self.llm

    def run(self, state: AiONState) -> AiONState:
        project_id = state.get("project_id")
        try:
            from backend.api_real import stream_queues
            q = stream_queues.get(project_id)
        except ImportError:
            q = None

        if q:
            q.put({"type": "agent_state", "agent": "devops"})
            q.put({"type": "timeline", "title": "☸️ DevOps: Generating deployment files...", "reason": "✅ Dockerfile\n✅ docker-compose.yml\n✅ GitHub Actions CI/CD", "status": "active"})
            
        print("[DevOps] Generating deployment files (Docker, CI/CD)...")
        
        # Format files for the prompt (TOKEN OPTIMIZATION)
        # The DevOps agent only needs backend dependencies and entry points to write a Dockerfile.
        # We strip out frontend components (.jsx, .css) to save massive amounts of tokens.
        formatted_files = ""
        for path, content in (state.get("code_files") or {}).items():
            if path.endswith((".jsx", ".css", ".html")) or "client/src/components" in path:
                continue
            formatted_files += f"\n--- File: {path} ---\n{content}\n"

        response = self.chain.invoke({
            "blueprint": json.dumps(state.get("blueprint", {})),
            "code_files": formatted_files
        })
        
        content = response.content
        if isinstance(content, list):
            content = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
        
        # Clean up potential markdown formatting from the response
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        try:
            # strict=False allows literal \n and \t in strings (fixing the Invalid control character error)
            from backend.utils.json_parser import parse_json_robustly
            devops_files = parse_json_robustly(content)
            
            current_files = state.get("code_files", {})
            infra_files = devops_files.get("files", [])
            
            for file_obj in infra_files:
                path = file_obj.get("path")
                file_content = file_obj.get("content")
                if path and file_content:
                    print(f"   -> [DevOps] Generated infrastructure file: {path}")
                    current_files[path] = file_content
            state["code_files"] = current_files
            
            # Phase 1: Persistent Project Memory (Log to Neo4j)
            try:
                from backend.memory.neo4j_client import Neo4jClient
                client = Neo4jClient()
                rationale = f"Configured containerized deployment with: {', '.join(devops_files.keys())}"
                client.log_decision(state['project_id'], "DevOps", rationale)
                client.close()
                print("   -> [Memory] Deployment decision saved to Neo4j.")
            except Exception as e:
                print(f"   -> [WARNING] Could not save DevOps decision to memory: {e}")

            print("   -> [DevOps] Successfully generated deployment infrastructure.")
            
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                q.put({"type": "timeline", "title": "DevOps Phase Complete", "reason": "Deployment infrastructure ready", "status": "done"})
                
            return state
        except Exception as e:
            print(f"   -> [DevOps] Error generating deployment files: {e}")
            if q:
                q.put({"type": "timeline_update", "status": "done"})
            return state
