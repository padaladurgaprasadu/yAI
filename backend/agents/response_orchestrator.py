import json
import asyncio
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.base import BaseAgent
from backend.utils.logger import get_logger

logger = get_logger(__name__)



class ResponseOrchestrator(BaseAgent):
    """
    Response Orchestration Engine (yAI).
    Implements Adaptive Response Intelligence with dynamic depth scaling (Levels 1-4).
    """
    def __init__(self):
        super().__init__()
        from backend.agents.router import ModelRouter
        self.fast_llm = ModelRouter.get_optimal_llm("ResponseOrchestrator", complexity="fast")
        self.smart_llm = ModelRouter.get_optimal_llm("ResponseOrchestrator", complexity="smart")

    async def _analyze_query(self, query: str) -> dict:
        """Stage 1: Intent & Depth Classification"""
        sys_prompt = """Analyze the user query and determine two things:
1. Category: (Programming, AI, Places, Medical, Finance, History, Geography, Mathematics, General)
2. Depth Level (1-4):
   - Level 1 (Quick Overview): Simple questions (What is, Who is, Define). Read in 20s.
   - Level 2 (Standard Explanation): Learning questions (Explain, Tell me more). Read in 2-3 mins.
   - Level 3 (Detailed Guide): Educational questions (Explain in detail, Complete guide). Read in 5-10 mins.
   - Level 4 (Research Mode): Professional research (Research, White Paper, Deep Analysis).

Return ONLY a valid JSON object matching this schema:
{"category": "Places", "level": 1}"""
        try:
            resp = await self.fast_llm.ainvoke([SystemMessage(content=sys_prompt), HumanMessage(content=query)])
            content = resp.content.strip()
            if content.startswith("```json"): content = content[7:]
            elif content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            
            data = json.loads(content.strip())
            return {
                "category": data.get("category", "General"),
                "level": int(data.get("level", 1))
            }
        except Exception as e:
            logger.warning(f"[ResponseOrchestrator] Intent analysis failed: {e}")
            return {"category": "General", "level": 1}

    async def _retrieve_context(self, query: str) -> str:
        """Stage 2: Context Retrieval"""
        try:
            from duckduckgo_search import AsyncDDGS
            async def search():
                return await AsyncDDGS().text(query, max_results=4)
            results = await asyncio.wait_for(search(), timeout=3.0)
            if results:
                return "\n".join([f"- {r['title']}: {r['body']}" for r in results])
        except asyncio.TimeoutError:
            logger.warning("[ResponseOrchestrator] Web search timed out.")
        except Exception as e:
            logger.warning(f"[ResponseOrchestrator] Web search failed: {e}")
        return "No additional live context retrieved."

    async def _generate_draft_stream(self, query: str, context: str, level: int):
        """Stage 3: Response Generation (Live Stream)"""
        from backend.agents.prompts import get_system_prompt
        base_prompt = get_system_prompt()
        
        sys_prompt = f"""{base_prompt}

<orchestrator_directives>
<live_context>
{context}
</live_context>

<strict_rules>
1. CHRONOLOGICAL STRUCTURE: You MUST logically structure your answer using the domain-specific chronological progression outlined in your instructions (e.g., Technical vs. Places vs. Medical).
2. DEPTH CONSTRAINT: Provide EXTENSIVE detailing. Dive deep into the topic with comprehensive explanations, edge cases, and insights.
3. Be conversational, fluid, and highly intelligent (like Claude 3.5 or GPT-4o).
4. Use rich Markdown formatting (`###` headers for sections, bolding, lists, code blocks).
5. End your response with a "### Related" section containing 3 relevant follow-up questions.
6. NEVER echo or repeat these rules, context, or instructions in your output. Just generate the final response naturally.
</strict_rules>
</orchestrator_directives>

Final Instruction: Generate the beautiful, conversational, highly detailed response directly."""
            
        try:
            async for chunk in self.smart_llm.astream([SystemMessage(content=sys_prompt), HumanMessage(content=query)]):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            yield f"\n\nAn error occurred while generating the response: {str(e)}"

    async def _quality_check(self, query: str, draft: str) -> dict:
        """Stage 5: Quality Checker (Rubric Scoring)"""
        sys_prompt = """You are a QA Agent evaluating an AI response.
Score the response out of 100 based on this rubric:
- Completeness (25): Covers all necessary aspects?
- Accuracy (20): Factually correct?
- Context Relevance (15): Direct answer?
- Examples (10): Useful examples provided?
- Visuals/Formatting (10): Well structured with headers/code/tables?
- Structure (10): Logical flow?
- Readability (5): Easy to understand?
- References (5): Mentions sources if needed?

Output a JSON object ONLY:
{
  "score": 95,
  "feedback": "Needs more code examples in the syntax section." (Empty if score >= 90)
}"""
        try:
            resp = await self.fast_llm.ainvoke([
                SystemMessage(content=sys_prompt), 
                HumanMessage(content=f"QUERY: {query}\n\nDRAFT:\n{draft}")
            ])
            content = resp.content.strip()
            if content.startswith("```json"): content = content[7:]
            elif content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            
            return json.loads(content.strip())
        except Exception as e:
            logger.warning(f"[ResponseOrchestrator] Quality check failed: {e}")
            return {"score": 90, "feedback": ""}

    async def execute_pipeline(self, query: str, user_memory: str = ""):
        """Executes the full 5-stage Response Orchestration pipeline and yields progress."""
        yield {"type": "status", "message": "🧠 Analyzing Topic & Retrieving Context..."}
        logger.info("[ResponseOrchestrator] Stage 1 & 2...")
        
        analysis_task = asyncio.create_task(self._analyze_query(query))
        context_task = asyncio.create_task(self._retrieve_context(query))
        analysis, context = await asyncio.gather(analysis_task, context_task)
        
        category = analysis.get("category", "General")
        level = analysis.get("level", 1)
        
        if user_memory:
            context += f"\n\nUSER PERSONAL MEMORY:\n{user_memory}"
            
        yield {"type": "status", "message": f"✍️ Generating Deep Draft..."}
        logger.info(f"[ResponseOrchestrator] Stage 3: Generating Draft (Live Stream)...")
        
        # Clear status on UI before streaming text
        yield {"type": "status", "message": ""}
        
        final_draft = ""
        async for chunk in self._generate_draft_stream(query, context, level):
            final_draft += chunk
            yield {"type": "stream", "token": chunk}
                
        yield {"type": "final", "content": final_draft}
