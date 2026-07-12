import json

content = """
**Router Agent Output**

```json
{
  "primary_intent": "Website Development",
  "complexity": "Large",
  "requires_web_search": false,
  "requires_repository_analysis": false,
  "requires_templates": true,
  "requires_image_search": false,
  "recommended_agents": ["Planner", "Architect"],
  "model_tier": "Reasoning",
  "entity_detection": {
    "requires_visuals": false,
    "search_query": null
  }
}
```

**Planner Agent Output**
{
  "workflow": []
}
"""

start = content.find('{')
if start != -1:
    depth = 0
    for i in range(start, len(content)):
        if content[i] == '{': depth += 1
        elif content[i] == '}': depth -= 1
        if depth == 0:
            content = content[start:i+1]
            break

content = content.replace("{{", "{").replace("}}", "}")
print("EXTRACTED:")
print(repr(content))

try:
    print(json.loads(content))
except Exception as e:
    print("ERROR:", e)
