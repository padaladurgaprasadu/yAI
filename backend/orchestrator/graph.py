from langgraph.graph import StateGraph, END
from backend.orchestrator.state import AiONState
from backend.agents.planner import PlannerAgent
from backend.agents.template_intelligence import TemplateAgent
from backend.agents.architect import ArchitectAgent
from backend.agents.design import DesignAgent
from backend.agents.coder import CoderAgent
from backend.agents.reviewer import ReviewerAgent
from backend.agents.visual_critique import VisualCritiqueAgent
from backend.agents.devops import DevOpsAgent
from backend.agents.executor import ExecutorAgent
from backend.agents.memory import MemoryAgent
from langgraph.checkpoint.memory import MemorySaver

def should_continue_review(state: AiONState):
    feedback = state.get("review_feedback", "")
    rev_count = state.get("revision_count", 0)
    if feedback == "APPROVED":
        return "visual_critique"
    if rev_count >= 3:
        print("   -> [Graph] Max code revisions reached. Proceeding to visual critique.")
        return "visual_critique"
    print(f"   -> [Graph] Review failed (Attempt {rev_count}/3). Routing back to Coder.")
    return "coder"

def should_continue_visual(state: AiONState):
    feedback = state.get("visual_critique_feedback", [])
    rev_count = state.get("visual_revision_count", 0)
    
    # If feedback is empty list, None, or a string indicating approval, it's passed.
    if not feedback or feedback == "APPROVED" or feedback == "ship":
        return "devops"
    
    if rev_count >= 2:
        print("   -> [Graph] Max visual revisions reached. Proceeding to devops.")
        return "devops"
    print(f"   -> [Graph] Visual critique failed (Attempt {rev_count}/2). Routing back to Coder.")
    return "coder"

def should_continue_execution(state: AiONState):
    runtime_error = state.get("runtime_error")
    retries = state.get("execution_retries", 0)
    if not runtime_error:
        return "memory"
    if retries >= 3:
        print("   -> [Graph] Max execution retries reached. Proceeding to memory.")
        return "memory"
    print(f"   -> [Graph] Execution failed with error: {runtime_error}. Routing back to Coder (Attempt {retries}/3).")
    return "coder"

def build_orchestrator_graph():
    """
    Builds the unified 12-agent Orchestrator Pipeline as defined in the user prompt set.
    CORE LOOP: Planner -> Architect -> Design -> Coder -> Reviewer(loop) -> VisualCritique(loop) -> DevOps -> Executor -> Memory
    """
    workflow = StateGraph(AiONState)
    
    # 1. Initialize nodes
    planner = PlannerAgent()
    template = TemplateAgent()
    architect = ArchitectAgent()
    design = DesignAgent()
    coder = CoderAgent()
    reviewer = ReviewerAgent()
    visual_critique = VisualCritiqueAgent()
    devops = DevOpsAgent()
    executor = ExecutorAgent()
    memory = MemoryAgent()
    
    # 2. Add nodes
    workflow.add_node("planner", planner.run)
    workflow.add_node("template", template.run)
    workflow.add_node("architect", architect.run)
    workflow.add_node("design", design.run)
    workflow.add_node("coder", coder.run)
    workflow.add_node("reviewer", reviewer.run)
    workflow.add_node("visual_critique", visual_critique.run)
    workflow.add_node("devops", devops.run)
    workflow.add_node("executor", executor.run)
    workflow.add_node("memory", memory.run)
    
    # 3. Add edges (The Core Loop)
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "template")
    workflow.add_edge("template", "architect")
    workflow.add_edge("architect", "design")
    workflow.add_edge("design", "coder")
    workflow.add_edge("coder", "reviewer")
    
    workflow.add_conditional_edges("reviewer", should_continue_review, {"coder": "coder", "visual_critique": "visual_critique"})
    workflow.add_conditional_edges("visual_critique", should_continue_visual, {"coder": "coder", "devops": "devops"})
    
    workflow.add_edge("devops", "executor")
    workflow.add_conditional_edges("executor", should_continue_execution, {"coder": "coder", "memory": "memory"})
    workflow.add_edge("memory", END)
    
    # Compile with memory saver (for human-in-the-loop persistence if needed)
    workflow_memory = MemorySaver()
    return workflow.compile(checkpointer=workflow_memory)
