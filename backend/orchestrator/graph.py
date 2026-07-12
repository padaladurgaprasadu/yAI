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
from backend.agents.tester import TesterAgent
from backend.agents.supervisor import SwarmSupervisorAgent
from backend.agents.mcp_client import MCPClientAgent
from backend.agents.adversary import AdversaryAgent
from langgraph.checkpoint.memory import MemorySaver

def should_continue_review(state: AiONState):
    feedback = state.get("review_feedback", "")
    rev_count = state.get("revision_count", 0)
    if feedback == "APPROVED":
        return "adversary"
    if rev_count >= 3:
        print("   -> [Graph] Max code revisions reached. Proceeding to adversary.")
        return "adversary"
    print(f"   -> [Graph] Review failed (Attempt {rev_count}/3). Routing back to Coder.")
    return "coder"

def should_continue_adversary(state: AiONState):
    feedback = state.get("review_feedback", "")
    rev_count = state.get("revision_count", 0)
    if "ADVERSARY ATTACK FAILED" not in feedback:
        return "visual_critique"
    if rev_count >= 4:
        print("   -> [Graph] Max code revisions reached (Adversary). Proceeding to visual critique.")
        return "visual_critique"
    print(f"   -> [Graph] Adversary attack succeeded. Routing back to Coder.")
    return "coder"

def should_continue_visual(state: AiONState):
    feedback = state.get("visual_critique_feedback", [])
    rev_count = state.get("visual_revision_count", 0)
    
    # If feedback is empty list, None, or a string indicating approval, it's passed.
    if not feedback or feedback == "APPROVED" or feedback == "ship":
        return "executor"
    
    if rev_count >= 2:
        print("   -> [Graph] Max visual revisions reached. Proceeding to execution.")
        return "executor"
    print(f"   -> [Graph] Visual critique failed (Attempt {rev_count}/2). Routing back to Coder.")
    return "coder"

def should_continue_execution(state: AiONState):
    runtime_error = state.get("runtime_error")
    retries = state.get("execution_retries", 0)
    if not runtime_error:
        return "devops"
    if retries >= 3:
        print("   -> [Graph] Max execution retries reached. Proceeding to devops.")
        return "devops"
    print(f"   -> [Graph] Execution failed with error: {runtime_error}. Routing back to Coder (Attempt {retries}/3).")
    return "coder"

def route_from_supervisor(state: AiONState):
    tasks = state.get("swarm_tasks", [])
    if tasks and len(tasks) > 0:
        next_agent = tasks[0].get("next_agent", "mcp_client")
        print(f"   -> [Swarm Routing] Supervisor delegating to: {next_agent}")
        return next_agent
    return "mcp_client"

def build_orchestrator_graph():
    """
    Builds the unified 11-Layer Orchestrator Pipeline as defined in the yAI End-to-End Workflow.
    CORE LOOP: Intent -> Repository -> Template -> Planner -> Architect -> Design -> Coder -> Quality (Tester, Reviewer, Adversary, Visual) -> Execution -> Deployment -> Memory
    """
    workflow = StateGraph(AiONState)
    
    # 1. Initialize nodes
    supervisor = SwarmSupervisorAgent()
    mcp_client = MCPClientAgent()
    template = TemplateAgent()
    planner = PlannerAgent()
    architect = ArchitectAgent()
    design = DesignAgent()
    coder = CoderAgent()
    tester = TesterAgent()
    reviewer = ReviewerAgent()
    adversary = AdversaryAgent()
    visual_critique = VisualCritiqueAgent()
    executor = ExecutorAgent()
    devops = DevOpsAgent()
    memory = MemoryAgent()
    
    # 2. Add nodes
    workflow.add_node("supervisor", supervisor.run)
    workflow.add_node("mcp_client", mcp_client.run)
    workflow.add_node("template", template.run)
    workflow.add_node("planner", planner.run)
    workflow.add_node("architect", architect.run)
    workflow.add_node("design", design.run)
    workflow.add_node("coder", coder.run)
    workflow.add_node("tester", tester.run)
    workflow.add_node("reviewer", reviewer.run)
    workflow.add_node("adversary", adversary.run)
    workflow.add_node("visual_critique", visual_critique.run)
    workflow.add_node("executor", executor.run)
    workflow.add_node("devops", devops.run)
    workflow.add_node("memory", memory.run)
    
    # 3. Add edges (The Core Loop)
    workflow.set_entry_point("supervisor")
    
    # Layer 1: Intent Intelligence
    workflow.add_conditional_edges(
        "supervisor", 
        route_from_supervisor, 
        {"mcp_client": "mcp_client", "template": "template", "coder": "coder"}
    )
    
    # Layer 2: Repository Intelligence
    workflow.add_edge("mcp_client", "template")
    
    # Layer 3: Template Intelligence
    workflow.add_edge("template", "planner")
    
    # Layer 4: Planning Intelligence
    workflow.add_edge("planner", "architect")
    
    # Layer 5: Architecture Intelligence
    workflow.add_edge("architect", "design")
    
    # Layer 6: Design Intelligence
    workflow.add_edge("design", "coder")
    
    # Layer 7: Engineering
    workflow.add_edge("coder", "tester")
    
    # Layer 8: Quality Intelligence (Tester -> Reviewer -> Adversary -> Visual)
    workflow.add_edge("tester", "reviewer")
    workflow.add_conditional_edges("reviewer", should_continue_review, {"coder": "coder", "adversary": "adversary"})
    workflow.add_conditional_edges("adversary", should_continue_adversary, {"coder": "coder", "visual_critique": "visual_critique"})
    workflow.add_conditional_edges("visual_critique", should_continue_visual, {"coder": "coder", "executor": "executor"})
    
    # Layer 9: Execution Intelligence
    workflow.add_conditional_edges("executor", should_continue_execution, {"coder": "coder", "devops": "devops"})
    
    # Layer 10: Deployment Intelligence
    workflow.add_edge("devops", "memory")
    
    # Layer 11: Memory Intelligence
    workflow.add_edge("memory", END)
    
    # Compile with memory saver (for human-in-the-loop persistence if needed)
    workflow_memory = MemorySaver()
    return workflow.compile(checkpointer=workflow_memory)
