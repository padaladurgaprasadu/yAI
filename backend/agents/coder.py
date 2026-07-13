import re
import json
import concurrent.futures
from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
from backend.utils.logger import get_logger, measure_time
from backend.utils.cache import llm_cache
import ast

logger = get_logger(__name__)

class CoderAgent(BaseAgent):
    """
    The Coder Agent generates code for multiple files simultaneously using multithreading.
    """
    def __init__(self):
        super().__init__()

    def _generate_single_file(self, blueprint_str, feedback, runtime_error, target_file, agent_role, semantic_context, design_tokens="{}"):
        
        # Dynamically adapt rules based on agent_role
        if "Research" in agent_role:
            framework_rules = "3. RESEARCH RULE: Write an extensive, academic, and highly detailed document for the requested file. Ensure you provide a NOVEL APPROACH with innovative ideas, avoiding generic statements. Use Markdown formatting. Do not write software code unless explicitly requested.\n4. Cite hypothetical but realistic methods where appropriate."
        elif "Fullstack" in agent_role or "Web" in agent_role or "UI" in agent_role:
            framework_rules = "3. CRITICAL PORT RULE: Your Express backend MUST run on PORT 5000. Your Vite React frontend will run on its default port, but you must configure your backend cors to accept requests.\n4. CRITICAL FRAMEWORK RULE: Write modular, clean code using React for the frontend and Node.js/Express for the backend. Use Tailwind CSS classes for styling.\n5. CRITICAL ROUTING RULE: You MUST use React Router v6 syntax. Do NOT use '<Switch>'. You MUST use '<Routes>' and '<Route path=\"/\" element={<Component />} />'.\n6. CRITICAL COMPONENT RULE: You MUST NOT import any components, contexts, or stores that you did not explicitly generate. If it's not in the blueprint's file_structure, DO NOT IMPORT IT.\n7. POSTGRESQL RULE: If using PostgreSQL, strictly use the connection string 'postgresql://postgres:postgres@localhost:5432/postgres'.\n8. CRITICAL BACKEND DEPENDENCY RULE: Your root 'package.json' MUST include 'express', 'cors', 'pg', 'dotenv', 'concurrently' and any other backend libraries. Its dev script MUST be: '\"dev\": \"concurrently \\\"node server.js\\\" \\\"cd client && npm run dev\\\"\"'.\n9. CRITICAL VITE RULE: The frontend is pre-scaffolded with Vite. You MUST NOT generate 'client/package.json', 'index.html', or 'main.jsx'. You ONLY generate 'client/src/App.jsx' and your custom components (e.g. 'client/src/components/Dashboard.jsx'). Every React file MUST end with '.jsx'.\n10. CRITICAL API PREVIEW RULE: The frontend preview runs in a Sandpack sandbox that DOES NOT RUN THE BACKEND. Therefore, every single API call (fetch/axios) in your React components MUST have a try/catch block that falls back to realistic MOCK DATA if the fetch fails! The UI must fully function and look beautiful using this mock data during the presentation!"
        else:
            framework_rules = "3. CRITICAL PORT RULE: The app must run on port 3000 for the iframe preview.\n4. CRITICAL FRAMEWORK RULE: Write modular, clean code using the appropriate Python libraries for ML/Data Science (e.g. Pandas, Scikit-learn, PyTorch, Streamlit, FastAPI). Ensure all dependencies are documented in requirements.txt.\n5. Do NOT write React code unless explicitly requested in the blueprint. Use Streamlit for simple UIs.\n6. POSTGRESQL RULE: If using PostgreSQL, you MUST strictly use the connection string 'postgresql://postgres:postgres@localhost:5432/postgres'. Do NOT use environment variables for DB connections."

        from backend.agents.base import GLOBAL_AGENT_RULES
        from backend.agents.orchestration_prompts import CODER_DISPATCHER_PROMPT
        
        import os
        from backend.utils.workspace import get_workspace_root
        workspace = get_workspace_root() if hasattr(get_workspace_root, '__call__') else "."
        target_path = os.path.join(workspace, target_file) if not os.path.isabs(target_file) else target_file
        
        # 1. Advanced Context Engine Integration
        try:
            from backend.agents.context_engine import ContextEngine
            ctx_engine = ContextEngine(workspace)
            dependency_context = ctx_engine.build_dependency_context(target_path)
            if dependency_context and dependency_context != "No local dependencies found.":
                semantic_context += f"\n\n[Advanced IDE Context - Dependencies for {target_file}]\n{dependency_context}"
        except Exception as e:
            logger.warning(f"[Coder] Context Engine failed: {e}")
            
        file_exists = os.path.exists(target_path)
        current_code = ""
        if file_exists:
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    current_code = f.read()
            except: pass

        # 2. Semantic Diff Engine Integration (Only if file is reasonably large to warrant a diff)
        if file_exists and len(current_code.split('\n')) > 30 and feedback:
            logger.info(f"   -> [Coder] Using Semantic Diff Engine for {target_file}...")
            try:
                from backend.agents.diff_engine import SemanticDiffEngine
                diff_engine = SemanticDiffEngine()
                instruction = f"Blueprint: {blueprint_str}\nFeedback/Error: {feedback} {runtime_error}\nContext: {semantic_context}"
                diffs = diff_engine.generate_diff(target_file, current_code, instruction)
                if diffs:
                    new_code = diff_engine.apply_diff(current_code, diffs)
                    return (target_file, new_code)
            except Exception as e:
                logger.warning(f"[Coder] Diff Engine failed, falling back to full generation: {e}")

        # Fallback to full generation
        system_prompt = GLOBAL_AGENT_RULES + "\\n\\n" + CODER_DISPATCHER_PROMPT + f"""
        
ADDITIONAL INSTRUCTIONS:
TARGET FILE: {target_file}
{framework_rules}
- ADVANCED CODE RULE: Write highly efficient, robust code. Strict error handling (try/catch), edge-case fallbacks, input validation.
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Blueprint: {blueprint}\nDesign Tokens: {design_tokens}\nSemantic Context: {context}\nTarget File: {target_file}\nReview Feedback: {review_feedback}\nRuntime Error: {runtime_error}")
        ])
        chain = prompt | self.llm
        
        import time
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = chain.invoke({
                    "blueprint": blueprint_str,
                    "design_tokens": design_tokens,
                    "context": semantic_context,
                    "target_file": target_file,
                    "review_feedback": feedback,
                    "runtime_error": runtime_error
                })
                content = response.content
                if isinstance(content, list):
                    content = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
                    
                import json
                import re
                
                # Extract JSON
                from backend.utils.json_parser import parse_json_robustly
                data = parse_json_robustly(content)
                    
                code = data.get("content", "")
                print(f"   -> [Success] Generated {target_file}")
                return (target_file, code)
                    
            except Exception as e:
                error_str = str(e)
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    print(f"      - [WARNING] Error generating {target_file}: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"      - [ERROR] Exception while generating {target_file} after {max_retries} attempts: {e}")
                    return target_file, f"// Error: yAI encountered an exception: {e}"

    @measure_time(logger)
    def run(self, state: AiONState, q=None) -> AiONState:
        # If we already have code files (e.g. from Reviewer loop), we might only regenerate the ones with issues.
        # For simplicity, we just regenerate all or use the target files.
        files_to_generate = state.get("blueprint", {}).get("file_structure", [])
        blueprint_str = json.dumps(state.get("blueprint", {}))
        
        feedback = state.get("review_feedback")
        audit_feedback = state.get("audit_feedback")
        runtime_error = state.get("runtime_error")
        missing_deps = state.get("missing_dependencies", [])
        
        # --- NEXT-GEN AUTO-HEALING DIAGNOSTIC ---
        if missing_deps:
            print(f"[Coder] Build Verification failed. Generating missing files: {missing_deps}")
            files_to_generate = missing_deps
            # Clear missing dependencies state so we don't infinitely loop if generation fails
            state["missing_dependencies"] = []
        elif runtime_error or feedback or audit_feedback or state.get("execution_mode") in ["lightning", "fast"]:
            print(f"[Coder] Next-Gen Auto-Healing / Fast Mode: Diagnosing failing files...")
            diagnostic_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an elite debugging AI. Given a list of files in the project, and a runtime error, goal, or review feedback, identify exactly which files need to be modified to fix the issue or implement the feature. Output EXACTLY a JSON list of strings (the exact file paths from the provided list) and nothing else."),
                ("human", "Project Files: {files}\nRuntime Error: {error}\nReview Feedback / Goal: {feedback}")
            ])
            try:
                available_files = list(state.get("code_files", {}).keys())
                # If there are no existing files, fallback to blueprint
                if not available_files:
                    available_files = state.get("blueprint", {}).get("file_structure", [])
                    
                diag_chain = diagnostic_prompt | self.fast_llm
                res = diag_chain.invoke({
                    "files": json.dumps(available_files),
                    "error": runtime_error,
                    "feedback": audit_feedback if audit_feedback else (feedback if feedback else state.get("goal"))
                })
                from backend.utils.json_parser import parse_json_robustly
                files_to_fix = parse_json_robustly(res.content)
                if isinstance(files_to_fix, list) and len(files_to_fix) > 0:
                    files_to_generate = [f for f in files_to_fix if f in files_to_generate]
                    if not files_to_generate: # Fallback if hallucinated
                        files_to_generate = state["blueprint"].get("file_structure", [])
            except Exception as e:
                print(f"   -> [Coder] Diagnostic failed: {e}. Falling back to full regeneration.")
        # ----------------------------------------
        
        print(f"[Coder] Generating {len(files_to_generate)} files sequentially (Streaming)...")
        
        # PRESERVE EXISTING FILES during auto-healing
        code_files = state.get("code_files", {}).copy()
        
        agent_role = state.get("agent_role", "Fullstack Web Developer")
        semantic_context = state.get("semantic_context", "No semantic context provided.")
        project_id = state.get("project_id")
        
        # Access the global stream queue if it exists
        try:
            from backend.api_real import stream_queues
            q = stream_queues.get(project_id)
        except ImportError:
            q = None
            
        if q:
            q.put({"type": "agent_state", "agent": "coder"})
            
        # Custom LangChain callback to stream tokens to our queue
        from langchain_core.callbacks.base import BaseCallbackHandler
        class QueueStreamCallback(BaseCallbackHandler):
            def on_llm_new_token(self, token: str, **kwargs) -> None:
                if q:
                    q.put({"type": "code_token", "token": token})

        # Increment revision count if we are looping
        if feedback or runtime_error or missing_deps:
            state["revision_count"] = state.get("revision_count", 0) + 1
            if runtime_error:
                print(f"[Coder] Auto-Heal Triggered! Attempting to fix runtime error...")
                if q:
                    q.put({"type": "progress", "message": "Auto-Heal Triggered! Attempting to fix runtime error..."})
                    q.put({"type": "timeline", "title": "yAI Autonomous Debugger", "reason": "Locating issue in logs and patching...", "status": "active"})
        elif q:
            q.put({"type": "timeline", "title": f"Generating {len(files_to_generate)} modules", "reason": "Translating architecture to code", "status": "active"})
        
        import concurrent.futures
        
        def generate_file(target_file):
            if q:
                q.put({"type": "progress", "message": f"⏳ Started generating {target_file}..."})
                q.put({"type": "file_start", "file": target_file})
                
            if "Research" in agent_role:
                framework_rules = "3. RESEARCH RULE: Write an extensive, academic, and highly detailed document for the requested file. Ensure you provide a NOVEL APPROACH with innovative ideas, avoiding generic statements. Use Markdown formatting. Do not write software code unless explicitly requested.\n4. Cite hypothetical but realistic methods where appropriate."
            elif "Fullstack" in agent_role or "Web" in agent_role or "UI" in agent_role:
                framework_rules = "3. CRITICAL PORT RULE: Your Express backend MUST run on PORT 5000. Your Vite React frontend will run on its default port, but you must configure your backend cors to accept requests.\n4. CRITICAL FRAMEWORK RULE: Write modular, clean code using React for the frontend and Node.js/Express for the backend. Use Tailwind CSS classes for styling.\n5. CRITICAL ROUTING RULE: You MUST use React Router v6 syntax. Do NOT use '<Switch>'. You MUST use '<Routes>' and '<Route path=\"/\" element={{<Component />}} />'.\n6. CRITICAL COMPONENT RULE: You MUST NOT import any components, contexts, or stores that you did not explicitly generate. If it's not in the blueprint's file_structure, DO NOT IMPORT IT.\n7. POSTGRESQL RULE: If using PostgreSQL, strictly use the connection string 'postgresql://postgres:postgres@localhost:5432/postgres'.\n8. CRITICAL BACKEND DEPENDENCY RULE: Your root 'package.json' MUST include 'express', 'cors', 'pg', 'dotenv', 'concurrently' and any other backend libraries. Its dev script MUST be: '\"dev\": \"concurrently \\\"node server.js\\\" \\\"cd client && npm run dev\\\"\"'.\n9. CRITICAL VITE RULE: The frontend is pre-scaffolded with Vite. You MUST NOT generate 'client/package.json', 'index.html', or 'main.jsx'. You ONLY generate 'client/src/App.jsx' and your custom components (e.g. 'client/src/components/Dashboard.jsx'). Every React file MUST end with '.jsx'.\n10. CRITICAL API PREVIEW RULE: The frontend preview runs in a Sandpack sandbox that DOES NOT RUN THE BACKEND. Therefore, every single API call (fetch/axios) in your React components MUST have a try/catch block that falls back to realistic MOCK DATA if the fetch fails! The UI must fully function and look beautiful using this mock data during the presentation!"
                
                design_tokens = state.get("design_tokens", {})
                if design_tokens:
                    framework_rules += "\n\nCRITICAL DESIGN SYSTEM RULE: You MUST strictly adhere to the following design system tokens:\n{design_tokens}\nEnsure all Tailwind classes, colors, CSS, layout, and animations perfectly reflect this exact premium style."
            else:
                framework_rules = "3. CRITICAL PORT RULE: The app must run on port 3000 for the iframe preview.\n4. CRITICAL FRAMEWORK RULE: Write modular, clean code using the appropriate Python libraries for ML/Data Science (e.g. Pandas, Scikit-learn, PyTorch, Streamlit, FastAPI). Ensure all dependencies are documented in requirements.txt.\n5. Do NOT write React code unless explicitly requested in the blueprint. Use Streamlit for simple UIs.\n6. POSTGRESQL RULE: If using PostgreSQL, you MUST strictly use the connection string 'postgresql://postgres:postgres@localhost:5432/postgres'. Do NOT use environment variables for DB connections."

            from backend.agents.base import GLOBAL_AGENT_RULES
            system_prompt = GLOBAL_AGENT_RULES + f"""
ROLE: Coder (Dispatcher Sub-Agent)
GOAL: Write the FULL production-grade content for the requested file: {{target_file}}.

IMPORTANT RULES:
- TDD COMPLIANCE: A TDD Test Suite is provided in the prompt. You MUST ensure that the code you generate strictly satisfies the requirements and contracts defined in this test suite.
- You must use only dependencies already declared in the Architect's tech_stack. If a new dependency is needed, add it to 'dependency_requests'.
{framework_rules}
- ADVANCED CODE RULE: Write highly efficient, robust code. Strict error handling (try/catch), edge-case fallbacks, input validation.
- If you receive Review Feedback or a Runtime Error, you must fix the issues mentioned.

OUTPUT SCHEMA:
{{
  "file_path": "{{target_file}}",
  "content": "raw code string (escape quotes properly)",
  "depends_on": ["other file paths this assumes exist"],
  "dependency_requests": ["package@version, with why"],
  "confidence": "high" | "medium" | "low",
  "known_gaps": ["e.g. 'no input validation on this endpoint yet'"]
}}
"""

            template_roster = state.get("template_roster", [])
            template_context = ""
            if template_roster:
                template_context = "\n=== TEMPLATE INTELLIGENCE ROSTER (ASSEMBLY ENGINE) ===\n"
                template_context += "You are acting as an Intelligent Software Assembler, NOT just a code generator.\n"
                template_context += "The following premium components have been evaluated and selected for this exact task. You MUST use this source code as your absolute foundation.\n"
                template_context += "ASSEMBLY RULES:\n"
                template_context += "1. NEVER write a component from scratch if a template is provided below for it.\n"
                template_context += "2. PRESERVE the underlying DOM structure, React hooks, and framer-motion animations of the template.\n"
                template_context += "3. CUSTOMIZE the text, Tailwind colors, fonts, and icons to perfectly match the user's requested brand and the design tokens.\n"
                template_context += "4. WEAVE these disparate templates together into a cohesive, single application where they look like they belong to the same design system.\n\n"
                for idx, t in enumerate(template_roster):
                    meta = t.get("metadata", {})
                    t_code = t.get("source_code", "")
                    template_context += f"\n--- TEMPLATE {idx+1}: {meta.get('name', 'Unknown')} ---\n"
                    template_context += f"Capability: {meta.get('capability', '')}\n"
                    template_context += f"Source Code:\n```tsx\n{t_code}\n```\n"

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "Blueprint: {blueprint}\nDesign Tokens: {design_tokens}\nSemantic Context: {context}\nTarget File: {target_file}\nReview Feedback: {review_feedback}\nRuntime Error: {runtime_error}\nTDD Test Suite: {test_suite}\n{template_context}")
            ])
            
            import time
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    messages = prompt.format_messages(
                        blueprint=blueprint_str,
                        context=semantic_context,
                        target_file=target_file,
                        review_feedback=feedback,
                        runtime_error=runtime_error,
                        design_tokens=json.dumps(state.get("design_tokens", {}), indent=2),
                        test_suite=state.get("test_suite", "No specific tests provided."),
                        template_context=template_context
                    )
                    
                    response_text = ""
                    buffer = ""
                    
                    from backend.agents.router import ModelRouter
                    file_specific_llm = ModelRouter.route_by_file_type(target_file)
                    
                    for chunk in file_specific_llm.stream(messages):
                        if chunk.content:
                            buffer += chunk.content
                            response_text += chunk.content
                            if q and len(buffer) > 20:
                                q.put({"type": "code_token", "file": target_file, "token": buffer})
                                buffer = ""
                    
                    if q and buffer:
                        q.put({"type": "code_token", "file": target_file, "token": buffer})
                    
                    full_content = response_text
                    import re
                    # Parse JSON Output
                    match = re.search(r'\{.*\}', full_content, re.DOTALL)
                    if match:
                        data = json.loads(match.group(0))
                        code = data.get("content", "")
                        
                        # Handle missing dependencies request
                        dep_requests = data.get("dependency_requests", [])
                        if dep_requests:
                            logger.info(f"[Coder] Dependency requests for {target_file}: {dep_requests}")
                    else:
                        data = json.loads(full_content)
                        code = data.get("content", "")
                        
                    if code:
                        
                        # CODE VALIDATION GATE
                        if target_file.endswith(".py"):
                            try:
                                ast.parse(code)
                            except SyntaxError:
                                pass
                            
                        logger.info(f"   -> [Success] Generated {target_file}")
                        if q:
                            q.put({"type": "progress", "message": f"✅ Finished {target_file}"})
                        return (target_file, code)
                    else:
                        logger.warning(f"   -> [Attempt {attempt+1}] Failed to parse XML tags for {target_file}.")
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str and attempt < max_retries - 1:
                        # Massive backoff for free-tier quotas (15 RPM). Wait 20s then 40s.
                        wait_time = (attempt + 1) * 20
                        logger.warning(f"      - [WARNING] Rate limit hit for {target_file}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"      - [ERROR] Exception while generating {target_file}: {e}")
                        last_error = str(e)
                        
                        # Wait briefly before retrying a generic error to prevent infinite spin
                        if attempt < max_retries - 1:
                            time.sleep(2)
            
            return (target_file, f"// Error: yAI failed to generate {target_file}. Exception: {last_error if 'last_error' in locals() else 'Unknown'}")

        # Execute parallel generation for speed
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_file = {executor.submit(generate_file, f): f for f in files_to_generate}
            try:
                # Add a hard timeout to prevent the pipeline from hanging forever
                for future in concurrent.futures.as_completed(future_to_file, timeout=180):
                    file_name, code = future.result()
                    code_files[file_name] = code
            except concurrent.futures.TimeoutError:
                logger.error("[Coder] Parallel generation timed out after 180 seconds!")
                if q:
                    q.put({"type": "progress", "message": "⚠️ Code generation timed out."})
        
        state["code_files"] = code_files
        
        # Clear errors if generation succeeded
        state["error"] = None
        state["review_feedback"] = None
        state["runtime_error"] = None
        
        if q:
            q.put({"type": "timeline_update", "status": "done"})
        
        # Log to memory
        try:
            from backend.memory.neo4j_client import Neo4jClient
            client = Neo4jClient()
            rationale = f"Generated {len(code_files)} files sequentially"
            client.log_decision(state.get("project_id"), "Coder", rationale)
            client.close()
        except Exception:
            pass
            
        return state
