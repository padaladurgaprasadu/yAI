import json
from typing import Dict, Any
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
from backend.utils.cache import llm_cache
from duckduckgo_search import DDGS

class ImageSearchAgent(BaseAgent):
    """
    Image Search Service
    Uses an external index (DuckDuckGo or internal DB) to fetch relevant images 
    for visual retrieval queries.
    """
    def __init__(self):
        super().__init__()

    @llm_cache("image_search")
    def run(self, state: AiONState) -> AiONState:
        # Check if the router requested visual retrieval
        router_data = {}
        # In a real scenario, the router stores the detected intent in state.
        # But we don't have a direct 'router_intent' field. We can parse goal or use a visual_query field.
        # For now, let's look for a visual_query if it exists.
        visual_query = state.get("goal", "")
        project_id = state.get("project_id", "")
        
        try:
            from backend.api_real import stream_queues
            q = stream_queues.get(project_id)
        except ImportError:
            q = None

        if q:
            q.put({"type": "timeline", "title": "Visual Retrieval Engine", "reason": f"Searching image index for '{visual_query}'", "status": "active"})

        print(f"[ImageSearchAgent] Fetching images for: {visual_query}")
        
        images = []
        try:
            with DDGS() as ddgs:
                # Get top 5 images
                results = list(ddgs.images(
                    visual_query,
                    max_results=5,
                ))
                
                for r in results:
                    images.append(r.get("image"))
        except Exception as e:
            print(f"   -> [ImageSearchAgent] Error fetching images: {e}")

        if images:
            # Update the state image field so it can be streamed or used downstream
            existing_images = state.get("image") or []
            state["image"] = existing_images + images
            state["visual_context"] = f"Retrieved Visuals: {', '.join(images)}"
            
            # Stream directly to UI
            if q:
                q.put({
                    "type": "images",
                    "urls": images
                })

        if q:
            q.put({"type": "timeline_update", "status": "done"})

        return state
