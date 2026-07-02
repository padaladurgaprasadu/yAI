import asyncio
from memory.chroma_client import ChromaClient

def clear_cache():
    try:
        client = ChromaClient()
        # ChromaDB doesn't easily let you delete everything, but we can delete the collection or re-init it.
        try:
            client.client.delete_collection("aion_semantic_cache")
            print("Semantic cache collection deleted successfully.")
        except Exception as e:
            print(f"Error deleting collection: {e}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clear_cache()
