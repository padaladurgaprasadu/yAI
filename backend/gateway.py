import json
import traceback
from backend.orchestrator.state import AiONState
from backend.utils.logger import get_logger
from backend.agents.router import OmniIntelligenceEngine

logger = get_logger(__name__)

class AIGateway:
    """
    Central AI Gateway for yAI.
    Routes requests into three distinct execution modes:
    1. Quick Chat (Lightweight, <2s)
    2. Specialist (Single Agent execution)
    3. Builder (Full Swarm Orchestration)
    """
    def __init__(self):
        self.router = OmniIntelligenceEngine()

    def run(self, initial_state: AiONState, q, project_id: str):
        """
        Executes the user request in the appropriate mode and streams progress/results to the queue.
        """
        goal = initial_state.get("goal", "")
        
        # Phase 1: Gateway Routing
        q.put({"type": "progress", "node": "gateway", "message": "🚦 AI Gateway routing request..."})
        try:
            intent_data = self.router.detect_intent(goal)
            
            # The intent_data uses the ROUTER_PROMPT schema
            router_mode = intent_data.get("mode", "chat").lower()
            complexity = intent_data.get("complexity", "fast").lower()
            
            # Additional heuristic: If the user pastes a massive spec, force builder
            goal_lower = goal.lower()
            if len(goal) > 600 or "database schema" in goal_lower or "system components" in goal_lower or "build" in goal_lower:
                router_mode = "builder"
                complexity = "smart"

            # Determine Execution Mode
            if router_mode == "builder":
                mode = "builder"
            elif router_mode == "chat" and complexity == "fast":
                mode = "quick_chat"
            else:
                mode = "specialist"
                
            q.put({"type": "progress", "node": "gateway", "message": f"⚡ Gateway selected mode: {mode.upper()}"})
            
            final_st = initial_state
            
            # Phase 2: Execution Modes
            if mode == "quick_chat":
                final_st = self._run_quick_chat(initial_state, q)
            elif mode == "specialist":
                final_st = self._run_specialist(initial_state, q, goal_lower)
            else:
                final_st = self._run_builder(initial_state, q, project_id)
                
            # Phase 3: Safety Validation Layer
            q.put({"type": "progress", "node": "gateway", "message": "🛡️ Running Safety Validation (Nemotron Content Safety)..."})
            final_st = self._run_safety_check(final_st)
            
            # Finish
            q.put({"type": "GRAPH_DONE", "state": final_st})
            
        except Exception as e:
            trace = traceback.format_exc()
            logger.error(f"[Gateway Error]: {trace}")
            q.put({"type": "error", "message": f"Gateway Error: {str(e)}"})

    def _run_quick_chat(self, state: AiONState, q) -> AiONState:
        """Mode 1: Direct LLM response for chat."""
        from backend.utils.model_registry import AIModelRegistry
        from langchain_core.prompts import ChatPromptTemplate
        
        q.put({"type": "progress", "node": "quick_chat", "message": "💬 Using Quick Chat model..."})
        
        llm = AIModelRegistry.get_llm_chain(capability="chat", temperature=0.7)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI assistant named yAI. Provide a concise, accurate response."),
            ("human", "{goal}")
        ])
        
        chain = prompt | llm
        response = chain.invoke({"goal": state.get("goal")})
        
        content = response.content
        if isinstance(content, list):
            content = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
            
        # We simulate a "code_file" so the frontend displays the chat response in the markdown viewer
        state["code_files"] = {"response.md": content}
        q.put({
            "type": "code_complete",
            "code_files": state["code_files"]
        })
        return state

    def _run_specialist(self, state: AiONState, q, goal_lower: str) -> AiONState:
        """Mode 2: Single agent execution."""
        from backend.agents.coder import CoderAgent
        from backend.agents.architect import ArchitectAgent
        
        if "architect" in goal_lower or "system" in goal_lower:
            q.put({"type": "progress", "node": "specialist", "message": "🏗️ Invoking Specialist Architect..."})
            agent = ArchitectAgent()
        else:
            q.put({"type": "progress", "node": "specialist", "message": "💻 Invoking Specialist Coder..."})
            agent = CoderAgent()
            
        state = agent.run(state)
        
        if state.get("code_files"):
            q.put({
                "type": "code_complete",
                "code_files": state["code_files"]
            })
            
        return state

    def _run_builder(self, state: AiONState, q, project_id: str) -> AiONState:
        """Mode 3: Full Swarm."""
        from backend.orchestrator.graph import build_orchestrator_graph
        graph = build_orchestrator_graph()
        thread_config = {"configurable": {"thread_id": project_id}}
        
        final_st = state
        for output in graph.stream(state, config=thread_config):
            node_name = list(output.keys())[0]
            final_st = output[node_name]
            q.put({
                "type": "progress",
                "node": node_name,
                "message": f"{node_name.capitalize()} agent completed its task..."
            })
            
            if node_name == "coder" and final_st and "code_files" in final_st:
                q.put({
                    "type": "code_complete",
                    "code_files": final_st["code_files"]
                })
                
        return final_st

    def _run_safety_check(self, state: AiONState) -> AiONState:
        """Mode 5: Safety Validation Layer."""
        from backend.utils.model_registry import AIModelRegistry
        from langchain_core.prompts import ChatPromptTemplate
        
        # In a production scenario, this checks the generated code/response for prompt injection or malicious content.
        # If it detects an issue, it would block the response. For now, it logs and allows.
        try:
            llm = AIModelRegistry.get_llm_chain(capability="safety", temperature=0.1)
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are the Nemotron Content Safety Model. Ensure the following output is safe, contains no malicious code, and does not violate safety guidelines. Respond with 'SAFE' or 'UNSAFE: [reason]'."),
                ("human", "Validate this output: {content}")
            ])
            
            # Only validate if there is content to check (e.g. quick chat response)
            content_to_check = ""
            if state.get("code_files") and "response.md" in state["code_files"]:
                content_to_check = state["code_files"]["response.md"]
                
            if content_to_check:
                chain = prompt | llm
                response = chain.invoke({"content": content_to_check[:1000]}) # check first 1000 chars to save tokens
                logger.info(f"[Safety Layer] Result: {response.content}")
                
        except Exception as e:
            logger.warning(f"[Safety Layer] Safety check bypassed due to error: {e}")
            
        return state
