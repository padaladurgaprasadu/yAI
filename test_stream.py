from backend.orchestrator.state import AiONState
from backend.orchestrator.graph import build_generate_graph

graph = build_generate_graph()
thread_config = {"configurable": {"thread_id": "test_project_123"}}

# Create a mock state
initial_state = AiONState(
    project_id="test_project_123",
    goal="test app",
    blueprint={"test": "data"},
    code_files={},
    revision_count=0,
    review_feedback="",
    execution_retries=0,
    execution_logs=[]
)

print("Starting stream...")
for output in graph.stream(initial_state, config=thread_config):
    node_name = list(output.keys())[0]
    final_st = output[node_name]
    print(f"Node finished: {node_name}")
    print(f"Has code_files: {'code_files' in final_st}")
    
    if node_name == "coder":
        print(f"CODER EMITTED: {type(final_st)}")
        break
