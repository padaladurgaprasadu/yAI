import asyncio
from backend.agents.base import BaseAgent
from backend.utils.compliance import StreamingComplianceEngine
from langchain_core.messages import HumanMessage

async def main():
    agent = BaseAgent()
    messages = [HumanMessage(content="Explain quantum computing.")]
    
    print("Starting LLM stream...")
    try:
        compliance_engine = StreamingComplianceEngine(agent.llm.stream(messages))
        for text_chunk in compliance_engine.process():
            print(text_chunk, end="", flush=True)
    except Exception as e:
        import traceback
        print("EXCEPTION CAUGHT!")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
