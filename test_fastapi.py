from fastapi.testclient import TestClient
from backend.api_real import app, verify_token

# Override verify_token dependency for testing
app.dependency_overrides[verify_token] = lambda: {"sub": "123", "role": "authenticated"}

client = TestClient(app)

payload = {
    "message": "hello",
    "history": [{"role": "user", "content": "hello"}]
}

response = client.post("/api/chat", json=payload, headers={"Authorization": "Bearer test"})
print("STATUS:", response.status_code)
print("RESPONSE:", response.text)
