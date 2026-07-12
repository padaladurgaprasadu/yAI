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

def should_continue_coder(state: AiONState):
    if state.get("is_fast_track"):
        print("   -> [Graph] Fast Track enabled. Bypassing Quality Intelligence and proceeding to Memory.")
        return "memory"
    return "tester"

def route_from_supervisor(state: AiONState):
    tasks = state.get("swarm_tasks", [])
    if tasks and len(tasks) > 0:
        next_agent = tasks[0].get("next_agent", "mcp_client")
        print(f"   -> [Swarm Routing] Supervisor delegating to: {next_agent}")
        return next_agent
    return "mcp_client"

def route_from_memory(state: AiONState):
    router = state.get("router_analysis", {})
    if router.get("requires_web_search", False): return "researcher"
    if router.get("requires_image_search", False): return "image_intelligence"
    if router.get("requires_templates", False): return "template"
    return "planner"

def route_from_researcher(state: AiONState):
    router = state.get("router_analysis", {})
    if router.get("requires_image_search", False): return "image_intelligence"
    if router.get("requires_templates", False): return "template"
    return "planner"

def route_from_image(state: AiONState):
    router = state.get("router_analysis", {})
    if router.get("requires_templates", False): return "template"
    return "planner"

def build_orchestrator_graph():
    """
    Builds the unified 11-Layer Orchestrator Pipeline as defined in the yAI End-to-End Workflow.
    CORE LOOP: Intent -> Repository -> Template -> Planner -> Architect -> Design -> Coder -> Quality (Tester, Reviewer, Adversary, Visual) -> Execution -> Deployment -> Memory
    """
    workflow = StateGraph(AiONState)
    
    # 1. Initialize lazy-loaded node wrappers
    def run_supervisor(state):
        from backend.agents.supervisor import SwarmSupervisorAgent
        return SwarmSupervisorAgent().run(state)
        
    def run_mcp_client(state):
        from backend.agents.mcp_client import MCPClientAgent
        return MCPClientAgent().run(state)
        
    def run_repository(state):
        from backend.agents.repository import RepositoryIntelligenceAgent
        return RepositoryIntelligenceAgent().run(state)
        
    def run_memory_retrieval(state):
        from backend.agents.memory import MemoryAgent
        return MemoryAgent().run_retrieval(state)
        
    def run_researcher(state):
        from backend.agents.researcher import ResearchAgent
        return ResearchAgent().run(state)
        
    def run_image_intelligence(state):
        from backend.agents.image_search import ImageSearchAgent
        return ImageSearchAgent().run(state)
        
    def run_template(state):
        from backend.agents.template_intelligence import TemplateAgent
        return TemplateAgent().run(state)
        
    def run_planner(state):
        from backend.agents.planner import PlannerAgent
        return PlannerAgent().run(state)
        
    def run_architect(state):
        from backend.agents.architect import ArchitectAgent
        return ArchitectAgent().run(state)
        
    def run_design(state):
        from backend.agents.design import DesignAgent
        return DesignAgent().run(state)
        
    def run_coder(state):
        from backend.agents.coder import CoderAgent
        return CoderAgent().run(state)
        
    def run_tester(state):
        from backend.agents.tester import TesterAgent
        return TesterAgent().run(state)
        
    def run_reviewer(state):
        from backend.agents.reviewer import ReviewerAgent
        return ReviewerAgent().run(state)
        
    def run_adversary(state):
        from backend.agents.adversary import AdversaryAgent
        return AdversaryAgent().run(state)
        
    def run_visual_critique(state):
        from backend.agents.visual_critique import VisualCritiqueAgent
        return VisualCritiqueAgent().run(state)
        
    def run_executor(state):
        from backend.agents.executor import ExecutorAgent
        return ExecutorAgent().run(state)
        
    def run_devops(state):
        from backend.agents.devops import DevOpsAgent
        return DevOpsAgent().run(state)
        
    def run_memory_storage(state):
        from backend.agents.memory import MemoryAgent
        return MemoryAgent().run_storage(state)
    
    # 2. Add nodes
    workflow.add_node("supervisor", run_supervisor)
    workflow.add_node("mcp_client", run_mcp_client)
    workflow.add_node("repository", run_repository)
    workflow.add_node("memory_retrieval", run_memory_retrieval)
    workflow.add_node("researcher", run_researcher)
    workflow.add_node("image_intelligence", run_image_intelligence)
    workflow.add_node("template", run_template)
    workflow.add_node("planner", run_planner)
    workflow.add_node("architect", run_architect)
    workflow.add_node("design", run_design)
    workflow.add_node("coder", run_coder)
    workflow.add_node("tester", run_tester)
    workflow.add_node("reviewer", run_reviewer)
    workflow.add_node("adversary", run_adversary)
    workflow.add_node("visual_critique", run_visual_critique)
    workflow.add_node("executor", run_executor)
    workflow.add_node("devops", run_devops)
    workflow.add_node("memory_storage", run_memory_storage)
    
    # 3. Add edges (The Core 15-Layer Loop)
    workflow.set_entry_point("supervisor")
    
    # Layer 1 & 2: Intent & Model Selection (Handled by Router in API before Graph, Supervisor manages fast track routing)
    workflow.add_conditional_edges(
        "supervisor", 
        route_from_supervisor, 
        {"mcp_client": "mcp_client", "coder": "coder"}
    )
    
    # Layer 3: Repository Intelligence
    workflow.add_edge("mcp_client", "repository")
    
    # Layer 4: Memory Intelligence
    workflow.add_edge("repository", "memory_retrieval")
    
    # Layer 5: Web & Research Intelligence (Conditional)
    workflow.add_conditional_edges("memory_retrieval", route_from_memory, {
        "researcher": "researcher",
        "image_intelligence": "image_intelligence",
        "template": "template",
        "planner": "planner"
    })
    
    # Layer 6: Image Intelligence (Conditional)
    workflow.add_conditional_edges("researcher", route_from_researcher, {
        "image_intelligence": "image_intelligence",
        "template": "template",
        "planner": "planner"
    })
    
    # Layer 7: Template Intelligence (Conditional)
    workflow.add_conditional_edges("image_intelligence", route_from_image, {
        "template": "template",
        "planner": "planner"
    })
    
    # Layer 8: Planning Intelligence
    workflow.add_edge("template", "planner")
    
    # Layer 9: Architecture Intelligence
    workflow.add_edge("planner", "architect")
    
    # Layer 10: Design Intelligence
    workflow.add_edge("architect", "design")
    
    # Layer 11: Multi-Agent Engineering
    workflow.add_edge("design", "coder")
    
    # Layer 12: Quality Intelligence (Tester -> Reviewer -> Adversary -> Visual)
    workflow.add_conditional_edges("coder", should_continue_coder, {"memory_storage": "memory_storage", "tester": "tester"})
    workflow.add_edge("tester", "reviewer")
    workflow.add_conditional_edges("reviewer", should_continue_review, {"coder": "coder", "adversary": "adversary"})
    workflow.add_conditional_edges("adversary", should_continue_adversary, {"coder": "coder", "visual_critique": "visual_critique"})
    workflow.add_conditional_edges("visual_critique", should_continue_visual, {"coder": "coder", "executor": "executor"})
    
    # Layer 13: Execution Intelligence
    workflow.add_conditional_edges("executor", should_continue_execution, {"coder": "coder", "devops": "devops"})
    
    # Layer 14: Deployment Intelligence
    workflow.add_edge("devops", "memory_storage")
    
    # Layer 15: Memory & Learning
    workflow.add_edge("memory_storage", END)
    
    # Compile with memory saver (for human-in-the-loop persistence if needed)
    workflow_memory = MemorySaver()
    return workflow.compile(checkpointer=workflow_memory)
