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
    missing_dependencies: Optional[List[str]]
    error: Optional[str]
    runtime_error: Optional[str]
    review_feedback: Optional[str]
    audit_feedback: Optional[str]
    revision_count: int
    execution_retries: int
    execution_logs: Optional[list[str]]
    semantic_context: Optional[str]
    
    # Phase 1: Omni Intelligence Engine
    execution_mode: Optional[str] # Lightning, Fast, Deep, Autonomous
    complexity: Optional[str]
    compressed_context: Optional[str]
    
    # yAI Swarm Protocol State
    swarm_tasks: Optional[List[Dict[str, Any]]] # Dynamic tasks for sub-agents
    swarm_results: Optional[List[Dict[str, Any]]] # Results collected from sub-agents
    federation_peer_id: Optional[str] # ID for cross-machine federation
    
    # Advanced Multi-Agent State
    design_tokens: Optional[Dict[str, Any]]
    visual_critique_feedback: Optional[str]
    visual_revision_count: int
    memory_log: Optional[Dict[str, Any]]
    architect_decisions: Optional[List[Dict[str, Any]]]
    memory_persisted: Optional[Dict[str, Any]]
    
    # Research and Novelty
    uploaded_files: Optional[List[Dict[str, str]]] # [{"name": "file.pdf", "content": "base64..."}]
    research_synthesis: Optional[Dict[str, Any]]
    novelty_recommendation: Optional[Dict[str, Any]]
