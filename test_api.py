import asyncio
import httpx
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8', line_buffering=True)

async def test_chat():
    url = "http://localhost:8000/api/chat"
    payload = {
        "message": "Tell me about the Adiyogi Statue",
        "history": []
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            async with client.stream("POST", url, json=payload) as response:
                print(f"Status: {response.status_code}", flush=True)
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("type") in ["status", "visual"]:
                            print(json.dumps(data), flush=True)
                        elif data.get("type") == "chat":
                            pass
                print("\nStream finished.", flush=True)
        except Exception as e:
            print("Request failed:", e, flush=True)

if __name__ == "__main__":
    asyncio.run(test_chat())
