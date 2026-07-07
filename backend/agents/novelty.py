import json
from typing import Dict, Any
from backend.agents.base import BaseAgent, GLOBAL_AGENT_RULES
from backend.orchestrator.state import AiONState
from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.orchestration_prompts import NOVELTY_AGENT_PROMPT
NOVELTY_SYSTEM_PROMPT = GLOBAL_AGENT_RULES + "\\n\\n" + NOVELTY_AGENT_PROMPT

class NoveltyAgent(BaseAgent):
    def __init__(self):
        super().__init__()

    def run(self, state: AiONState) -> AiONState:
        goal = state.get("goal", "")
        project_id = state.get("project_id")
        research_synthesis = state.get("research_synthesis", {})
        
        try:
            from backend.api_real import stream_queues
            q = stream_queues.get(project_id)
        except ImportError:
            q = None
            
        if q:
            q.put({"type": "agent_state", "agent": "novelty_agent"})
            q.put({"type": "timeline", "title": "Novelty Agent", "reason": "Verifying existing approaches before recommending new ideas", "status": "active"})
            
        print(f"[NoveltyAgent] Analyzing novelty for: {goal}")
        
        prompt_content = f"Original Goal:\n{goal}\n\n"
        if research_synthesis:
            prompt_content += f"Research Synthesis:\n{json.dumps(research_synthesis, indent=2)}\n\n"
            
        prompt_content += "Based on this research, evaluate existing approaches and propose your novel recommendation according to the mandatory order of operations and output schema."
        
        messages = [
            SystemMessage(content=NOVELTY_SYSTEM_PROMPT),
            HumanMessage(content=prompt_content)
        ]
        
        try:
            res = self.llm.invoke(messages)
            content = res.content
            
            # Parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1]
            
            novelty_data = json.loads(content.strip())
            
            # Store in state
            state["novelty_recommendation"] = novelty_data
            
            # Add to semantic context
            existing_context = state.get("semantic_context", "")
            recommendation = novelty_data.get("recommendation", {})
            idea = recommendation.get("idea", "")
            
            new_context = existing_context + "\n\n=== NOVELTY RECOMMENDATION ===\n" + idea
            state["semantic_context"] = new_context
            
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                
        except Exception as e:
            print(f"   -> [NoveltyAgent] Error generating novelty recommendation: {e}")
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                
        return state
