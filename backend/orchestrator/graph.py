from langgraph.graph import StateGraph, END
from backend.orchestrator.state import AiONState
from backend.agents.planner import PlannerAgent
from backend.agents.architect import ArchitectAgent
from backend.agents.swarm_orchestrator import SwarmOrchestratorAgent
from backend.agents.coder import CoderAgent
from backend.agents.reviewer import ReviewerAgent
from backend.agents.executor import ExecutorAgent
from backend.agents.devops import DevOpsAgent
from backend.agents.ml_trainer import AIMLModelTrainingAgent
from backend.agents.hyperparameter_tuner import AutoHyperparameterTuningAgent
from backend.agents.researcher import ResearchAgent
from backend.agents.tester import TesterAgent
from backend.agents.dependency_checker import DependencyCheckerAgent
from backend.agents.auditor import AuditorAgent

def should_continue(state: AiONState):
    """
    Routing function to determine if we should loop back to the Coder or finish.
    """
    feedback = state.get("review_feedback", "")
    revision_count = state.get("revision_count", 0)
    
    if feedback == "APPROVED":
        return "auditor"
    
    if revision_count >= 2:
        print("   -> [System] Max revisions reached. Proceeding to auditor.")
        return "auditor"
        
    return "swarm_orchestrator"

def should_continue_audit(state: AiONState):
    """
    Routing function for the advanced Auditor QA phase.
    """
    feedback = state.get("audit_feedback", "")
    revision_count = state.get("revision_count", 0)
    
    if feedback == "APPROVED":
        return "devops"
    
    if revision_count >= 2:
        print("   -> [System] Max revisions reached in audit. Proceeding to devops.")
        return "devops"
        
    return "swarm_orchestrator"

def check_dependencies(state: AiONState):
    """
    Routing function to loop back to Coder if there are missing dependencies.
    """
    missing = state.get("missing_dependencies", [])
    revision_count = state.get("revision_count", 0)
    
    if missing and revision_count < 3:
        print(f"   -> [Graph] Routing back to Swarm Orchestrator to generate missing files: {missing}")
        return "swarm_orchestrator"
    elif missing:
        print(f"   -> [Graph] Max revisions reached while fixing dependencies. Proceeding anyway.")
        
    return "ml_trainer"

def should_retry_execution(state: AiONState):
    """
    Routing function to loop back to Coder if Executor failed.
    """
    error = state.get("runtime_error")
    execution_retries = state.get("execution_retries", 0)
    
    if error and execution_retries < 3:
        print(f"   -> [Auto-Heal] Execution failed (Retry {execution_retries + 1}/3). Looping back to Swarm Orchestrator for healing.")
        return "swarm_orchestrator"
        
    if error:
        print("   -> [Auto-Heal] Max execution retries reached. Failing gracefully.")
    
    return END

def build_graph():
    """
    Builds and returns the LangGraph state machine.
    Flow: Planner -> Architect -> Coder <-> DependencyChecker -> ML Trainer -> ... -> END
    """
    workflow = StateGraph(AiONState)

    planner = PlannerAgent()
    architect = ArchitectAgent()
    coder = CoderAgent()
    dep_checker = DependencyCheckerAgent()
    reviewer = ReviewerAgent()
    devops = DevOpsAgent()
    executor = ExecutorAgent()
    ml_trainer = AIMLModelTrainingAgent()
    hp_tuner = AutoHyperparameterTuningAgent()
    tester = TesterAgent()
    auditor = AuditorAgent()

    researcher = ResearchAgent()

    workflow.add_node("planner", planner.run)
    workflow.add_node("researcher", researcher.run)
    workflow.add_node("architect", architect.run)
    
    swarm_orchestrator = SwarmOrchestratorAgent()
    workflow.add_node("swarm_orchestrator", swarm_orchestrator.run)
    
    workflow.add_node("coder", coder.run)
    workflow.add_node("dependency_checker", dep_checker.run)
    workflow.add_node("ml_trainer", ml_trainer.run)
    workflow.add_node("hp_tuner", hp_tuner.run)
    workflow.add_node("tester", tester.run)
    workflow.add_node("reviewer", reviewer.run)
    workflow.add_node("auditor", auditor.run)
    workflow.add_node("devops", devops.run)
    workflow.add_node("executor", executor.run)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "architect")
    workflow.add_edge("architect", "swarm_orchestrator")
    workflow.add_edge("swarm_orchestrator", "coder")
    
    workflow.add_edge("coder", "dependency_checker")
    workflow.add_conditional_edges("dependency_checker", check_dependencies, {"swarm_orchestrator": "swarm_orchestrator", "ml_trainer": "ml_trainer"})
    
    workflow.add_edge("ml_trainer", "hp_tuner")
    workflow.add_edge("hp_tuner", "tester")
    workflow.add_edge("tester", "reviewer")
    workflow.add_conditional_edges("reviewer", should_continue, {"swarm_orchestrator": "swarm_orchestrator", "auditor": "auditor"})
    workflow.add_conditional_edges("auditor", should_continue_audit, {"swarm_orchestrator": "swarm_orchestrator", "devops": "devops"})
    workflow.add_edge("devops", "executor")
    workflow.add_conditional_edges("executor", should_retry_execution, {"swarm_orchestrator": "swarm_orchestrator", END: END})

    return workflow.compile()

def build_plan_graph():
    """
    Builds the first half of the graph (Phase 4): Planner -> Researcher -> Architect -> END
    """
    workflow = StateGraph(AiONState)
    planner = PlannerAgent()
    researcher = ResearchAgent()
    architect = ArchitectAgent()
    
    workflow.add_node("planner", planner.run)
    workflow.add_node("researcher", researcher.run)
    workflow.add_node("architect", architect.run)
    
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "architect")
    workflow.add_edge("architect", END)
    
    return workflow.compile()

from langgraph.checkpoint.memory import MemorySaver

# Global memory saver for human-in-the-loop persistence across requests
workflow_memory = MemorySaver()

def build_generate_graph():
    """
    Builds the second half of the graph (Phase 4): ContextOrchestrator -> Coder <-> Reviewer -> DevOps -> Executor -> END
    """
    workflow = StateGraph(AiONState)
    from backend.memory.context_orchestrator import ContextOrchestratorAgent
    
    ctx_orchestrator = ContextOrchestratorAgent()
    coder = CoderAgent()
    reviewer = ReviewerAgent()
    devops = DevOpsAgent()
    executor = ExecutorAgent()
    ml_trainer = AIMLModelTrainingAgent()
    hp_tuner = AutoHyperparameterTuningAgent()
    tester = TesterAgent()
    auditor = AuditorAgent()
    
    workflow.add_node("context_orchestrator", ctx_orchestrator.run)
    workflow.add_node("coder", coder.run)
    workflow.add_node("ml_trainer", ml_trainer.run)
    workflow.add_node("hp_tuner", hp_tuner.run)
    workflow.add_node("tester", tester.run)
    workflow.add_node("reviewer", reviewer.run)
    workflow.add_node("auditor", auditor.run)
    workflow.add_node("devops", devops.run)
    workflow.add_node("executor", executor.run)
    
    workflow.set_entry_point("context_orchestrator")
    
    workflow.add_edge("context_orchestrator", "coder")
    workflow.add_edge("coder", "ml_trainer")
    workflow.add_edge("ml_trainer", "hp_tuner")
    workflow.add_edge("hp_tuner", "tester")
    workflow.add_edge("tester", "reviewer")
    
    workflow.add_conditional_edges("reviewer", should_continue, {"coder": "coder", "auditor": "auditor"})
    workflow.add_conditional_edges("auditor", should_continue_audit, {"coder": "coder", "devops": "devops"})
    workflow.add_edge("devops", "executor")
    workflow.add_conditional_edges("executor", should_retry_execution, {"coder": "coder", END: END})
    
    # Compile with memory saver (no interrupts, fully autonomous)
    return workflow.compile(checkpointer=workflow_memory)
