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
    Searches Wikipedia for hand-curated page images of real-world places and people.
    Falls back to Wikimedia Commons if no encyclopedia entry matches.
    Returns a single URL string if count=1, or a list of URL strings if count>1.
    """
    if not query:
        return None
        
    image_urls = []
    
    # STEP 1: Try Wikipedia PageImages First (Curated by editors, much higher quality)
    try:
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(query)}&prop=pageimages&pithumbsize=800&format=json"
        req = urllib.request.Request(wiki_url, headers={'User-Agent': 'AiON/1.0 (contact@aion.ai)'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
        
        pages = data.get('query', {}).get('pages', {})
        for page_id, page in pages.items():
            if 'thumbnail' in page:
                image_urls.append(page['thumbnail']['source'])
                if len(image_urls) >= count:
                    break
    except Exception as e:
        logger.error(f"Visuals: Wikipedia PageImages failed for {query} - {e}")
        
    if image_urls:
        if count == 1:
            return image_urls[0]
        return image_urls

    # STEP 2: Fallback to Wikimedia Commons Search if Wikipedia has no pages
    try:
        url = f"https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&srnamespace=6&utf8=&format=json"
        req = urllib.request.Request(url, headers={'User-Agent': 'AiON/1.0 (contact@aion.ai)'})
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
        if not data.get('query', {}).get('search'):
            return None
            
        results = data['query']['search'][:max(count*2, 10)]
        
        # Sort to deprioritize inscriptions or texts if possible
        titles = [item['title'] for item in results]
        good_titles = [t for t in titles if 'inscription' not in t.lower() and 'text' not in t.lower() and not t.lower().endswith('.pdf')]
        bad_titles = [t for t in titles if t not in good_titles]
        sorted_titles = good_titles + bad_titles
        
        for title in sorted_titles:
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
                    if len(image_urls) >= count:
                        break
        
        if count == 1:
            return image_urls[0] if image_urls else None
        return image_urls
        
    except Exception as e:
        logger.error(f"Visuals: Commons fallback failed for {query} - {e}")
        return None
