import urllib.request, json, time, sys

url = "http://127.0.0.1:8000/api/chat"
data = json.dumps({
    "message": "Write a 5 sentence story about a brave knight. Do it slowly.",
    "history": []
}).encode()
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

print(f"[{time.time()}] Sending request...")
try:
    with urllib.request.urlopen(req) as response:
        print(f"[{time.time()}] Headers received!")
        for line in response:
            print(f"[{time.time()}] Chunk: {line.decode().strip()}", flush=True)
except Exception as e:
    print(e)
