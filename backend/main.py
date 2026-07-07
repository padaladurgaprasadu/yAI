import sys
import os

# Make sure Python can find our backend module when running from the CLI
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.orchestrator.graph import build_orchestrator_graph
from backend.orchestrator.state import AiONState
import uuid
from backend.memory.neo4j_client import Neo4jClient

def main():
    if len(sys.argv) < 2:
        print("Usage: python backend/main.py \"Your project goal here\"")
        print("Example: python backend/main.py \"Build a student management system\"")
        sys.exit(1)

    # Get the user's goal from the command line arguments
    user_goal = sys.argv[1]
    
    print("[SYSTEM] Starting AiON Build Process...")
    print(f"Goal: {user_goal}")
    print("-" * 40)

    # Check for API key
    from dotenv import load_dotenv
    load_dotenv()
    if os.getenv("OPENROUTER_API_KEY") in [None, "your_openrouter_api_key_here"]:
        print("\n[ERROR] You must set a valid OPENROUTER_API_KEY in the .env file first!")
        sys.exit(1)

    # Build the graph
    try:
        app = build_orchestrator_graph()
    except Exception as e:
        print(f"\n[ERROR] Error building the graph: {e}")
        sys.exit(1)

    # Initialize the starting state
    project_id = f"proj-{str(uuid.uuid4())[:8]}"
    print(f"Project ID: {project_id}")
    
    try:
        memory_client = Neo4jClient()
        memory_client.log_project(project_id, user_goal)
        print("-> [Memory] Project logged to database.")
    except Exception as e:
        print(f"-> [WARNING] Could not connect to memory database: {e}")
        memory_client = None

    initial_state = AiONState(
        goal=user_goal,
        project_id=project_id,
        modules=[],
        blueprint={},
        code_files={},
        error=None
    )

    # Run the graph
    try:
        final_state = app.invoke(initial_state)
        
        print("\n[SUCCESS] Build Complete!")
        print("-" * 40)
        print("Final Code Files Generated:")
        
        # Save generated files locally
        if final_state.get("code_files"):
            output_dir = "generated_project"
            os.makedirs(output_dir, exist_ok=True)
            for path, content in final_state["code_files"].items():
                print(f"- {path}")
                # Save it
                full_path = os.path.join(output_dir, os.path.basename(path))
                with open(full_path, "w") as f:
                    f.write(content)
            print(f"\nFiles have been saved to the '{output_dir}' directory.")
            
        if memory_client:
            print("\n[Memory Check] Here is what the AI remembers about this project:")
            decisions = memory_client.get_project_decisions(project_id)
            for d in decisions:
                print(f"   - {d['agent']}: {d['rationale']}")
            memory_client.close()
            
        # Store the final blueprint in Semantic Memory
        if final_state.get("blueprint"):
            try:
                from backend.memory.chroma_client import ChromaClient
                vector_db = ChromaClient()
                vector_db.store_blueprint(project_id, user_goal, str(final_state["blueprint"]))
                print("\n[Semantic Memory] Project blueprint successfully stored in ChromaDB.")
            except Exception as e:
                print(f"\n[WARNING] Could not save to Semantic Memory: {e}")
            
    except Exception as e:
        print(f"\n[ERROR] An error occurred during the build process:\n{str(e)}")
        print("No files were generated.")

if __name__ == "__main__":
    main()
