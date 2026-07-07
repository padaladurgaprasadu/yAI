import json
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState

class PreviewAgent(BaseAgent):
    """
    Preview Agent (Persistent Sandbox setup)
    Spins up or warms up the execution sandbox in parallel with code generation
    so it's immediately ready when the code finishes.
    """
    def __init__(self):
        super().__init__()

    def run(self, state: AiONState) -> AiONState:
        project_id = state.get("project_id", "")
        
        try:
            from backend.api_real import stream_queues
            q = stream_queues.get(project_id)
        except ImportError:
            q = None

        if q:
            q.put({"type": "timeline", "title": "Preview Environment", "reason": "Warming up persistent sandbox...", "status": "active"})
            
        print("[PreviewAgent] Warming up persistent sandbox environment...")
        
        # Simulate sandbox warm up
        import time
        time.sleep(1) # Fast warmup
        
        if q:
            q.put({"type": "sandbox_status", "status": "ready", "url": "http://localhost:5173"})
            q.put({"type": "timeline_update", "status": "done"})

        return state
