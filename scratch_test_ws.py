import asyncio, websockets, json
async def test():
    async with websockets.connect("ws://localhost:8000/api/ws/generate", ping_interval=None) as ws:
        payload = {
            "project_id": "test_project_123",
            "goal": "build a simple express backend with one route",
            "blueprint": {"tech_stack": [], "file_structure": [], "blueprint_notes": ""},
            "agent_role": "Fullstack Web Developer",
            "execution_mode": "autonomous",
            "code_files": {}
        }
        await ws.send(json.dumps(payload))
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            print(f"[{data.get('type')}] {str(data)[:150]}")
            if data.get("type") in ["error", "done", "complete"]:
                break
asyncio.run(test())
