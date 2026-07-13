import asyncio
import os
import sys

# Ensure the backend module can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backend.agents.domain_experts import DomainOrchestrator

async def run_test():
    print("Initializing yAI Quantum Orchestrator Test...")
    orchestrator = DomainOrchestrator()
    
    test_request = "Design a telehealth platform. I need a secure Kubernetes deployment architecture, a React UI structure, and a process for handling ICD-10 medical coding for remote diagnostics."
    test_context = "Authorized internal testing environment."
    
    print(f"Submitting Test Request:\n'{test_request}'\n")
    
    try:
        print("Triggering Fractal Planning Engine...")
        result = await orchestrator.execute_parallel_experts(test_request, test_context)
        
        print("\nExecution Complete!")
        print(f"Synthesized Agents: {', '.join(result['experts'])}")
        
        print("\nFused Output Preview (First 500 chars):")
        print("-" * 40)
        print(result['fused_response'][:500] + "...\n")
        print("-" * 40)
        
        if len(result['experts']) >= 2:
            print("\nSUCCESS: Orchestrator successfully synthesized multiple specialized agents and executed the DAG!")
        else:
            print("\nWARNING: Orchestrator only synthesized a single agent or failed planning.")
            
    except Exception as e:
        print(f"\nERROR: Orchestrator test failed with exception: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
