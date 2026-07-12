import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.orchestrator.state import AiONState

class TemplateAgent:
    def __init__(self):
        # We use a fast model for reasoning about component compatibility
        from backend.agents.router import ModelRouter
        self.llm = ModelRouter.get_optimal_llm("TemplateAgent", complexity="fast")
        
        self.templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        self.catalog_path = os.path.join(self.templates_dir, "catalog.json")

    def run(self, state: AiONState) -> AiONState:
        print("\n--- Template Intelligence Layer: Searching for Components ---")
        
        goal = state.get("goal", "")
        modules = state.get("modules", [])
        
        if not modules:
            print("   -> No modules found. Skipping template intelligence.")
            return state
            
        try:
            with open(self.catalog_path, 'r') as f:
                catalog = json.load(f)
        except Exception as e:
            print(f"   -> [Error loading Template Catalog]: {e}")
            return state
            
        catalog_str = json.dumps(catalog.get("templates", []), indent=2)
            
        system_prompt = f"""
        You are the Template Intelligence Layer of the yAI Engineering OS.
        Your job is to analyze the user's project goal and proposed modules, then retrieve and compose a roster of premium UI components from our Template Catalog.
        
        GOAL: {goal}
        MODULES: {json.dumps(modules)}
        
        AVAILABLE TEMPLATE CATALOG:
        {catalog_str}
        
        RULES:
        1. Select the absolute best components from the catalog for the given goal. 
        2. Output MUST be valid JSON containing a list of selected component IDs.
        
        OUTPUT FORMAT (JSON only):
        [
            "hero_001",
            "nav_001"
        ]
        """
        
        try:
            response = self.llm.invoke(system_prompt)
            raw_text = response.content.strip()
            
            # Clean markdown formatting if present
            if raw_text.startswith("```json"):
                raw_text = raw_text.replace("```json", "", 1).rstrip("`").strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text.replace("```", "", 1).rstrip("`").strip()
                
            selected_ids = json.loads(raw_text)
            
            # Now retrieve the ACTUAL source code for the selected components
            retrieved_templates = []
            
            templates = catalog.get("templates", [])
            for comp_id in selected_ids:
                template_meta = next((t for t in templates if t["id"] == comp_id), None)
                if template_meta:
                    # Construct absolute path to the file
                    file_path = template_meta.get("file_path")
                    # Make path absolute based on project root
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                    abs_path = os.path.join(project_root, file_path.replace("/", os.sep))
                    
                    try:
                        with open(abs_path, 'r', encoding='utf-8') as cf:
                            source_code = cf.read()
                            
                        retrieved_templates.append({
                            "metadata": template_meta,
                            "source_code": source_code
                        })
                        print(f"   -> Retrieved source code for {template_meta['name']}")
                    except Exception as fe:
                        print(f"   -> [Error reading source for {comp_id}]: {fe}")
            
            state["template_roster"] = retrieved_templates
            print(f"   -> Total templates successfully retrieved and injected: {len(retrieved_templates)}")
                
        except Exception as e:
            print(f"   -> [Error in Template Layer]: {str(e)}")
            state["template_roster"] = []
            
        return state
