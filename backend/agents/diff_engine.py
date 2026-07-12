import json
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.base import BaseAgent
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class SemanticDiffEngine(BaseAgent):
    """
    Semantic Diff Engine (yAI IDE OS).
    Replaces full-file generation with targeted, AST-safe diff chunks.
    """
    def __init__(self):
        super().__init__()
        from backend.agents.router import ModelRouter
        # Diff generation requires high reasoning (to match indentation/context)
        self.smart_llm = ModelRouter.get_optimal_llm("DiffEngine", complexity="smart")

    def generate_diff(self, target_file: str, current_code: str, instruction: str) -> list:
        """
        Requests targeted edits from the LLM.
        Returns a list of dicts: [{'start_line': int, 'end_line': int, 'replacement': str}]
        """
        # Add line numbers to the current code so the LLM can reference them
        lines = current_code.split('\n')
        numbered_code = "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines))

        sys_prompt = """ROLE: Semantic Diff Engine
GOAL: Modify the provided file based on the instruction by generating targeted code replacements.
RULES:
1. DO NOT return the entire file.
2. Return ONLY a valid JSON array of objects, where each object represents a contiguous block of lines to replace.
3. Schema: [ { "start_line": number, "end_line": number, "replacement": "new code block as string" } ]
4. The `start_line` and `end_line` are INCLUSIVE and 1-indexed.
5. If you are inserting new code without deleting, set `end_line` equal to `start_line - 1` (insert before start_line).
6. CRITICAL: Your replacement string must include exact whitespace/indentation necessary to fit seamlessly.
7. CRITICAL: Output ONLY the JSON array. No markdown blocks, no prose.
"""

        try:
            response = self.smart_llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"TARGET FILE: {target_file}\nINSTRUCTION:\n{instruction}\n\nCURRENT CODE (Numbered):\n{numbered_code}")
            ])
            
            content = response.content.strip()
            if content.startswith("```json"): content = content[7:]
            elif content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            
            diffs = json.loads(content.strip())
            return diffs
        except Exception as e:
            logger.error(f"[DiffEngine] Failed to generate diff for {target_file}: {e}")
            return []

    def apply_diff(self, current_code: str, diffs: list) -> str:
        """
        Applies a list of diff objects to the code string.
        Modifications are applied from bottom-to-top to avoid shifting line numbers.
        """
        lines = current_code.split('\n')
        
        # Sort diffs by start_line descending
        diffs_sorted = sorted(diffs, key=lambda x: x.get('start_line', 0), reverse=True)
        
        for diff in diffs_sorted:
            start = diff.get('start_line', 1) - 1 # 0-indexed
            end = diff.get('end_line', start) # 0-indexed, inclusive
            replacement = diff.get('replacement', "")
            
            if start < 0: start = 0
            if end >= len(lines): end = len(lines) - 1
            
            replacement_lines = replacement.split('\n')
            
            # If it's an insertion (end_line == start_line - 1)
            if diff.get('end_line') == diff.get('start_line') - 1:
                lines = lines[:start] + replacement_lines + lines[start:]
            else:
                lines = lines[:start] + replacement_lines + lines[end+1:]
                
        return "\n".join(lines)
