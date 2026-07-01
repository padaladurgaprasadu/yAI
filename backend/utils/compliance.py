import re

class StreamingComplianceEngine:
    """
    Middleware that wraps an LLM token stream to forcefully enforce formatting rules in real-time,
    without sacrificing TTFT (Time-To-First-Token) by waiting for the full response.
    """
    def __init__(self, stream):
        self.stream = stream
        self.in_code_block = False
        self.sentence_count = 0
        self.current_paragraph = ""

    async def process(self):
        """
        Yields chunks while monitoring sentence lengths.
        If a paragraph reaches 2 sentences, it automatically injects \n\n to force a break.
        """
        async for chunk in self.stream:
            text_chunk = chunk.content
            if isinstance(text_chunk, list):
                text_chunk = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in text_chunk)
            
            # Check for code block toggles
            if "```" in text_chunk:
                # Count how many times ``` appears in this chunk
                toggles = text_chunk.count("```")
                for _ in range(toggles):
                    self.in_code_block = not self.in_code_block
                    
            if "<mermaid>" in text_chunk:
                self.in_code_block = True
            if "</mermaid>" in text_chunk:
                self.in_code_block = False

            # If we are in a code block or list item/table, we don't force break
            # Heuristic: lists start with - or *, tables use |
            # We will just yield raw
            
            processed_chunk = ""
            for char in text_chunk:
                self.current_paragraph += char
                processed_chunk += char
                
                # Reset on paragraph break
                if self.current_paragraph.endswith("\n\n") or self.current_paragraph.endswith("\r\n\r\n"):
                    self.sentence_count = 0
                    self.current_paragraph = ""
                    continue
                    
                # Check for sentence end (heuristic: dot/bang/question followed by space or newline)
                if not self.in_code_block:
                    # Detect end of sentence
                    is_sentence_end = False
                    if len(self.current_paragraph) >= 2:
                        last_two = self.current_paragraph[-2:]
                        if last_two in [". ", "! ", "? ", ".\n", "!\n", "?\n"]:
                            is_sentence_end = True
                        elif len(self.current_paragraph) >= 3:
                            last_three = self.current_paragraph[-3:]
                            if last_three in ['. "\n', '! "\n', '? "\n', '." ', '!" ', '?" ']:
                                is_sentence_end = True
                    
                    if is_sentence_end:
                        # Avoid counting abbreviations like "Mr. " or "e.g. "
                        if len(self.current_paragraph) > 4 and not re.search(r'\b(?:Mr|Mrs|Ms|Dr|vs|e\.g|i\.e|etc)\.\s*$', self.current_paragraph, flags=re.IGNORECASE):
                            self.sentence_count += 1
                            
                            # Force break if we hit 2 sentences!
                            if self.sentence_count >= 2:
                                # Inject a double newline to guarantee Markdown paragraph break
                                processed_chunk += "\n\n"
                                self.sentence_count = 0
                                self.current_paragraph = ""

            yield processed_chunk
