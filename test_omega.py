import asyncio
import os
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.models.omega import OmegaModel

async def test_omega():
    print("Testing Omega Meta-Model...")
    
    # We will use dummy models if real ones aren't available, but if env vars are present we'll use them.
    if os.getenv("OPENAI_API_KEY"):
        fast_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)
        smart_llm = ChatOpenAI(model="gpt-4o", temperature=0.5)
    else:
        # Fallback for testing logic (won't actually connect)
        class DummyWorker:
            def __init__(self, name):
                self.name = name
            async def ainvoke(self, input, *args, **kwargs):
                class DummyResponse:
                    content = f"Response from {self.name}"
                await asyncio.sleep(1)
                return DummyResponse()
                
        fast_llm = DummyWorker("Fast")
        smart_llm = DummyWorker("Smart")

    omega = OmegaModel(workers=[fast_llm, smart_llm], synthesizer=smart_llm)
    
    try:
        response = await omega.ainvoke("What is the capital of France?")
        print(f"Omega Synthesized Response:\n{response.content if hasattr(response, 'content') else response}")
        print("\nOmega test passed!")
    except Exception as e:
        print(f"Omega test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_omega())
