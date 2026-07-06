import asyncio
from sandbox.manager import global_sandbox_manager

async def test():
    files = {
        "server/app.js": "const http = require('http');\nconst server = http.createServer((req, res) => {\n  res.writeHead(200, {'Content-Type': 'text/plain'});\n  res.end('Hello AiON Sandbox Engine!');\n});\nserver.listen(process.env.PORT, () => console.log('Server running!'));",
        "package.json": "{\"name\": \"test-app\", \"scripts\": {\"dev\": \"node server/app.js\"}}"
    }
    
    info = await global_sandbox_manager.start_sandbox("test_proj_1", files)
    print(f"Sandbox started: {info}")
    
    # Wait a bit
    await asyncio.sleep(2)
    
    print("Logs:")
    async def print_logs():
        async for log in global_sandbox_manager.stream_logs("test_proj_1"):
            print(log)
            
    # Run log reader for 5 seconds
    task = asyncio.create_task(print_logs())
    await asyncio.sleep(5)
    
    global_sandbox_manager.stop_sandbox("test_proj_1")
    task.cancel()
    print("Done")

if __name__ == "__main__":
    asyncio.run(test())
