import sys
import traceback

def run():
    try:
        from backend.agents.base import BaseAgent
        from backend.utils.compliance import StreamingComplianceEngine
        from langchain_core.messages import HumanMessage
        
        agent = BaseAgent()
        messages = [HumanMessage(content="Explain quantum computing.")]
        
        print("Starting stream...")
        stream_iter = agent.llm.stream(messages)
        engine = StreamingComplianceEngine(stream_iter)
        
        count = 0
        for chunk in engine.process():
            count += 1
            if count > 5:
                break
        print(f"Stream successful, read {count} chunks.")
    except Exception as e:
        with open("error.log", "w") as f:
            f.write(traceback.format_exc())
        print("Error written to error.log")

if __name__ == "__main__":
    run()
