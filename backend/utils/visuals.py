import urllib.parse
import urllib.request
import json
from backend.utils.logger import get_logger

logger = get_logger("AiON_Visuals")

def get_generative_image(query: str) -> str:
    """
    Uses Pollinations Generative AI to create the absolute 'best, latest, recent' 
    image for abstract concepts, UI designs, and digital art.
    """
    if not query:
        return None
    try:
        enhanced_query = f"{query} high quality, modern, photorealistic, best, latest"
        encoded_query = urllib.parse.quote(enhanced_query)
        img_url = f"https://image.pollinations.ai/prompt/{encoded_query}?width=800&height=600&nologo=true"
        logger.info(f"Visuals: Generated AI Image URL for query: {query}")
        return img_url
    except Exception as e:
        logger.error(f"Visuals: Failed to generate AI image for {query} - {e}")
        return None

def get_real_world_image(query: str, count: int = 1):
    """
    Searches Wikimedia Commons for highly accurate, real-world photographs
    of actual places (e.g. Vijayawada, Eiffel Tower) or real people.
    Returns a single URL string if count=1, or a list of URL strings if count>1.
    """
    if not query:
        return None
    try:
        # Search Wikimedia Commons for real photos
        url = f"https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&srnamespace=6&utf8=&format=json"
        req = urllib.request.Request(url, headers={'User-Agent': 'AiON/1.0 (contact@aion.ai)'})
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
        if not data.get('query', {}).get('search'):
            return None
            
        results = data['query']['search'][:count]
        image_urls = []
        
        for item in results:
            title = item['title']
            
            # Fetch the direct image URL for the found file
            img_url_req = f"https://commons.wikimedia.org/w/api.php?action=query&prop=imageinfo&iiprop=url&titles={urllib.parse.quote(title)}&format=json"
            req2 = urllib.request.Request(img_url_req, headers={'User-Agent': 'AiON/1.0 (contact@aion.ai)'})
            
            with urllib.request.urlopen(req2) as response2:
                img_data = json.loads(response2.read().decode())
                
            pages = img_data.get('query', {}).get('pages', {})
            if pages:
                page_id = list(pages.keys())[0]
                if 'imageinfo' in pages[page_id]:
                    image_urls.append(pages[page_id]['imageinfo'][0]['url'])
        
        if count == 1:
            return image_urls[0] if image_urls else None
        return image_urls
        
    except Exception as e:
        logger.error(f"Visuals: Failed to fetch real-world image for {query} - {e}")
        
    # Fallback to Wikipedia PageImages if Commons fails or is empty
    try:
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(query)}&prop=pageimages&pithumbsize=800&format=json"
        req = urllib.request.Request(wiki_url, headers={'User-Agent': 'AiON/1.0 (contact@aion.ai)'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
        
        pages = data.get('query', {}).get('pages', {})
        wiki_urls = []
        for page_id, page in pages.items():
            if 'thumbnail' in page:
                wiki_urls.append(page['thumbnail']['source'])
                if len(wiki_urls) >= count:
                    break
                    
        if count == 1:
            return wiki_urls[0] if wiki_urls else None
        return wiki_urls
    except Exception as e2:
        logger.error(f"Visuals: Wikipedia fallback failed for {query} - {e2}")
        return None
