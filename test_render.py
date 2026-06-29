import requests
import jwt

payload = {"sub": "123", "role": "authenticated", "iss": "supabase"}
token = jwt.encode(payload, "secret", algorithm="HS256")

req_payload = {
    "message": "hello",
    "history": [{"role": "user", "content": "hello"}]
}

resp = requests.post(
    "https://aion-v1-beta.onrender.com/api/chat",
    json=req_payload,
    headers={"Authorization": f"Bearer {token}"}
)

print("STATUS:", resp.status_code)
try:
    print("JSON:", resp.json())
except:
    print("TEXT:", resp.text)
