import os
import json
from langchain_core.prompts import ChatPromptTemplate
from backend.orchestrator.state import AiONState
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class ComponentMemoryAgent:
    """
    Component Memory Engine: Scans generated UI components after successful builds, 
    evaluates them for quality and customization, and saves exceptional ones back to the Template Catalog
    as a 'yAI Internal' reusable component, allowing yAI to build its own bespoke library over time.
    """
    def __init__(self):
        from backend.agents.router import ModelRouter
        # Use reasoning model to deeply evaluate code quality
        self.llm = ModelRouter.get_optimal_llm("ReviewerAgent", complexity="smart")
        self.templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        self.catalog_path = os.path.join(self.templates_dir, "catalog.json")

    def run(self, state: AiONState) -> AiONState:
        print("\n--- Component Memory Engine: Scanning for reusable components ---")
        
        # Only run memory agent if the build actually succeeded (e.g., passed tests/visual critique)
        feedback = state.get("visual_critique_feedback", "")
        if feedback and feedback != "APPROVED" and feedback != "ship":
            print("   -> Build not fully approved. Skipping Component Memory.")
            return state

        generated_files = state.get("generated_files", {})
        if not generated_files:
            return state

        # Filter for React components
        ui_components = {
            path: code for path, code in generated_files.items() 
            if path.endswith(('.tsx', '.jsx')) and ('components/' in path or 'ui/' in path)
        }

        if not ui_components:
            print("   -> No UI components found to memorize.")
            return state

        system_prompt = """
        You are the Component Memory Engine of yAI.
        Your job is to evaluate newly generated React UI components and decide if they are high-quality, 
        highly-customized, and reusable enough to be permanently added to the yAI Internal Template Library.

        EVALUATION CRITERIA:
        1. **High Quality**: Zero syntax errors, well-structured Tailwind, elegant design.
        2. **Reusable**: It must be generic enough to be adapted in future projects (no hyper-specific hardcoded business logic that can't be easily swapped).
        3. **Novelty/Customization**: It must be a substantive component (e.g., a full Hero, Pricing, or Dashboard layout), not just a basic button.

        If a component passes, extract its metadata. If none pass, return an empty array.
        
        OUTPUT FORMAT (Strict JSON):
        {
            "memorize": [
                {
                    "file_path": "the exact path provided",
                    "id": "a unique snake_case ID like 'custom_hero_002'",
                    "name": "Human readable name",
                    "category": "Hero | Pricing | Auth | Dashboard | Features | Testimonials",
                    "tags": ["react", "tailwind", "custom"],
                    "capability": "Brief description of what this component provides."
                }
            ]
        }
        """

        # We will evaluate up to 3 components to save tokens and time
        components_to_eval = list(ui_components.items())[:3]
        
        eval_payload = ""
        for path, code in components_to_eval:
            eval_payload += f"\n\n--- FILE: {path} ---\n```tsx\n{code}\n```"

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", f"Please evaluate these generated components:\n{eval_payload}")
        ])

        try:
            response = self.llm.invoke(prompt.format_messages())
            raw_text = response.content.strip()
            
            if raw_text.startswith("```json"):
                raw_text = raw_text.replace("```json", "", 1).rstrip("`").strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text.replace("```", "", 1).rstrip("`").strip()
                
            parsed = json.loads(raw_text)
            to_memorize = parsed.get("memorize", [])
            
            if not to_memorize:
                print("   -> No components met the elite quality threshold for memory.")
                return state

            # Load catalog
            try:
                with open(self.catalog_path, 'r') as f:
                    catalog = json.load(f)
            except Exception:
                catalog = {"templates": []}

            templates_list = catalog.get("templates", [])
            
            for item in to_memorize:
                file_path = item.get("file_path")
                if file_path not in ui_components:
                    continue
                    
                code = ui_components[file_path]
                new_id = item.get("id")
                
                # Check if ID already exists, if so append random string
                import uuid
                if any(t["id"] == new_id for t in templates_list):
                    new_id = f"{new_id}_{uuid.uuid4().hex[:6]}"
                    
                # Save the physical file into backend/templates/components/
                comp_dir = os.path.join(self.templates_dir, "components")
                os.makedirs(comp_dir, exist_ok=True)
                
                new_filename = f"{new_id}.tsx"
                dest_path = os.path.join(comp_dir, new_filename)
                
                with open(dest_path, "w", encoding="utf-8") as f:
                    f.write(code)
                    
                # Add to catalog metadata
                new_meta = {
                    "id": new_id,
                    "name": item.get("name", "yAI Custom Component"),
                    "library": "yAI Internal",
                    "category": item.get("category", "Custom"),
                    "framework": "React",
                    "styling": "Tailwind CSS",
                    "dependencies": [], # Could be extracted, keeping simple for now
                    "responsive": True,
                    "darkMode": True,
                    "tags": item.get("tags", []),
                    "file_path": f"backend/templates/components/{new_filename}",
                    "capability": item.get("capability", "A custom high-quality component generated by yAI.")
                }
                
                templates_list.append(new_meta)
                print(f"   -> [Component Memory] Successfully saved new component to library: {new_id} ({item.get('name')})")

            # Save updated catalog
            catalog["templates"] = templates_list
            with open(self.catalog_path, "w", encoding="utf-8") as f:
                json.dump(catalog, f, indent=2)

        except Exception as e:
            logger.warning(f"   -> [Component Memory] Engine failed: {e}")

        return state
