import asyncio, os
from dotenv import load_dotenv
load_dotenv()
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

async def main():
    llm = ChatOpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.getenv("NVIDIA_API_KEY"),
        model="meta/llama-3.1-70b-instruct",
        temperature=0.1,
        streaming=True
    )
    print("Sending request with empty AI message...")
    try:
        async for chunk in llm.astream([
            HumanMessage(content="Show me Kurnool"),
            AIMessage(content=""), # EMPTY CONTENT
            HumanMessage(content="Explain oops in python")
        ]):
            print(chunk.content, end="", flush=True)
    except Exception as e:
        print(f"FAILED: {e}")

asyncio.run(main())
