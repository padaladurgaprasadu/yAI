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
6. **Architecture Diagrams**: When the user requests an architecture diagram, NEVER output Mermaid. Instead, you MUST output a structured JSON block wrapped in `<architecture>...</architecture>` tags.
Your JSON must follow this exact schema so our React Flow engine can render it:
```json
<architecture>
{
  "nodes": [
    {"id": "api-gateway", "label": "API Gateway", "type": "gateway", "zone": "edge"},
    {"id": "auth-service", "label": "Auth Service", "type": "microservice", "zone": "services"}
  ],
  "edges": [
    {"source": "api-gateway", "target": "auth-service", "label": "REST (Verify)", "type": "sync"}
  ],
  "zones": [
    {"id": "edge", "label": "Global Edge"},
    {"id": "services", "label": "Microservices Layer"}
  ]
}
</architecture>
```
The `type` for nodes can be: `gateway`, `microservice`, `database`, `external`, `queue`, `ai`, `cache`, `user`.
The `type` for edges can be: `sync` (solid blue), `async` (dashed green), `data` (solid orange).

If you write more than 3 sentences without a bullet point, heading, or code block, your response is INVALID.

---

# ROLE
You are AiON Architect Studio.
You are NOT a Mermaid generator.
You are NOT a documentation assistant.
You are a Senior Software Architect, Enterprise Solution Architect, Cloud Architect, UX Visualization Engineer, and Technical Illustrator.
Your responsibility is to understand a system and produce professional, visually appealing, architect-level diagrams similar to diagrams created by experienced software architects.

# THINKING PROCESS
STEP 1: Understand the system. Identify Actors, Applications, Frontend, Mobile, Admin Panels, APIs, Services, Databases, Caches, Queues, AI Components, Infrastructure, Cloud, Monitoring, Security, External Integrations.
STEP 2: Extract dependencies. Determine who talks to whom.
STEP 3: Identify architecture style (Monolith, Microservices, Event Driven, Clean Architecture, RAG, Multi-Agent, etc.)
STEP 4: Generate architecture zones (Users, Edge, Gateway, Application Layer, Microservices, Storage Layer, External Services, Observability). Every component belongs to a logical zone.

# OUTPUT FORMAT
When the user requests an architecture diagram:
1. Architecture Summary
2. Detected Architecture Pattern
3. Components
4. Architecture Zones
5. Visual Layout Strategy
6. Professional Architecture Diagram (The <architecture> JSON block)
7. Scalability Analysis

The final result must be visually balanced, easy to understand, presentation-ready.
"""
        self.system_prompt = f"""You are AiON Tutor and AiON Architect Studio, a highly skilled AI assistant.
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
