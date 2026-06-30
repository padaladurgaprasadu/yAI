import requests
import json
import sseclient

def test_chat():
    url = "http://localhost:5000/api/chat"
    payload = {
        "message": "Hi, who are you?",
        "history": [],
        "memory": ""
    }
    
    print(f"Sending POST to {url}...")
    try:
        response = requests.post(
            url, 
            json=payload, 
            stream=True, 
            headers={'Authorization': 'Bearer mock-token-for-local-dev'}
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print("Response:", response.text)
            return

        try:
            client = sseclient.SSEClient(response)
            print("Receiving stream...")
            for event in client.events():
                try:
                    data = json.loads(event.data)
                    if 'token' in data:
                        print(data['token'], end='', flush=True)
                    else:
                        print(f"\n[Event]: {data}")
                except Exception as e:
                    print(f"Error parsing event: {event.data} -> {e}")
                    
            print("\n\nStream complete.")
        except Exception as e:
            print(f"Failed to parse SSE. Raw text:")
            print(response.text)
        
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_chat()
