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

from backend.agents.orchestration_prompts import RESEARCHER_PROMPT
RESEARCH_SYSTEM_PROMPT = GLOBAL_AGENT_RULES + "\n\n" + RESEARCHER_PROMPT

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
                elif name.lower().endswith(".csv"):
                    import csv
                    csv_data = file_bytes.decode("utf-8", errors="ignore")
                    reader = csv.reader(io.StringIO(csv_data))
                    for idx, row in enumerate(reader):
                        parsed_text += f"Row {idx}: {', '.join(row)}\n"
                elif name.lower().endswith((".png", ".jpg", ".jpeg")):
                    parsed_text += "[Image File Uploaded. Ensure description or OCR is provided if text is needed.]\n"
                else:
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

    def _search_web(self, query: str) -> List[Dict[str, str]]:
        """
        Performs a web search using DuckDuckGo.
        Returns a list of search results with titles, snippets, and links.
        """
        results = []
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(query, max_results=5))
                for r in ddg_results:
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "link": r.get("href", "")
                    })
        except Exception as e:
            print(f"[ResearchAgent] DDG search failed: {e}")
            wiki_summary = self._fetch_wikipedia_summary(query)
            if wiki_summary:
                results.append({
                    "title": f"Wikipedia: {query}",
                    "snippet": wiki_summary,
                    "link": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(query)}"
                })
        return results

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
        
        # Live web search with citations
        web_context = ""
        citations = []
        try:
            search_query = " ".join(goal.split()[:5])
            web_results = self._search_web(search_query)
            for idx, res in enumerate(web_results):
                cite_num = idx + 1
                web_context += f"[{cite_num}] Title: {res['title']}\nSnippet: {res['snippet']}\nSource: {res['link']}\n\n"
                citations.append(f"[{cite_num}] {res['title']} ({res['link']})")
        except Exception as e:
            print(f"   -> [ResearchAgent] Web search failed: {e}")
            
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
            from backend.utils.json_parser import parse_json_robustly
            research_data = parse_json_robustly(content)
            
            # Store in state
            state["research_synthesis"] = research_data
            
            # Add to semantic context for downstream agents
            existing_context = state.get("semantic_context", "") or ""
            syn = research_data.get("synthesis", "")
            
            # Format Citations Bibliography
            citation_block = ""
            if citations:
                citation_block = "\n\n=== CITATIONS & RANKED SOURCES ===\n" + "\n".join(citations)
                
            new_context = existing_context + "\n\n=== RESEARCH SYNTHESIS ===\n" + syn + citation_block
            state["semantic_context"] = new_context
            
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                
        except Exception as e:
            print(f"   -> [ResearchAgent] Error generating synthesis: {e}")
            if q:
                q.put({"type": "timeline_update", "status": "done"})
                
        return state
