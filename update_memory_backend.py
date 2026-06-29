with open('backend/api_real.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update ChatRequest
if "memory: typing.Optional[str] = None" not in content:
    content = content.replace(
        "image: typing.Optional[str] = None",
        "image: typing.Optional[str] = None\n    memory: typing.Optional[str] = None"
    )

# Add USER MEMORY MODULE to the system prompt
# We will append it right before the """ closing the system_prompt block.
memory_directive = """
[LONG-TERM MEMORY DIRECTIVE]: If the user explicitly shares a new personal fact about themselves (e.g., their name, profession, goals, skill level, or preferences), you MUST secretly append exactly `[MEMORY_ADD] <fact>` to the VERY END of your response. 
Example: `[MEMORY_ADD] User is a physics student.`

[USER'S PAST MEMORY]:
{USER_MEMORY}
"""

if "[LONG-TERM MEMORY DIRECTIVE]" not in content:
    content = content.replace(
        'agent_role": "Select the best role: Fullstack Web Developer, Machine Learning Engineer, Deep Learning Researcher, Data Scientist, Data Analyst, AI Systems Architect"}\n"""',
        f'agent_role": "Select the best role: Fullstack Web Developer, Machine Learning Engineer, Deep Learning Researcher, Data Scientist, Data Analyst, AI Systems Architect"}}\n{memory_directive}"""'
    )

# Inject memory into the system prompt when processing the request
injection_code = """
    # Inject memory if available
    user_mem = request_data.memory if request_data.memory else "No past memory recorded yet."
    system_prompt = system_prompt.replace("{USER_MEMORY}", user_mem)

    messages = [SystemMessage(content=system_prompt)]
"""

if "user_mem = request_data.memory" not in content:
    content = content.replace("    messages = [SystemMessage(content=system_prompt)]", injection_code.strip())

with open('backend/api_real.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Backend memory updated successfully.")
