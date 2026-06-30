with open('backend/api_real.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_logic = """
                # If we detect the build tag, we stop streaming to the user and buffer it
                if "[BUILD]" in buffer:
                    is_build = True
                    continue
                
                # If we're sure it's not a build command, stream the chunk
                if not is_build and len(buffer) > 10 and "[BUILD]" not in buffer:
                    if not flushed_initial:
                        # Yield the entire buffer accumulated so far
                        escaped_chunk = json.dumps({"type": "chat", "token": buffer})
                        yield f"data: {escaped_chunk}\\n\\n"
                        flushed_initial = True
                    else:
                        # yield normal text in SSE format
                        escaped_chunk = json.dumps({"type": "chat", "token": text_chunk})
                        yield f"data: {escaped_chunk}\\n\\n"
"""

new_logic = """
                # Zero TTFT Prefix Divergence Logic
                if not is_build:
                    if "[BUILD]" in buffer:
                        is_build = True
                        continue
                    
                    # If it starts with a subset of "[BUILD]", we MUST wait.
                    # e.g., buffer = "[", or "[B", or "[BU"
                    if len(buffer) > 0 and "[BUILD]".startswith(buffer):
                        continue
                        
                    # If we reach here, it either doesn't start with "[" at all,
                    # OR it started with "[" but diverged (e.g., "[Here...").
                    # It is safe to stream immediately!
                    if not flushed_initial:
                        escaped_chunk = json.dumps({"type": "chat", "token": buffer})
                        yield f"data: {escaped_chunk}\\n\\n"
                        flushed_initial = True
                    else:
                        escaped_chunk = json.dumps({"type": "chat", "token": text_chunk})
                        yield f"data: {escaped_chunk}\\n\\n"
"""

content = content.replace(old_logic.strip(), new_logic.strip())

with open('backend/api_real.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Zero TTFT logic implemented successfully.")
