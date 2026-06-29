with open('backend/api_real.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

out_lines = []
skip = False
for line in lines:
    if line.strip() == "# === AI RESOURCE RECOMMENDER (RAG) ===":
        skip = True
    if not skip:
        out_lines.append(line)
    if skip and line.strip() == "# =====================================":
        skip = False

with open('backend/api_real.py', 'w', encoding='utf-8') as f:
    f.writelines(out_lines)
print("RAG block removed successfully.")
