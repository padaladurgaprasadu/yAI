import asyncio
from typing import List, Any
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langchain_core.runnables import Runnable
from backend.utils.logger import get_logger, measure_time

logger = get_logger(__name__)

class OmegaModel(Runnable):
    """
    yAI Omega Meta-Model (Mixture-of-Agents).
    Wraps multiple LLMs. It fires the prompt to all 'worker' LLMs concurrently.
    Then it feeds all their responses into the 'synthesizer' LLM to produce a final, superior output.
    """
    def __init__(self, workers: List[Any], synthesizer: Any):
        self.workers = workers
        self.synthesizer = synthesizer

    @measure_time(logger)
    def invoke(self, input: Any, config: Any = None) -> Any:
        return asyncio.run(self.ainvoke(input, config))

    async def ainvoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        logger.info(f"[OmegaModel] Firing request to {len(self.workers)} concurrent worker models...")
        
        # 1. Parallel Generation Phase
        tasks = [worker.ainvoke(input, config, **kwargs) for worker in self.workers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_responses = []
        for idx, res in enumerate(results):
            if isinstance(res, Exception):
                logger.warning(f"[OmegaModel] Worker {idx} failed: {res}")
            else:
                valid_responses.append(res)
                
        if not valid_responses:
            raise RuntimeError("All Omega worker models failed.")
            
        if len(valid_responses) == 1:
            logger.warning("[OmegaModel] Only 1 worker succeeded. Skipping synthesis.")
            return valid_responses[0]
            
        # 2. Synthesis Phase
        logger.info("[OmegaModel] Synthesizing outputs from multiple models into an ultimate response...")
        
        # Extract original prompt string
        original_prompt = "Unknown prompt"
        if isinstance(input, str):
            original_prompt = input
        elif isinstance(input, list):
            original_prompt = "\n".join(m.content if hasattr(m, 'content') else str(m) for m in input)
        elif isinstance(input, dict):
            original_prompt = str(input)
            
        synthesis_prompt = f"""You are the yAI Omega Meta-Model Synthesizer.
Your goal is to evaluate the responses from multiple expert AI agents to the following prompt, and synthesize an ultimate, superior response that is better than any individual agent's answer.
You must correct any flaws, combine their best ideas, and return ONLY the final response exactly as requested by the original prompt (e.g., if the original prompt asked for JSON, you must return JSON).

ORIGINAL PROMPT:
{original_prompt}

"""
        for i, resp in enumerate(valid_responses):
            content = resp.content if hasattr(resp, 'content') else str(resp)
            synthesis_prompt += f"\n--- EXPERT {i+1} RESPONSE ---\n{content}\n"
            
        synthesis_prompt += "\n--- END OF RESPONSES ---\nSynthesize the ultimate response now. Do not include introductory text like 'Here is the synthesized response', just output the final result."

        messages = [
            SystemMessage(content="You are the Omega Meta-Model Synthesizer."),
            HumanMessage(content=synthesis_prompt)
        ]
        
        final_response = await self.synthesizer.ainvoke(messages, config, **kwargs)
        logger.info("[OmegaModel] Synthesis complete.")
        return final_response
