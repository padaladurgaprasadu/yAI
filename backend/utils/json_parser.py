import json
import re

def parse_json_robustly(content: str) -> dict:
    \"\"\"
    Tries multiple strategies to robustly parse JSON from an LLM response,
    including markdown stripping, nested bracket balancing, and greedy substring extraction.
    \"\"\"
    content_str = content.strip()
    
    # Strategy 1: Direct JSON parsing
    try:
        return json.loads(content_str)
    except json.JSONDecodeError:
        pass
        
    # Strategy 2: Remove markdown code block wrappers
    cleaned = content_str
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned.strip())
        except json.JSONDecodeError:
            pass

    # Strategy 3: Balanced bracket parsing (extracts the first balanced JSON object)
    try:
        first_brace = content_str.find('{')
        if first_brace != -1:
            brace_count = 0
            in_quote = False
            escape = False
            for idx in range(first_brace, len(content_str)):
                char = content_str[idx]
                if char == '"' and not escape:
                    in_quote = not in_quote
                elif char == '\\' and not escape:
                    escape = True
                    continue
                
                if not in_quote:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            candidate = content_str[first_brace:idx+1]
                            try:
                                return json.loads(candidate)
                            except json.JSONDecodeError:
                                break
                escape = False
    except Exception:
        pass

    # Strategy 4: Find first '{' and last '}' (greedy matching fallback)
    try:
        first_brace = content_str.find('{')
        last_brace = content_str.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidate = content_str[first_brace:last_brace+1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
    except Exception:
        pass

    # If all else fails, attempt a direct load to throw the standard JSONDecodeError
    return json.loads(content_str)
