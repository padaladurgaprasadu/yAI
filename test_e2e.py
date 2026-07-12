import asyncio
import websockets
import json
import uuid

async def test_workflow():
    uri = "ws://localhost:8000/api/ws/generate"
    project_id = f"test-{uuid.uuid4().hex[:8]}"
    log_file = open("test_e2e_output.txt", "w", encoding="utf-8")
    
    def log(msg):
        try:
            print(msg, flush=True)
        except Exception:
            pass
        log_file.write(msg + "\n")
        log_file.flush()
        
    log(f"Connecting to {uri} with project {project_id}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            log("Connected! Sending generate request...")
            req = {
                "project_id": project_id,
                "goal": "Build a very simple hello world python app.",
                "agent_role": "Python Developer",
                "execution_mode": "Lightning",
                "blueprint": {"tech_stack": ["Python"], "file_structure": ["app.py"]},
                "code_files": {}
            }
            await websocket.send(json.dumps(req))
            
            while True:
                try:
                    response_raw = await websocket.recv()
                    response = json.loads(response_raw)
                    msg_type = response.get("type")
                    
                    if msg_type == "progress":
                        log(f"[PROGRESS] {response.get('node', 'unknown')}: {response.get('message')}")
                    elif msg_type == "code_complete":
                        log(f"[CODE_COMPLETE] Files generated: {list(response.get('code_files', {}).keys())}")
                    elif msg_type == "timeline":
                        log(f"[TIMELINE] {response.get('title')} - {response.get('status')}")
                    elif msg_type == "PREVIEW_READY":
                        log(f"[PREVIEW] URL: {response.get('url')}")
                    elif msg_type == "complete":
                        log(f"[COMPLETE] Final logs: {len(response.get('execution_logs', []))} log entries.")
                        break
                    elif msg_type == "error":
                        log(f"[ERROR] {response.get('message')}")
                        break
                    else:
                        log(f"[{msg_type.upper()}] {str(response)[:100]}...")
                except websockets.exceptions.ConnectionClosed:
                    log("Connection closed.")
                    break
    except Exception as e:
        log(f"Failed to connect or test: {e}")
    finally:
        log_file.close()

if __name__ == "__main__":
    asyncio.run(test_workflow())
