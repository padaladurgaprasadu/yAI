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
            
        all_templates = []
        for tier_key, items in catalog.items():
            if isinstance(items, list):
                all_templates.extend(items)
                
        catalog_str = json.dumps(catalog, indent=2)
            
        system_prompt = f"""
        You are the Template Intelligence Layer (Component Selection Engine) of the yAI Engineering OS.
        Your job is to act as an Intelligent Software Assembler. You must analyze the user's project goal and proposed modules, then evaluate, rank, and select the absolute best premium components from our 6-Tier Template Registry.
        
        GOAL: {goal}
        MODULES: {json.dumps(modules)}
        
        AVAILABLE 6-TIER TEMPLATE CATALOG:
        {catalog_str}
        
        RULES:
        1. Evaluate templates across ALL tiers (UI, Backend, Database, Deployment) and select ALL that apply to this project's requirements.
        2. Prioritize Tier 3 (Internal), Tier 4 (Backend), and Tier 5 (Database) templates if they match the requested features (e.g., JWT Auth, SaaS Schema).
        3. Output MUST be valid JSON containing an array of selected components, including your rationale.
        
        OUTPUT FORMAT (JSON only):
        {{
            "selected_templates": [
                {{
                    "id": "hero_001",
                    "rationale": "High design quality, perfectly matches the SaaS landing page requirement with animated framer-motion elements."
                }}
            ]
        }}
        """
        
        try:
            response = self.llm.invoke(system_prompt)
            raw_text = response.content.strip()
            
            if raw_text.startswith("```json"):
                raw_text = raw_text.replace("```json", "", 1).rstrip("`").strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text.replace("```", "", 1).rstrip("`").strip()
                
            parsed_data = json.loads(raw_text)
            selected_ids = [t["id"] for t in parsed_data.get("selected_templates", [])]
            
            for t in parsed_data.get("selected_templates", []):
                print(f"   -> [Template Engine] Selected {t['id']}: {t.get('rationale', '')}")
            
            # Now retrieve the ACTUAL source code for the selected components
            retrieved_templates = []
            
            for comp_id in selected_ids:
                template_meta = next((t for t in all_templates if t["id"] == comp_id), None)
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
            
            if "code_files" not in state or state["code_files"] is None:
                state["code_files"] = {}
                
            for template in retrieved_templates:
                meta = template["metadata"]
                base_name = os.path.basename(meta.get("file_path", ""))
                target_output_path = meta.get("target_output_path")
                
                if target_output_path:
                    final_path = target_output_path
                else:
                    base_name = base_name.replace(".tsx", ".jsx")
                    if base_name:
                        final_path = f"client/src/components/{base_name}"
                    else:
                        continue
                        
                state["code_files"][final_path] = template["source_code"]
                print(f"   -> [Zero-Shot Assembly] Injected {final_path} directly into codebase memory.")

            print(f"   -> Total templates successfully retrieved and injected: {len(retrieved_templates)}")
                
        except Exception as e:
            print(f"   -> [Error in Template Layer]: {str(e)}")
            state["template_roster"] = []
            
        return state
