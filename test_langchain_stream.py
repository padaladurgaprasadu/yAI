import asyncio, os
from dotenv import load_dotenv
load_dotenv()
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

async def main():
    llm = ChatOpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.getenv("NVIDIA_API_KEY"),
        model="meta/llama-3.1-8b-instruct",
        temperature=0.1,
        streaming=True
    )
    print("Sending request to LLM...")
    async for chunk in llm.astream([HumanMessage(content="Count to 10 slowly. Put a dash between numbers. Do not stop until 10.")]):
        print(chunk.content, flush=True)

asyncio.run(main())
