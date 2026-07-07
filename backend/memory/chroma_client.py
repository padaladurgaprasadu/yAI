import chromadb
from chromadb.utils import embedding_functions

class ChromaClient:
    """
    Manages the Vector Database (ChromaDB) for Semantic Memory.
    It stores projects and their architectures so the AI can search for them by 'meaning'.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ChromaClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path="./chroma_db"):
        if self._initialized:
            return
            # Initialize a local ChromaDB instance
        try:
            self.client = chromadb.PersistentClient(path=db_path)
        except Exception as e:
            print(f"[ChromaDB] Persistent DB failed (likely read-only FS). Falling back to Ephemeral: {e}")
            self.client = chromadb.EphemeralClient()
            
        # Use Google Gemini Embeddings for speed (100x faster than local ONNX model on Render CPU)
        import os
        gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        nvidia_api_key = os.getenv("NVIDIA_API_KEY")
        
        if gemini_api_key:
            from chromadb.utils.embedding_functions import GoogleGenerativeAiEmbeddingFunction
            self.embedding_fn = GoogleGenerativeAiEmbeddingFunction(api_key=gemini_api_key)
            print("[ChromaDB] Using Google Gemini Embeddings.")
        elif openai_api_key:
            from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
            self.embedding_fn = OpenAIEmbeddingFunction(api_key=openai_api_key)
            print("[ChromaDB] Using OpenAI Embeddings.")
        elif nvidia_api_key:
            # Custom NVIDIA embedding function for Chroma
            from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
            import requests
            
            class NvidiaEmbeddingFunction(EmbeddingFunction):
                def __init__(self, api_key: str):
                    self.api_key = api_key
                    self.url = "https://integrate.api.nvidia.com/v1/embeddings"
                    
                def __call__(self, input: Documents) -> Embeddings:
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "input": input,
                        "model": "nvidia/nv-embedqa-e5-v5",
                        "encoding_format": "float",
                        "input_type": "query"
                    }
                    try:
                        res = requests.post(self.url, json=payload, headers=headers)
                        res.raise_for_status()
                        data = res.json()
                        return [d["embedding"] for d in data["data"]]
                    except Exception as e:
                        print(f"[ChromaDB] NVIDIA Embedding failed: {e}")
                        # Return zero vectors as fallback so it doesn't crash
                        return [[0.0] * 1024 for _ in input]

            self.embedding_fn = NvidiaEmbeddingFunction(api_key=nvidia_api_key)
            print("[ChromaDB] Using NVIDIA Embeddings.")
        else:
            # FATAL: Local embedding causes OOM on Render. Use dummy to prevent crash.
            from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
            class DummyEmbeddingFunction(EmbeddingFunction):
                def __call__(self, input: Documents) -> Embeddings:
                    return [[0.0] * 384 for _ in input]
            self.embedding_fn = DummyEmbeddingFunction()
            print("[ChromaDB] WARNING: No API keys found. Using Dummy Embeddings to prevent OOM crash.")
        
        # Helper to safely get or create collection to avoid ValueError on embedding function conflict
        def safe_get_or_create(name):
            try:
                return self.client.get_collection(name=name)
            except Exception:
                return self.client.create_collection(name=name, embedding_function=self.embedding_fn)
                
        # Get or create our 'blueprints' collection
        self.collection = safe_get_or_create("blueprints")
        
        # Get or create semantic cache collection
        self.cache_collection = safe_get_or_create("semantic_cache")
        
        # Get or create user memory collection
        self.memory_collection = safe_get_or_create("user_memory")
        
        self._initialized = True

    def store_blueprint(self, project_id, goal, blueprint):
        """Stores the project's goal and resulting blueprint into the vector database."""
        # We embed the 'goal' so we can search by goal later
        document = f"Goal: {goal}\nBlueprint: {blueprint}"
        
        # We use upsert so it overwrites if it already exists
        self.collection.upsert(
            documents=[document],
            metadatas=[{"project_id": project_id, "goal": goal}],
            ids=[project_id]
        )

    def find_similar_projects(self, new_goal, n_results=2):
        """Searches the database for past projects similar to the new goal."""
        try:
            # Check how many items are in the DB so we don't request more than exists
            count = self.collection.count()
            if count == 0:
                return []
                
            n = min(n_results, count)
            
            results = self.collection.query(
                query_texts=[new_goal],
                n_results=n
            )
            
            # Extract and return the documents if any exist
            if results and results["documents"] and len(results["documents"][0]) > 0:
                return results["documents"][0]
            return []
        except Exception as e:
            print(f"   -> [WARNING] ChromaDB search failed: {e}")
            return []

    def get_cache(self, query: str, threshold: float = 0.3):
        """Searches for a semantically similar query in the cache."""
        try:
            if self.cache_collection.count() == 0:
                return None, 0
            
            results = self.cache_collection.query(
                query_texts=[query],
                n_results=1
            )
            
            if results and results["documents"] and len(results["documents"][0]) > 0:
                distance = results["distances"][0][0] if "distances" in results and results["distances"] else 0
                if distance < threshold:
                    return results["documents"][0][0], distance
            return None, 0
        except Exception as e:
            return None, 0

    def set_cache(self, query: str, response: str):
        """Saves a query-response pair to the semantic cache."""
        import uuid
        try:
            cache_id = f"cache-{str(uuid.uuid4())[:8]}"
            self.cache_collection.add(
                documents=[response],
                metadatas=[{"original_query": query}],
                ids=[cache_id]
            )
        except Exception as e:
            print(f"   -> [WARNING] Failed to set Semantic Cache: {e}")

    def store_memory(self, user_id: str, fact: str):
        """Saves a personal fact about the user into their memory collection."""
        import uuid
        try:
            mem_id = f"mem-{str(uuid.uuid4())[:8]}"
            self.memory_collection.add(
                documents=[fact],
                metadatas=[{"user_id": user_id}],
                ids=[mem_id]
            )
            print(f"[MEMORY DB] Stored new fact for {user_id}: {fact}")
        except Exception as e:
            print(f"   -> [WARNING] Failed to store Memory: {e}")

    def retrieve_memory(self, user_id: str, query: str, n_results: int = 3) -> str:
        """Retrieves top semantically relevant facts about the user based on their query."""
        try:
            # We filter by user_id to ensure strict data separation!
            count = self.memory_collection.count()
            if count == 0:
                return ""
            
            n = min(n_results, count)
            results = self.memory_collection.query(
                query_texts=[query],
                n_results=n,
                where={"user_id": user_id}
            )
            
            if results and results["documents"] and len(results["documents"][0]) > 0:
                facts = results["documents"][0]
                return "\n".join([f"- {fact}" for fact in facts])
            return ""
        except Exception as e:
            print(f"   -> [WARNING] Failed to retrieve Memory: {e}")
            return ""
