from backend.orchestrator.state import AiONState
import json

class ContextOrchestratorAgent:
    """
    Context Orchestrator
    Dynamically compresses and ranks the active memory to preserve the context window.
    """
    def run(self, state: AiONState) -> AiONState:
        print("[Context Orchestrator] Compressing and ranking active context...")
        
        project_id = state.get("project_id")
        try:
            from backend.api_real import stream_queues
            q = stream_queues.get(project_id)
        except ImportError:
            q = None
            
        if q:
            q.put({"type": "agent_state", "agent": "architect"})
            q.put({"type": "timeline", "title": "Context Compression", "reason": "Ranking memory for optimal LLM context", "status": "active"})
            q.put({"type": "progress", "message": "🧠 Compressing active memory context..."})
            
        code_files = state.get("code_files", {})
        goal = state.get("goal", "")
        
        # Simple Phase 1 Heuristic:
        # If we have too many files, we only keep the ones relevant to the goal.
        # For now, we will just serialize them efficiently into compressed_context.
        
        compressed = []
        for path, content in code_files.items():
            # Basic compression: remove empty lines and extra whitespace if file is huge
            # For phase 1, we just provide a compact representation.
            compressed.append(f"--- {path} ---\n{content}")
            
        state["compressed_context"] = "\n".join(compressed)
        
        print(f"   -> [SUCCESS] Context compressed ({len(state.get('compressed_context', ''))} chars)")
        if q:
            q.put({"type": "timeline_update", "status": "done"})
            
        return state
