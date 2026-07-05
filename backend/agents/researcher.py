import json
import urllib.request
import urllib.parse
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
from langchain_core.prompts import ChatPromptTemplate

class ResearchAgent(BaseAgent):
    """
    The Research Agent (Innovation Engine) is responsible for analyzing the user's goal,
    researching existing methodologies via real-time web lookups (Wikipedia/Knowledge Graphs),
    and synthesizing a NOVEL APPROACH before the Architect designs the system.
    """
    def __init__(self):
        super().__init__()
        
        # We use the LLM to parse the goal and formulate search queries
        self.query_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an elite Research Planner. Determine the TOP 2 key concepts or methodologies that need to be researched for the user's project. Output EXACTLY a JSON list of 2 strings. Example: [\"Video streaming architectures\", \"WebRTC latency optimization\"]"),
            ("human", "Goal: {goal}")
        ])
        self.query_chain = self.query_prompt | self.llm
        
        # We use the LLM to synthesize the final Innovation Brief
        self.innovation_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an elite Tech Innovator and Systems Architect. Given the user's goal and the gathered background research on existing methodologies, you MUST formulate a NOVEL APPROACH. Your job is to rethink the standard way of doing things and propose an advanced, creative, or highly optimized architecture/idea. Output a structured briefing starting with '### Existing Methodologies' and ending with '### AiON Novel Approach'."),
            ("human", "Goal: {goal}\n\nGathered Research on existing methods:\n{research}\n\nPropose the novel approach!")
        ])
        self.innovation_chain = self.innovation_prompt | self.llm

    def _fetch_wikipedia_summary(self, query: str) -> str:
        try:
            url = f'https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&titles={urllib.parse.quote(query)}&format=json'
            req = urllib.request.Request(url, headers={'User-Agent': 'AiON/1.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                pages = data.get('query', {}).get('pages', {})
                for page_id in pages:
                    if page_id != "-1":
                        return pages[page_id].get('extract', '')
        except Exception:
            pass
        return ""
        
    def _search_wikipedia_list(self, query: str) -> str:
        try:
            url = f'https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json'
            req = urllib.request.Request(url, headers={'User-Agent': 'AiON/1.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                results = data.get('query', {}).get('search', [])
                if results:
                    return self._fetch_wikipedia_summary(results[0]['title'])
        except Exception:
            pass
        return ""

    def run(self, state: AiONState) -> AiONState:
        goal = state.get("goal", "")
        project_id = state.get("project_id")
        
        # Push UI updates if running in API loop
        try:
            from backend.api_real import stream_queues
            q = stream_queues.get(project_id)
        except ImportError:
            q = None
            
        if q:
            q.put({"type": "agent_state", "agent": "researcher"})
            q.put({"type": "timeline", "title": "Researching Methodologies...", "reason": "Querying knowledge graphs", "status": "active"})
            
        print(f"[ResearchAgent] Planning research strategy for: {goal}")
        
        try:
            # 1. Ask LLM for the best search concepts
            response = self.query_chain.invoke({"goal": goal})
            content = response.content.replace("```json", "").replace("```", "").strip()
            queries = json.loads(content)
            if not isinstance(queries, list):
                queries = [goal]
        except Exception as e:
            print(f"   -> [ResearchAgent] Error generating queries: {e}. Falling back.")
            queries = [goal]
            
        gathered_context = ""
        
        # 2. Execute Web Search via Wikipedia Knowledge Graph
        for query in queries[:2]:
            print(f"   -> [ResearchAgent] Searching knowledge graph: '{query}'...")
            summary = self._search_wikipedia_list(query)
            if summary:
                gathered_context += f"Topic: {query}\nMethodology Context: {summary[:500]}...\n\n"
                
        if not gathered_context:
            gathered_context = "No direct knowledge graph entries found. Assume standard industry practices."
            
        if q:
            q.put({"type": "timeline", "title": "Synthesizing Novel Approach", "reason": "Analyzing existing methods", "status": "active"})

        # 3. Synthesize the Innovation Brief
        print("   -> [ResearchAgent] Synthesizing Novel Approach...")
        try:
            innovation_res = self.innovation_chain.invoke({
                "goal": goal,
                "research": gathered_context
            })
            innovation_brief = innovation_res.content
            
            # 4. Append to semantic context so the Architect and Coder can read it
            existing_context = state.get("semantic_context", "")
            new_context = existing_context + "\n\n=== RESEARCH & INNOVATION BRIEF ===\n" + innovation_brief
            state["semantic_context"] = new_context
            
            print("   -> [ResearchAgent] Innovation Brief successfully generated.")
            
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                
        except Exception as e:
            print(f"   -> [ResearchAgent] Error synthesizing approach: {e}")
            if q:
                q.put({"type": "timeline_update", "status": "done"})

        return state
