import asyncio
import os
import json
from dotenv import load_dotenv
load_dotenv()
from backend.agents.base import BaseAgent
from langchain_core.messages import SystemMessage, HumanMessage

async def main():
    llm = BaseAgent().smart_llm
    reminder = '\n\n[CRITICAL REMINDER]: The user wants to build a project. You MUST return EXACTLY the `[BUILD] {"goal": "...", "agent_role": "..."}` format and nothing else. DO NOT generate markdown lists or conversational text. Output ONLY the [BUILD] tag.'
    msg = [HumanMessage(content='build a library management system web app' + reminder)]
    res = await llm.ainvoke(msg)
    print(repr(res.content))

asyncio.run(main())
