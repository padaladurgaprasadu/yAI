import urllib.parse
from backend.utils.logger import get_logger

logger = get_logger("AiON_Visuals")

def get_wiki_image(query: str) -> str:
    """
    Upgraded Visual Intelligence: Uses Pollinations Generative AI to create 
    the absolute 'best, latest, recent' image perfectly matching the query,
    rather than scraping outdated thumbnails from Wikipedia.
    """
    if not query:
        return None
        
    try:
        # Enhance the query for better visual generation
        enhanced_query = f"{query} high quality, modern, photorealistic, best, latest"
        encoded_query = urllib.parse.quote(enhanced_query)
        
        # We return the direct URL which the frontend will render in an <img> tag.
        # Pollinations dynamically generates and caches the image.
        img_url = f"https://image.pollinations.ai/prompt/{encoded_query}?width=800&height=600&nologo=true"
        
        logger.info(f"Visuals: Generated AI Image URL for query: {query}")
        return img_url
        
    except Exception as e:
        logger.error(f"Visuals: Failed to generate AI image for {query} - {e}")
        return None
