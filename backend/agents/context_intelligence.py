import json
import asyncio
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent

class ContextIntelligenceEngine(BaseAgent):
    """
    General Chat Context Intelligence Engine.
    Implements 8 levels of context parsing and fusion.
    """
    def __init__(self):
        super().__init__()
        from backend.agents.router import ModelRouter
        # Use a fast model for pre-flight context extraction
        self.fast_llm = ModelRouter.get_optimal_llm("ContextIntelligence", complexity="fast")

    async def _fetch_web_context(self, query: str) -> str:
        """Level 5: Fetch fresh dynamic knowledge."""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
                if results:
                    return json.dumps(results)
        except Exception as e:
            print(f"[ContextIntelligence] Web search failed: {e}")
        return ""

    async def build_context(self, message: str, history: list, intent_data: dict, memory_context: str) -> dict:
        """
        Builds the 8-level Knowledge Context Block.
        """
        # Level 1: Intent & Entity
        primary_intent = intent_data.get("primary_intent", "General Chat")
        requires_web_search = intent_data.get("requires_web_search", False)
        entity_detection = intent_data.get("entity_detection", {})
        search_query = entity_detection.get("search_query", "")
        
        # Level 5: Knowledge Context (Web Search if needed)
        live_data = ""
        if requires_web_search and search_query:
            print(f"[ContextIntelligence] Live Data requested for: {search_query}")
            live_data = await asyncio.to_thread(self._fetch_web_context_sync, search_query)

        # Level 2 & 3: Conversation & Session Compression
        # We simulate a rolling summary by analyzing history if it's long
        session_summary = ""
        if len(history) > 6:
            session_summary = "Long conversation detected. Extracting core topic."

        # Level 7: Emotional Context
        # Set tone based on complexity
        tone = "Professional, helpful, and concise."
        if intent_data.get("complexity") == "Simple":
            tone = "Friendly and direct."
        elif intent_data.get("complexity") == "Large":
            tone = "Deeply technical, analytical, and structured."

        # Knowledge Fusion
        fused_context = {
            "intent": primary_intent,
            "domain": intent_data.get("domain", "General"),
            "memory": memory_context,
            "live_data": live_data,
            "tone": tone
        }
        
        return fused_context
        
    def _fetch_web_context_sync(self, query: str) -> str:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
                if results:
                    formatted = []
                    for r in results:
                        formatted.append(f"Title: {r.get('title')}\nSnippet: {r.get('body')}")
                    return "\n".join(formatted)
        except Exception as e:
            print(f"[ContextIntelligence] Web search sync failed: {e}")
        return ""

    def generate_system_prompt(self, fused_context: dict) -> str:
        """
        Level 8: Generates the Response Planner Prompt for the Streaming LLM.
        """
        prompt = f"""You are yAI, a deeply context-aware Personal AI Operating System.
You are NOT a simple chatbot. You are an expert system.

=== CONTEXT INTELLIGENCE BLOCK ===
- **Domain**: {fused_context.get('domain')}
- **Detected Intent**: {fused_context.get('intent')}
- **Tone/Style Guidelines**: {fused_context.get('tone')}

=== LONG-TERM MEMORY ===
{fused_context.get('memory', 'No past memory recorded.')}

=== LIVE WEB DATA (If available) ===
{fused_context.get('live_data', 'No live data fetched.')}
===================================

[RESPONSE PLANNING RULES]:
1. **Understand Follow-ups:** Use the conversation history to understand pronouns and context.
2. **Knowledge Fusion:** If Live Web Data is provided, seamlessly integrate it into your answer to provide up-to-date facts.
3. **Rich Formatting:** You MUST use Markdown. Use H3 (###) headers, bold text, bullet points, and short paragraphs.
4. **Visuals:** If explaining a complex process or architecture, use Tables or Step-by-Step guides. 
5. **Memory Update:** If the user explicitly shares a new personal fact about themselves, secretly append `[MEMORY_ADD] <fact>` at the very end of your response.
"""
        return prompt
