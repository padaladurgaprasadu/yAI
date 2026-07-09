import asyncio
from backend.agents.router import OmniIntelligenceEngine
from backend.agents.base import BaseAgent

async def main():
    r = OmniIntelligenceEngine(BaseAgent().fast_llm)
    res = await r.adetect_intent('Vijayawada')
    print("RES:", res)

asyncio.run(main())
