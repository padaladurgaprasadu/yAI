from backend.agents.base import BaseAgent
from langchain_core.messages import HumanMessage, SystemMessage
from backend.orchestrator.state import AiONState
import json

class AutoHyperparameterTuningAgent(BaseAgent):
    def __init__(self):
        super().__init__(temperature=0.2)
        
    def run(self, state: AiONState) -> dict:
        """Generates advanced hyperparameter tuning scripts."""
        
        # Only execute if the role is ML-related
        ml_roles = ["Machine Learning Engineer", "Data Scientist", "Deep Learning Researcher"]
        if state.get("agent_role") not in ml_roles:
            return {"code_files": state.get("code_files", {})}
            
        print("🤖 [Auto HP Tuner] Generating Optuna/Ray Tune optimization scripts...")
        
        goal = state.get("goal")
        blueprint = state.get("blueprint", {})
        code_files = state.get("code_files", {})
        semantic_context = state.get("semantic_context", "No context available.")
        
        system_prompt = """You are the yAI Auto Hyperparameter Tuning Agent.
Your job is to analyze the user's ML goal and the current codebase (specifically the training loop), and generate an advanced, highly robust hyperparameter optimization script using Optuna.
Use the provided Semantic Context from past successful projects to guide your optimization strategies.

The script MUST include:
1. Definition of the objective function incorporating cross-validation.
2. A comprehensive hyperparameter search space (e.g., learning rate, batch size, dropout, num_layers, optimizer type).
3. The Optuna study/optimization loop with early stopping/pruning enabled (e.g., MedianPruner).
4. Saving the best hyperparameters to a structured JSON file.
5. Excellent error handling and exception logging.

Return ONLY a valid JSON object containing the new or updated files. Do NOT use markdown code blocks like ```json.
Format:
{
  "tune.py": "import optuna\\n..."
}"""

        prompt = f"""
Goal: {goal}
Blueprint: {json.dumps(blueprint, indent=2)}

Semantic Context (Past Successes):
{semantic_context}

Current Code Files:
{json.dumps(code_files, indent=2)}

Generate the highly robust tuning script and return the valid JSON object.
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
            print(f"⚠️ [Auto HP Tuner] Failed to generate tuning logic: {e}")
            return {"code_files": code_files}
