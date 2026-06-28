from langgraph.graph import StateGraph, END
from backend.orchestrator.state import AiONState
from backend.agents.planner import PlannerAgent
from backend.agents.architect import ArchitectAgent
from backend.agents.coder import CoderAgent
from backend.agents.reviewer import ReviewerAgent
from backend.agents.executor import ExecutorAgent
from backend.agents.devops import DevOpsAgent
from backend.agents.ml_trainer import AIMLModelTrainingAgent
from backend.agents.hyperparameter_tuner import AutoHyperparameterTuningAgent
from backend.agents.researcher import ResearchAgent
from backend.agents.tester import TesterAgent

def should_continue(state: AiONState):
    """
    Routing function to determine if we should loop back to the Coder or finish.
    """
    feedback = state.get("review_feedback", "")
    revision_count = state.get("revision_count", 0)
    
    if feedback == "APPROVED":
        return "devops"
    
    if revision_count >= 2:
        print("   -> [System] Max revisions reached. Proceeding to devops.")
        return "devops"
        
    return "coder"

def should_retry_execution(state: AiONState):
    """
    Routing function to loop back to Coder if Executor failed.
    """
    error = state.get("runtime_error")
    execution_retries = state.get("execution_retries", 0)
    
    if error and execution_retries < 3:
        print(f"   -> [Auto-Heal] Execution failed (Retry {execution_retries + 1}/3). Looping back to Coder for healing.")
        return "coder"
        
    if error:
        print("   -> [Auto-Heal] Max execution retries reached. Failing gracefully.")
    
    return END

def build_graph():
    """
    Builds and returns the LangGraph state machine.
    Flow: Planner -> Architect -> Coder <-> Reviewer -> DevOps -> Executor -> END
    """
    workflow = StateGraph(AiONState)

    planner = PlannerAgent()
    architect = ArchitectAgent()
    coder = CoderAgent()
    reviewer = ReviewerAgent()
    devops = DevOpsAgent()
    executor = ExecutorAgent()
    ml_trainer = AIMLModelTrainingAgent()
    hp_tuner = AutoHyperparameterTuningAgent()
    tester = TesterAgent()

    researcher = ResearchAgent()

    workflow.add_node("planner", planner.run)
    workflow.add_node("researcher", researcher.run)
    workflow.add_node("architect", architect.run)
    workflow.add_node("coder", coder.run)
    workflow.add_node("ml_trainer", ml_trainer.run)
    workflow.add_node("hp_tuner", hp_tuner.run)
    workflow.add_node("tester", tester.run)
    workflow.add_node("reviewer", reviewer.run)
    workflow.add_node("devops", devops.run)
    workflow.add_node("executor", executor.run)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "architect")
    workflow.add_edge("architect", "coder")
    
    workflow.add_edge("coder", "ml_trainer")
    workflow.add_edge("ml_trainer", "hp_tuner")
    workflow.add_edge("hp_tuner", "tester")
    workflow.add_edge("tester", "reviewer")
    workflow.add_conditional_edges("reviewer", should_continue, {"coder": "coder", "devops": "devops"})
    workflow.add_edge("devops", "executor")
    workflow.add_conditional_edges("executor", should_retry_execution, {"coder": "coder", END: END})

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

def build_generate_graph():
    """
    Builds the second half of the graph (Phase 4): Coder <-> Reviewer -> DevOps -> Executor -> END
    """
    workflow = StateGraph(AiONState)
    coder = CoderAgent()
    reviewer = ReviewerAgent()
    devops = DevOpsAgent()
    executor = ExecutorAgent()
    ml_trainer = AIMLModelTrainingAgent()
    hp_tuner = AutoHyperparameterTuningAgent()
    tester = TesterAgent()
    
    workflow.add_node("coder", coder.run)
    workflow.add_node("ml_trainer", ml_trainer.run)
    workflow.add_node("hp_tuner", hp_tuner.run)
    workflow.add_node("tester", tester.run)
    workflow.add_node("reviewer", reviewer.run)
    workflow.add_node("devops", devops.run)
    workflow.add_node("executor", executor.run)
    
    workflow.set_entry_point("coder")
    
    workflow.add_edge("coder", "ml_trainer")
    workflow.add_edge("ml_trainer", "hp_tuner")
    workflow.add_edge("hp_tuner", "tester")
    workflow.add_edge("tester", "reviewer")
    
    workflow.add_conditional_edges("reviewer", should_continue, {"coder": "coder", "devops": "devops"})
    workflow.add_edge("devops", "executor")
    workflow.add_conditional_edges("executor", should_retry_execution, {"coder": "coder", END: END})
    
    return workflow.compile()
