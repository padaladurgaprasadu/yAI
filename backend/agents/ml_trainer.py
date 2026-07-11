from backend.agents.base import BaseAgent
from langchain_core.messages import HumanMessage, SystemMessage
from backend.orchestrator.state import AiONState
import json

class AIMLModelTrainingAgent(BaseAgent):
    def __init__(self):
        super().__init__(temperature=0.2)
        
    def run(self, state: AiONState) -> dict:
        """Generates advanced ML training loops based on the blueprint and generated code."""
        
        # Only execute if the role is ML-related
        ml_roles = ["Machine Learning Engineer", "Data Scientist", "Deep Learning Researcher"]
        if state.get("agent_role") not in ml_roles:
            return {"code_files": state.get("code_files", {})}
            
        print("🤖 [AIML Trainer] Generating robust training loops and data loaders...")
        
        goal = state.get("goal")
        blueprint = state.get("blueprint", {})
        code_files = state.get("code_files", {})
        semantic_context = state.get("semantic_context", "No context available.")
        
        system_prompt = """You are the yAI AI/ML Model Training Agent.
Your job is to analyze the user's ML goal and the current codebase, and generate a HIGH-QUALITY, robust `train.py` script.
Use the provided Semantic Context from past successful projects to guide your architectural decisions.

The script MUST include:
1. Robust data loading and preprocessing (handling missing values, normalization, train/val/test splits).
2. The complete model training loop (PyTorch, TensorFlow, or Scikit-learn) with detailed comments.
3. Proper Loss functions and optimizers (with learning rate scheduling if applicable).
4. Evaluation metrics (Accuracy, F1, MSE, etc.) evaluated on a validation set during training.
5. Model saving/checkpointing logic (save the best model, not just the last epoch).
6. Excellent error handling and exception logging.

Return ONLY a valid JSON object containing the new or updated files. Do NOT use markdown code blocks like ```json.
Format:
{
  "train.py": "import torch\\n..."
}"""

        prompt = f"""
Goal: {goal}
Blueprint: {json.dumps(blueprint, indent=2)}

Semantic Context (Past Successes):
{semantic_context}

Current Code Files:
{json.dumps(code_files, indent=2)}

Generate the highly robust training scripts and return the valid JSON object.
"""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            content = response.content
            if isinstance(content, list):
                content = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
            
            content = content.strip().strip('`').replace('json\n', '').strip()
            new_files = json.loads(content, strict=False)
            
            # Merge new files into existing code files
            merged_files = {**code_files, **new_files}
            return {"code_files": merged_files}
            
        except Exception as e:
            print(f"⚠️ [AIML Trainer] Failed to generate training logic: {e}")
            return {"code_files": code_files}
