import urllib.request, json
url = "http://127.0.0.1:8000/api/chat"
data = json.dumps({
    "message": "What is next?",
    "history": [
        {"role": "user", "content": "Explain oops in python"},
        {"role": "ai", "content": "OOP is..."}
    ]
}).encode()
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req) as response:
        print(response.status)
        for line in response:
            print(line.decode().strip())
except Exception as e:
    print("ERROR:", e)
