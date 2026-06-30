with open('backend/api_real.py', 'r', encoding='utf-8') as f:
    content = f.read()

cache_hit_logic = """
    async def event_generator():
        try:
            is_build = False
            buffer = ""
            flushed_initial = False
            
            # === SEMANTIC CACHE HIT CHECK ===
            if len(request_data.history) == 0 and not request_data.image:
                try:
                    from backend.memory.chroma_client import ChromaClient
                    cache_client = ChromaClient()
                    cached_response = cache_client.get_cache(sanitized_message)
                    if cached_response:
                        import json
                        escaped_chunk = json.dumps({"type": "chat", "token": cached_response})
                        yield f"data: {escaped_chunk}\\n\\n"
                        return
                except Exception as e:
                    print(f"[Semantic Cache] Error checking cache: {e}")
            # ================================

            # Stream the response"""

content = content.replace("""
    async def event_generator():
        try:
            is_build = False
            buffer = ""
            flushed_initial = False
            # Stream the response""", cache_hit_logic.strip())

cache_set_logic = """
            # If it is a build, send the final parsed JSON
            if is_build:
                try:
                    json_str = buffer.split("[BUILD]")[1].strip()
                    parsed = json.loads(json_str, strict=False)
                    escaped_chunk = json.dumps({"type": "build", "data": parsed})
                    yield f"data: {escaped_chunk}\\n\\n"
                except Exception as e:
                    escaped_chunk = json.dumps({"type": "chat", "token": "\\n\\n(Error parsing build parameters. Please try again.)"})
                    yield f"data: {escaped_chunk}\\n\\n"
            
            # === SEMANTIC CACHE SET ===
            if len(request_data.history) == 0 and not request_data.image and not is_build:
                try:
                    from backend.memory.chroma_client import ChromaClient
                    import asyncio
                    def save_cache():
                        ChromaClient().set_cache(sanitized_message, buffer)
                    asyncio.create_task(asyncio.to_thread(save_cache))
                except Exception as e:
                    print(f"[Semantic Cache] Error setting cache: {e}")
            # ==========================
"""

# Finding the exact block to replace for cache setting
old_build_block = """
            # If it is a build, send the final parsed JSON
            if is_build:
                try:
                    json_str = buffer.split("[BUILD]")[1].strip()
                    parsed = json.loads(json_str, strict=False)
                    escaped_chunk = json.dumps({"type": "build", "data": parsed})
                    yield f"data: {escaped_chunk}\\n\\n"
                except Exception as e:
                    escaped_chunk = json.dumps({"type": "chat", "token": "\\n\\n(Error parsing build parameters. Please try again.)"})
                    yield f"data: {escaped_chunk}\\n\\n"
"""

content = content.replace(old_build_block.strip(), cache_set_logic.strip())

with open('backend/api_real.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("api_real.py updated for caching.")
