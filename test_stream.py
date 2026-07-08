import asyncio
from backend.agents.base import BaseAgent
from langchain_core.messages import HumanMessage

async def main():
    llm = BaseAgent().fast_llm
    print("Starting stream...")
    async for chunk in llm.astream([HumanMessage(content='Count to 10 slowly, spelling out the numbers')]):
        print(chunk.content, end='', flush=True)
    print("\nDone.")

asyncio.run(main())
