import json
import base64
import io
import urllib.request
import urllib.parse
from typing import List, Dict, Any
from backend.agents.base import BaseAgent, GLOBAL_AGENT_RULES
from backend.orchestrator.state import AiONState
from langchain_core.messages import HumanMessage, SystemMessage
from backend.utils.cache import llm_cache

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import docx
except ImportError:
    docx = None

RESEARCH_SYSTEM_PROMPT = f"""
{GLOBAL_AGENT_RULES}

ROLE: Research Assistant Agent
GOAL: Take a research question (with or without uploaded source material) and produce an
expert-level synthesis — grounded in actual sources, not fabricated, with diagrams where they
aid understanding.

CAPABILITIES REQUIRED:
1. FILE INGESTION: Read extracted content and cross-reference multiple uploaded files.
2. EXTERNAL RESEARCH: Synthesize current information.
3. DEEP THINKING MODE: Decompose the question and look for disconfirming evidence.
4. DIAGRAM GENERATION: Use mermaid syntax if a diagram aids understanding.
5. EXPERT-LEVEL SYNTHESIS: Be precise and honest about uncertainty.
6. NOVEL RECOMMENDATION: If a novel approach is requested, flag novelty_requested: true so the Novelty Agent can run next.

OUTPUT SCHEMA:
{{
  "question_decomposition": {{"actual_question": "", "sub_questions": [""]}},
  "sources_used": [{{"type": "uploaded_file" | "web", "identifier": "", "role_in_answer": ""}}],
  "synthesis": "the expert answer, in prose",
  "diagrams": [{{"type": "flowchart|sequence|architecture|tree|table", "purpose": "", "content": ""}}],
  "confidence_map": [{{"claim": "", "confidence": "high|medium|low", "basis": ""}}],
  "disagreement_or_uncertainty": ["areas where genuine expert disagreement or evidence gaps exist"],
  "novelty_requested": true,
  "trend_checked": true
}}
"""

class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__()

    def _parse_files(self, files: List[Dict[str, str]]) -> str:
        """Parses files which are expected to have 'name' and 'content' (base64 string)."""
        parsed_text = ""
        for f in files:
            name = f.get("name", "unknown_file")
            b64_content = f.get("content", "")
            if not b64_content:
                continue
            
            try:
                # Strip data URI prefix if present
                if "," in b64_content:
                    b64_content = b64_content.split(",")[1]
                
                file_bytes = base64.b64decode(b64_content)
                parsed_text += f"\n--- CONTENT OF {name} ---\n"
                
                if name.lower().endswith(".pdf") and PyPDF2:
                    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                    for page in reader.pages:
                        parsed_text += page.extract_text() + "\n"
                elif name.lower().endswith(".docx") and docx:
                    doc = docx.Document(io.BytesIO(file_bytes))
                    for para in doc.paragraphs:
                        parsed_text += para.text + "\n"
                elif name.lower().endswith((".png", ".jpg", ".jpeg")):
                    parsed_text += "[Image File Uploaded. Ensure description or OCR is provided if text is needed.]\n"
                else:
                    # Fallback to standard utf-8 decoding for text/csv files
                    parsed_text += file_bytes.decode("utf-8", errors="ignore")
                    
            except Exception as e:
                parsed_text += f"[Failed to parse {name}: {str(e)}]\n"
                
        return parsed_text

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
    @llm_cache("researcher")
    def run(self, state: AiONState) -> AiONState:
        goal = state.get("goal", "")
        project_id = state.get("project_id")
        uploaded_files = state.get("uploaded_files", [])
        
        try:
            from backend.api_real import stream_queues
            q = stream_queues.get(project_id)
        except ImportError:
            q = None
            
        if q:
            q.put({"type": "agent_state", "agent": "researcher"})
            q.put({"type": "timeline", "title": "Researching...", "reason": "Gathering context & parsing files", "status": "active"})
            
        print(f"[ResearchAgent] Parsing context for: {goal}")
        
        # Parse uploaded files
        file_context = ""
        if uploaded_files:
            file_context = self._parse_files(uploaded_files)
        
        # Quick knowledge graph search to complement
        web_context = ""
        try:
            # We'll just search the main goal topic or first few words
            search_query = " ".join(goal.split()[:4])
            web_context = self._fetch_wikipedia_summary(search_query)
        except Exception:
            pass
            
        # Formulate request
        prompt_content = f"Goal/Question:\n{goal}\n\n"
        if file_context:
            prompt_content += f"Uploaded Document Context:\n{file_context}\n\n"
        if web_context:
            prompt_content += f"Web Context:\n{web_context}\n\n"
            
        prompt_content += "Provide your expert synthesis matching the JSON output schema exactly."
        
        messages = [
            SystemMessage(content=RESEARCH_SYSTEM_PROMPT),
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
            
            research_data = json.loads(content.strip())
            
            # Store in state
            state["research_synthesis"] = research_data
            
            # Add to semantic context for downstream agents
            existing_context = state.get("semantic_context", "")
            syn = research_data.get("synthesis", "")
            new_context = existing_context + "\n\n=== RESEARCH SYNTHESIS ===\n" + syn
            state["semantic_context"] = new_context
            
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                
        except Exception as e:
            print(f"   -> [ResearchAgent] Error generating synthesis: {e}")
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                
        return state
