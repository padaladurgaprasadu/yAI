from typing import TypedDict, List, Dict, Any, Optional

class AiONState(TypedDict):
    """
    Represents the state of our project generation process as it flows through the agents.
    Think of this as a shared clipboard that all agents can read from and write to.
    """
    goal: str
    project_id: str
    agent_role: str
    modules: Optional[List[str]]
    dag_tasks: Optional[List[Dict[str, Any]]]
    blueprint: Optional[Dict[str, Any]]
    image: Optional[List[str]]
    code_files: Optional[Dict[str, str]]
    error: Optional[str]
    runtime_error: Optional[str]
    review_feedback: Optional[str]
    revision_count: int
    execution_retries: int
    execution_logs: Optional[list[str]]
    semantic_context: Optional[str]
