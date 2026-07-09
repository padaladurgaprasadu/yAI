import urllib.request, json, os, sys
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("NVIDIA_API_KEY")
if not api_key:
    sys.exit("No NVIDIA_API_KEY")

url = "https://integrate.api.nvidia.com/v1/chat/completions"
data = json.dumps({
    "model": "meta/llama-3.1-8b-instruct",
    "messages": [{"role": "user", "content": "Count to 10 slowly"}],
    "stream": True
}).encode()
req = urllib.request.Request(url, data=data, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})

print("Sending request...")
try:
    with urllib.request.urlopen(req) as response:
        for line in response:
            print(line.decode().strip(), flush=True)
except Exception as e:
    print(e)
