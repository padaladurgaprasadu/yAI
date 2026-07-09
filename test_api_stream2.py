import urllib.request, json
url = "http://127.0.0.1:8000/api/chat"
data = json.dumps({"message": "hi", "history": []}).encode()
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as response:
    print(response.headers)
