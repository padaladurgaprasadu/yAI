import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.orchestrator.state import AiONState

class TemplateAgent:
    def __init__(self):
        # We use a fast model for reasoning about component compatibility
        from backend.agents.router import ModelRouter
        self.llm = ModelRouter.get_optimal_llm("TemplateAgent", complexity="fast")
        
        # Hardcoded component metadata index (simulating a Vector DB/Registry)
        self.component_registry = """
        AVAILABLE LIBRARIES & COMPONENTS:
        
        1. shadcn/ui (Tailwind CSS, Radix UI primitives)
           - Components: Button, Input, Form, Table, Dialog, DropdownMenu, Card, Avatar, Badge
           - Best for: Dashboards, SaaS, Forms, Data-heavy interfaces
           
        2. ReactBits (Tailwind CSS, React Spring / Framer Motion)
           - Components: AnimatedHero, SplitText, ParticlesBackground, MagnetButton, ShinyText
           - Best for: Landing pages, portfolios, eye-catching marketing sections
           
        3. Aceternity UI (Tailwind CSS, Framer Motion)
           - Components: 3DPin, BackgroundBeams, BentoGrid, ContainerScroll, HoverEffect, Sparkles, TracingBeam
           - Best for: AI startup landing pages, highly interactive premium interfaces
           
        4. Magic UI (Tailwind CSS, Framer Motion)
           - Components: RetroGrid, Meteors, ShineBorder, TextReveal, Marquee, BentoGrid
           - Best for: AI chat interfaces, modern SaaS landing pages
           
        5. yAI Internal Library (Tailwind CSS, Glassmorphism)
           - Components: WorkspaceTabs, GlassPanel, AIChatWidget, TerminalView, CodeEditor
           - Best for: AI Engineering OS, IDE-like interfaces
        """

    def run(self, state: AiONState) -> AiONState:
        print("\n--- Template Intelligence Layer: Searching for Components ---")
        
        goal = state.get("goal", "")
        modules = state.get("modules", [])
        
        if not modules:
            print("   -> No modules found. Skipping template intelligence.")
            return state
            
        system_prompt = f"""
        You are the Template Intelligence Layer of the yAI Engineering OS.
        Your job is to analyze the user's project goal and proposed modules, then retrieve and compose a roster of premium UI components from trusted libraries.
        
        GOAL: {goal}
        MODULES: {json.dumps(modules)}
        
        {self.component_registry}
        
        RULES:
        1. Select the absolute best components for the given goal. If it's an AI landing page, favor Aceternity/Magic UI. If it's a SaaS dashboard, favor shadcn/ui.
        2. Ensure compatibility. Avoid mixing too many different animation libraries (e.g., stick to Framer Motion based ones if possible).
        3. Output MUST be valid JSON containing a list of selected components.
        
        OUTPUT FORMAT (JSON only):
        [
            {{
                "name": "Component Name (e.g. BentoGrid)",
                "library": "Aceternity UI",
                "purpose": "Used for the features section",
                "dependencies": ["framer-motion", "clsx", "tailwind-merge"]
            }}
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
                
            roster = json.loads(raw_text)
            state["template_roster"] = roster
            
            print(f"   -> Retrieved {len(roster)} premium components for the UI.")
            for comp in roster:
                print(f"      - {comp['name']} from {comp['library']}")
                
        except Exception as e:
            print(f"   -> [Error in Template Layer]: {str(e)}")
            state["template_roster"] = []
            
        return state
