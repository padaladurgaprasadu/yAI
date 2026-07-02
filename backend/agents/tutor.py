from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from backend.agents.base import BaseAgent

class TutorAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.formatting_rule = """
🔴 **CRITICAL FORMATTING RULE - YOU MUST FOLLOW THIS EXACTLY:**

NEVER respond in a single continuous paragraph.

ALWAYS structure your response using these elements:
1. **Bold headings** for each section (e.g., **Concept**, **Syntax**, **Example**).
2. **Bullet points** (`- `) for listing items.
3. **Numbered lists** (`1. `, `2. `) for step-by-step instructions.
4. **Code blocks** (```...```) for ANY code.
5. **Blank lines** between sections for readability.
6. **Mermaid Diagrams**: When asked for architecture, you MUST use Advanced Visuals. ALWAYS start your Mermaid blocks exactly with:
```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#111827', 'primaryTextColor': '#e5e7eb', 'primaryBorderColor': '#374151', 'lineColor': '#8b5cf6', 'secondaryColor': '#1f2937', 'tertiaryColor': '#111827'} } }%%
graph TD
    classDef default fill:#1f2937,stroke:#374151,stroke-width:2px,color:#e5e7eb;
    classDef gateway fill:#4c1d95,stroke:#8b5cf6,stroke-width:2px,color:#fff;
    classDef microservice fill:#065f46,stroke:#10b981,stroke-width:2px,color:#fff;
    classDef database fill:#991b1b,stroke:#ef4444,stroke-width:2px,color:#fff;
    classDef external fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#fff;
```
Then build your graph and apply these classes (e.g., `API[API Gateway]:::gateway`, `UserDB[(Database)]:::database`). Use standard flowchart syntax (never `participant`).

If you write more than 3 sentences without a bullet point, heading, or code block, your response is INVALID.
"""
        self.system_prompt = f"""You are AiON Tutor, a highly skilled AI assistant that explains code, architecture, and concepts clearly to the user.
{self.formatting_rule}
"""

    def respond(self, chat_history: list, latest_query: str) -> str:
        """
        Takes a list of previous messages (chronological order) and the latest query.
        Injects the formatting rule into the latest query to prevent context drift.
        """
        messages = [SystemMessage(content=self.system_prompt)]
        
        # Append chronological chat history
        for msg in chat_history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            else:
                messages.append(AIMessage(content=msg.get("content", "")))
                
        # 🟢 CRITICAL: Inject the formatting rule into EVERY user message at the very end
        # This guarantees it is in the active context window, overriding any bad habits learned in chat history.
        injected_query = f"""{latest_query}

---
Remember: Your response MUST use headings, bullet points, numbered lists, and code blocks. 
NEVER write a single paragraph. You MUST retain this structured format.
"""
        messages.append(HumanMessage(content=injected_query))
        
        # Step 1: Get raw response
        try:
            response = self.invoke_with_retry(self.llm, messages)
            raw_response = response.content
            if isinstance(raw_response, list):
                raw_response = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in raw_response)
        except Exception as e:
            return f"**Error**: Could not connect to AI service. Details: {str(e)}"
            
        # Step 2: "Formatting Police" - If the response is a single paragraph, force reformat
        if len(raw_response.split('\n')) < 3 and len(raw_response) > 150:
            print("🔧 [Tutor] Reformatting detected paragraph...")
            
            reformat_prompt = f"""
Take this text and reformat it exactly according to the following rules:
- Headings (bold)
- Bullet points
- Numbered lists
- Code blocks

Do not change the meaning of the text, just the formatting.

Original text:
{raw_response}
"""
            try:
                formatted_response = self.invoke_with_retry(self.llm, [HumanMessage(content=reformat_prompt)])
                return formatted_response.content
            except Exception:
                return raw_response
                
        return raw_response
