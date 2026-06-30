with open('backend/memory/chroma_client.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_init = """    def __init__(self, db_path="./chroma_db"):
        # Initialize a local ChromaDB instance
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Use ChromaDB's default local sentence-transformer model for embeddings
        # This runs 100% locally and does not require an API key!
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # Get or create our 'blueprints' collection
        self.collection = self.client.get_or_create_collection(
            name="blueprints",
            embedding_function=self.embedding_fn
        )
        
        # Get or create semantic cache collection
        self.cache_collection = self.client.get_or_create_collection(
            name="semantic_cache",
            embedding_function=self.embedding_fn
        )"""

cache_methods = """
    def get_cache(self, query: str, threshold: float = 0.3):
        \"\"\"Searches for a semantically similar query in the cache.\"\"\"
        try:
            if self.cache_collection.count() == 0:
                return None
            
            results = self.cache_collection.query(
                query_texts=[query],
                n_results=1
            )
            
            if results and results["documents"] and len(results["documents"][0]) > 0:
                # results["distances"] contains the L2 distance. Smaller is closer.
                distance = results["distances"][0][0] if "distances" in results and results["distances"] else 0
                if distance < threshold:
                    print(f"⚡ [Semantic Cache Hit] Distance: {distance:.4f} for query: {query}")
                    return results["documents"][0][0]
                else:
                    print(f"🐌 [Semantic Cache Miss] Closest distance: {distance:.4f}")
            return None
        except Exception as e:
            print(f"   -> [WARNING] Semantic Cache search failed: {e}")
            return None

    def set_cache(self, query: str, response: str):
        \"\"\"Saves a query-response pair to the semantic cache.\"\"\"
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
"""

content = content.replace("    def __init__(self, db_path=\"./chroma_db\"):", "###REPLACE_INIT###")
# Extract everything up to the first def after __init__
init_block_end = content.find("    def store_blueprint")
before_init = content[:content.find("###REPLACE_INIT###")]
after_init = content[init_block_end:]

content = before_init + new_init + "\n\n" + after_init + cache_methods

with open('backend/memory/chroma_client.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("chroma_client.py updated successfully.")
