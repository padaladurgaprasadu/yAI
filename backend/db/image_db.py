import os
import json
import logging
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

class MultimodalVisualDB:
    """
    Visual Retrieval Engine
    Uses ChromaDB to store multimodal embeddings (Images and Text) into the same vector space.
    """
    def __init__(self):
        try:
            self.client = chromadb.PersistentClient(path=os.path.join(os.getcwd(), "chroma_db", "visuals"))
            self.collection = self.client.get_or_create_collection(name="image_embeddings")
            
            # Lazy load CLIP model to save memory until first use
            self.clip_model = None
            logger.info("[VisualDB] Initialized ChromaDB for Multimodal Visual Retrieval.")
        except Exception as e:
            logger.error(f"[VisualDB] Failed to initialize ChromaDB: {e}")
            self.collection = None

    def _get_model(self):
        if self.clip_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("[VisualDB] Loading CLIP model (clip-ViT-B-32)...")
                self.clip_model = SentenceTransformer('clip-ViT-B-32')
            except ImportError:
                logger.error("[VisualDB] sentence-transformers not installed. Cannot generate embeddings.")
        return self.clip_model

    def add_image(self, image_id: str, image_url: str, metadata: Dict[str, Any] = None):
        """Adds an image to the vector index using its URL/metadata."""
        if not self.collection:
            return
            
        model = self._get_model()
        if not model:
            return
            
        # For phase 1, we embed the descriptive text or image URL.
        # In a full multimodal setup, we would load the PIL image and embed it.
        # `clip_model.encode(Image.open(...))`
        # We will fallback to metadata embedding if URL fetch is too slow.
        text_to_embed = f"Image: {image_url} " + json.dumps(metadata or {})
        try:
            embedding = model.encode(text_to_embed).tolist()
            self.collection.add(
                embeddings=[embedding],
                ids=[image_id],
                metadatas=[metadata or {"url": image_url}]
            )
            logger.info(f"[VisualDB] Indexed image {image_id}")
        except Exception as e:
            logger.error(f"[VisualDB] Failed to index image {image_id}: {e}")

    def search_similar(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Finds images matching the semantic query in the vector space."""
        if not self.collection:
            return []
            
        model = self._get_model()
        if not model:
            return []
            
        try:
            query_embedding = model.encode(query).tolist()
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            matched_images = []
            for i, meta in enumerate(results.get("metadatas", [[]])[0]):
                matched_images.append({
                    "id": results["ids"][0][i],
                    "metadata": meta,
                    "distance": results["distances"][0][i]
                })
            return matched_images
        except Exception as e:
            logger.error(f"[VisualDB] Search failed: {e}")
            return []

# Global instance
visual_db = MultimodalVisualDB()
