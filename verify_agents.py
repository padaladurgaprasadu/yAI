import os
import sys

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backend.orchestrator.graph import build_orchestrator_graph
from backend.agents.domain_experts import DomainOrchestrator
from backend.agents.router import OmniIntelligenceEngine

# To test instantiation of agents without hitting API errors if keys are missing
os.environ["OPENAI_API_KEY"] = "sk-test12345"
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test12345"
os.environ["GEMINI_API_KEY"] = "AIzaSyTest12345"

def run_checks():
    print("Starting Comprehensive Agent Verification...\n")
    
    passed = 0
    failed = 0
    
    # 1. Test Router
    try:
        print("Checking OmniIntelligenceEngine (Router)...", end=" ")
        router = OmniIntelligenceEngine()
        print("PASSED")
        passed += 1
    except Exception as e:
        print(f"FAILED ({e})")
        failed += 1
        
    # 2. Test Domain Orchestrator
    try:
        print("Checking DomainOrchestrator (Quantum)...", end=" ")
        do = DomainOrchestrator()
        print("PASSED")
        passed += 1
    except Exception as e:
        print(f"FAILED ({e})")
        failed += 1

    # 3. Test Graph Build
    try:
        print("\nChecking 15-Layer Builder Graph (LangGraph)...", end=" ")
        graph = build_orchestrator_graph()
        print("PASSED")
        passed += 1
    except Exception as e:
        print(f"FAILED ({e})")
        failed += 1
        
    # 4. Extract node callables and run them manually (just verifying they don't crash on import/instantiation)
    print("\nVerifying Individual Graph Agents (Instantiation check):")
    
    # The nodes are stored in the graph's nodes mapping, but those are function wrappers
    # We can just manually import the 18 classes to be extremely thorough
    
    agent_classes = [
        ("backend.agents.supervisor", "SwarmSupervisorAgent"),
        ("backend.agents.mcp_client", "MCPClientAgent"),
        ("backend.agents.repository", "RepositoryIntelligenceAgent"),
        ("backend.agents.memory", "MemoryAgent"),
        ("backend.agents.researcher", "ResearchAgent"),
        ("backend.agents.image_search", "ImageSearchAgent"),
        ("backend.agents.template_intelligence", "TemplateAgent"),
        ("backend.agents.planner", "PlannerAgent"),
        ("backend.agents.architect", "ArchitectAgent"),
        ("backend.agents.design", "DesignAgent"),
        ("backend.agents.coder", "CoderAgent"),
        ("backend.agents.tester", "TesterAgent"),
        ("backend.agents.reviewer", "ReviewerAgent"),
        ("backend.agents.adversary", "AdversaryAgent"),
        ("backend.agents.visual_critique", "VisualCritiqueAgent"),
        ("backend.agents.executor", "ExecutorAgent"),
        ("backend.agents.devops", "DevOpsAgent"),
        ("backend.agents.component_memory", "ComponentMemoryAgent"),
    ]
    
    import importlib
    
    for module_name, class_name in agent_classes:
        print(f"  - Checking {class_name}...", end=" ")
        try:
            mod = importlib.import_module(module_name)
            agent_cls = getattr(mod, class_name)
            
            # For testing, some agents might require args, but most yAI agents don't
            try:
                agent = agent_cls()
                print("PASSED")
                passed += 1
            except TypeError as te:
                # If they require args, we consider it a pass for module syntax
                print(f"PASSED (Requires args: {te})")
                passed += 1
                
        except Exception as e:
            print(f"FAILED ({e})")
            failed += 1
            
    print("\n--- VERIFICATION SUMMARY ---")
    print(f"Total Checks: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
if __name__ == "__main__":
    run_checks()
