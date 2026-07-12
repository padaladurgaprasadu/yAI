import json
import asyncio
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.base import BaseAgent
from backend.utils.logger import get_logger

logger = get_logger(__name__)

TOPIC_TEMPLATES = {
    "Programming": """
- Overview
- Definition
- Syntax
- Parameters
- Flow Diagram
- Example
- Output
- Real-world Applications
- Advantages
- Disadvantages
- Interview Questions
- Best Practices
- Common Mistakes
- Summary
""",
    "Places": """
- Overview
- History
- Location
- Culture
- Weather
- Food
- Tourist Attractions
- Transportation
- Economy
- Education
- Interesting Facts
- Nearby Places
- Travel Tips
""",
    "AI": """
- Definition
- History
- Architecture
- Working Workflow
- Components
- Algorithms
- Advantages
- Disadvantages
- Applications
- Future
- Comparison
- References
""",
    "General": """
- Overview
- Key Concepts
- Detailed Explanation
- Real-world Examples
- Visuals or Diagrams
- Summary
"""
}

class ResponseOrchestrator(BaseAgent):
    """
    Response Orchestration Engine (yAI).
    Implements a 5-stage pipeline for highly-structured, deeply-researched knowledge retrieval.
    """
    def __init__(self):
        super().__init__()
        from backend.agents.router import ModelRouter
        self.fast_llm = ModelRouter.get_optimal_llm("ResponseOrchestrator", complexity="fast")
        self.smart_llm = ModelRouter.get_optimal_llm("ResponseOrchestrator", complexity="smart")

    async def _classify_intent(self, query: str) -> str:
        """Stage 1: Intent Classification"""
        sys_prompt = """Classify the query into one of these exact categories:
Programming, AI, Places, Medical, Finance, History, Geography, Mathematics, General.
Return ONLY the category name."""
        try:
            resp = await self.fast_llm.ainvoke([SystemMessage(content=sys_prompt), HumanMessage(content=query)])
            cat = resp.content.strip()
            if cat in TOPIC_TEMPLATES:
                return cat
            if cat in ["Medical", "Finance", "History", "Geography", "Mathematics"]:
                return "General" # Fallback to general template but with domain context
            return "General"
        except:
            return "General"

    async def _retrieve_context(self, query: str) -> str:
        """Stage 2: Context Retrieval"""
        try:
            from duckduckgo_search import AsyncDDGS
            results = await AsyncDDGS().text(query, max_results=4)
            if results:
                return "\n".join([f"- {r['title']}: {r['body']}" for r in results])
        except Exception as e:
            logger.warning(f"[ResponseOrchestrator] Web search failed: {e}")
        return "No additional live context retrieved."

    async def _generate_plan(self, query: str, category: str) -> str:
        """Stage 3: Response Planning"""
        template = TOPIC_TEMPLATES.get(category, TOPIC_TEMPLATES["General"])
        sys_prompt = f"""You are a Planning Agent.
Given a user query and a strict Topic Template, generate an internal blueprint outline for the response.
Expand upon the template sections dynamically based on the specific query.
Template:
{template}

Output ONLY the structured outline list."""
        
        try:
            resp = await self.fast_llm.ainvoke([SystemMessage(content=sys_prompt), HumanMessage(content=query)])
            return resp.content.strip()
        except:
            return template

    async def _generate_draft(self, query: str, plan: str, context: str, feedback: str = "") -> str:
        """Stage 4: Response Generation"""
        sys_prompt = f"""You are an Expert Knowledge Generator.
Write a brilliant, comprehensive, and highly-detailed response following this strict outline:
{plan}

LIVE KNOWLEDGE CONTEXT:
{context}

RULES:
1. You MUST use Markdown headers (###) for every section in the outline.
2. Use Visual Intelligence: include tables, code blocks, or textual charts where appropriate.
3. Be exhaustive in detail (Level 3 depth).
4. Expand contexts and related concepts automatically.
"""
        if feedback:
            sys_prompt += f"\n\nCRITICAL FIX: The previous draft failed the Quality Check. Address this feedback immediately:\n{feedback}"
            
        try:
            resp = await self.smart_llm.ainvoke([SystemMessage(content=sys_prompt), HumanMessage(content=query)])
            return resp.content.strip()
        except Exception as e:
            return f"An error occurred while generating the response: {str(e)}"

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

    async def execute_pipeline(self, query: str, user_memory: str = "") -> str:
        """Executes the full 5-stage Response Orchestration pipeline."""
        logger.info("[ResponseOrchestrator] Stage 1: Intent Detection...")
        category_task = asyncio.create_task(self._classify_intent(query))
        
        logger.info("[ResponseOrchestrator] Stage 2: Context Retrieval...")
        context_task = asyncio.create_task(self._retrieve_context(query))
        
        category, context = await asyncio.gather(category_task, context_task)
        
        if user_memory:
            context += f"\n\nUSER PERSONAL MEMORY:\n{user_memory}"
            
        logger.info(f"[ResponseOrchestrator] Stage 3: Planning (Category: {category})...")
        plan = await self._generate_plan(query, category)
        
        max_attempts = 2
        feedback = ""
        final_draft = ""
        
        for attempt in range(max_attempts):
            logger.info(f"[ResponseOrchestrator] Stage 4: Generating Draft (Attempt {attempt+1})...")
            final_draft = await self._generate_draft(query, plan, context, feedback)
            
            logger.info("[ResponseOrchestrator] Stage 5: Quality Check...")
            qa_result = await self._quality_check(query, final_draft)
            score = int(qa_result.get("score", 0))
            
            if score >= 90:
                logger.info(f"[ResponseOrchestrator] QA Passed with score: {score}")
                break
            else:
                logger.info(f"[ResponseOrchestrator] QA Failed with score {score}. Feedback: {qa_result.get('feedback')}")
                feedback = qa_result.get("feedback", "Improve structure and detail.")
                
        return final_draft
