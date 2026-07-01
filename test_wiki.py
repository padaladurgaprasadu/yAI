from backend.utils.visuals import get_wiki_image
import asyncio

async def test():
    print("Testing Adiyogi Statue:", await asyncio.to_thread(get_wiki_image, "Adiyogi Statue"))
    print("Testing Eiffel Tower:", await asyncio.to_thread(get_wiki_image, "Eiffel Tower"))

if __name__ == "__main__":
    asyncio.run(test())
