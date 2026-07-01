import re
import json
import concurrent.futures
from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.orchestrator.state import AiONState
from backend.utils.logger import get_logger, measure_time
import ast

logger = get_logger(__name__)

class CoderAgent(BaseAgent):
    """
    The Coder Agent generates code for multiple files simultaneously using multithreading.
    """
    def __init__(self):
        super().__init__()

    def _generate_single_file(self, blueprint_str, feedback, runtime_error, target_file, agent_role, semantic_context):
        
        # Dynamically adapt rules based on agent_role
        if "Research" in agent_role:
            framework_rules = "3. RESEARCH RULE: Write an extensive, academic, and highly detailed document for the requested file. Ensure you provide a NOVEL APPROACH with innovative ideas, avoiding generic statements. Use Markdown formatting. Do not write software code unless explicitly requested.\n4. Cite hypothetical but realistic methods where appropriate."
        elif "Fullstack" in agent_role or "Web" in agent_role or "UI" in agent_role:
            framework_rules = "3. CRITICAL PORT RULE: Your Express backend MUST run on PORT 5000. Your Vite React frontend will run on its default port, but you must configure your backend cors to accept requests.\n4. CRITICAL FRAMEWORK RULE: Write modular, clean code using React for the frontend and Node.js/Express for the backend. Use Tailwind CSS classes for styling.\n5. CRITICAL ROUTING RULE: You MUST use React Router v6 syntax. Do NOT use '<Switch>'. You MUST use '<Routes>' and '<Route path=\"/\" element={{<Component />}} />'.\n6. CRITICAL COMPONENT RULE: You MUST NOT import any components, contexts, or stores that you did not explicitly generate. If it's not in the blueprint's file_structure, DO NOT IMPORT IT.\n7. POSTGRESQL RULE: If using PostgreSQL, strictly use the connection string 'postgresql://postgres:postgres@localhost:5432/postgres'.\n8. CRITICAL BACKEND DEPENDENCY RULE: Your root 'package.json' MUST include 'express', 'cors', 'pg', 'dotenv', 'concurrently' and any other backend libraries. Its dev script MUST be: '\"dev\": \"concurrently \\\"node server.js\\\" \\\"cd client && npm run dev\\\"\"'.\n9. CRITICAL VITE RULE: The frontend is pre-scaffolded with Vite. You MUST NOT generate 'client/package.json', 'index.html', or 'main.jsx'. You ONLY generate 'client/src/App.jsx' and your custom components (e.g. 'client/src/components/Dashboard.jsx'). Every React file MUST end with '.jsx'."
        else:
            framework_rules = "3. CRITICAL PORT RULE: The app must run on port 3000 for the iframe preview.\n4. CRITICAL FRAMEWORK RULE: Write modular, clean code using the appropriate Python libraries for ML/Data Science (e.g. Pandas, Scikit-learn, PyTorch, Streamlit, FastAPI). Ensure all dependencies are documented in requirements.txt.\n5. Do NOT write React code unless explicitly requested in the blueprint. Use Streamlit for simple UIs.\n6. POSTGRESQL RULE: If using PostgreSQL, you MUST strictly use the connection string 'postgresql://postgres:postgres@localhost:5432/postgres'. Do NOT use environment variables for DB connections."

        system_prompt = f"You are a Senior AI {agent_role}. Given a blueprint and semantic context from past successful projects, write the FULL production-grade content for the requested file: {{target_file}}.\n\nIMPORTANT RULES:\n1. Output the file EXACTLY in this format:\n\n<file path=\"{{target_file}}\">\n[YOUR CODE/CONTENT HERE]\n</file>\n\n2. Do NOT use JSON. Do not use markdown backticks outside of the file tags.\n{framework_rules}\n10. MULTILINGUAL CAPABILITY: Automatically detect the language used in the human's Blueprint or context. All comments, UI text, and placeholder text you generate MUST be written in that same language.\n11. If you receive Review Feedback or a Runtime Error, you must fix the issues mentioned."

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Blueprint: {blueprint}\nSemantic Context: {context}\nTarget File: {target_file}\nReview Feedback: {review_feedback}\nRuntime Error: {runtime_error}")
        ])
        chain = prompt | self.llm
        
        import time
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = chain.invoke({
                    "blueprint": blueprint_str,
                    "context": semantic_context,
                    "target_file": target_file,
                    "review_feedback": feedback,
                    "runtime_error": runtime_error
                })
                content = response.content
                if isinstance(content, list):
                    content = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
                    
                import re
                match = re.search(r'<file\s+path="[^"]+">(.*?)</file>', content, re.DOTALL)
                if match:
                    code = match.group(1).strip()
                    print(f"   -> [Success] Generated {target_file}")
                    return (target_file, code)
                else:
                    print(f"   -> [Attempt {attempt+1}] Failed to parse XML tags for {target_file}.")
                    return target_file, f"// Error: AiON LLM failed to format {target_file} correctly"
                    
            except Exception as e:
                error_str = str(e)
                if "429" in error_str and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    print(f"      - [WARNING] Rate limit hit for {target_file}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"      - [ERROR] Exception while generating {target_file}: {e}")
                    return target_file, f"// Error: AiON encountered an exception: {e}"

    @measure_time(logger)
    def run(self, state: AiONState, q=None) -> AiONState:
        # If we already have code files (e.g. from Reviewer loop), we might only regenerate the ones with issues.
        # For simplicity, we just regenerate all or use the target files.
        files_to_generate = state["blueprint"].get("file_structure", ["src/server.js", "package.json"])
        
        blueprint_str = json.dumps(state["blueprint"])
        feedback = state.get("review_feedback")
        runtime_error = state.get("runtime_error")
        
        # --- NEXT-GEN AUTO-HEALING DIAGNOSTIC ---
        if runtime_error or feedback:
            print(f"[Coder] Next-Gen Auto-Healing: Diagnosing failing files...")
            diagnostic_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an elite debugging AI. Given a list of files in the project, and a runtime error or review feedback, identify exactly which files need to be modified to fix the issue. Output EXACTLY a JSON list of strings (the exact file paths from the provided list) and nothing else."),
                ("human", "Project Files: {files}\nRuntime Error: {error}\nReview Feedback: {feedback}")
            ])
            try:
                diag_chain = diagnostic_prompt | self.llm
                res = diag_chain.invoke({
                    "files": json.dumps(files_to_generate),
                    "error": runtime_error,
                    "feedback": feedback
                })
                content = res.content.replace("```json", "").replace("```", "").strip()
                files_to_fix = json.loads(content)
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
        
        # Custom LangChain callback to stream tokens to our queue
        from langchain.callbacks.base import BaseCallbackHandler
        class QueueStreamCallback(BaseCallbackHandler):
            def on_llm_new_token(self, token: str, **kwargs) -> None:
                if q:
                    q.put({"type": "code_token", "token": token})

        # Increment revision count if we are looping
        if feedback or runtime_error:
            state["revision_count"] = state.get("revision_count", 0) + 1
            if runtime_error:
                print(f"[Coder] Auto-Heal Triggered! Attempting to fix runtime error...")
                if q:
                    q.put({"type": "progress", "message": "Auto-Heal Triggered! Attempting to fix runtime error..."})
        
        for target_file in files_to_generate:
            if q:
                # Tell the UI we are starting a new file
                q.put({"type": "file_start", "file": target_file})
                
            # Temporarily inject the callback into self.llm for this generation
            # Note: Depending on the LLM initialization, we might need to recreate the chain
            # with streaming enabled. We'll pass the callback directly in the invoke call.
            
            # Since invoke doesn't stream by default unless the LLM is configured with streaming=True,
            # we'll use stream() instead of invoke()!
            
            # Dynamically adapt rules based on agent_role
            if "Research" in agent_role:
                framework_rules = "3. RESEARCH RULE: Write an extensive, academic, and highly detailed document for the requested file. Ensure you provide a NOVEL APPROACH with innovative ideas, avoiding generic statements. Use Markdown formatting. Do not write software code unless explicitly requested.\n4. Cite hypothetical but realistic methods where appropriate."
            elif "Fullstack" in agent_role or "Web" in agent_role or "UI" in agent_role:
                framework_rules = "3. CRITICAL PORT RULE: Your Express backend MUST run on PORT 5000. Your Vite React frontend will run on its default port, but you must configure your backend cors to accept requests.\n4. CRITICAL FRAMEWORK RULE: Write modular, clean code using React for the frontend and Node.js/Express for the backend. Use Tailwind CSS classes for styling.\n5. CRITICAL ROUTING RULE: You MUST use React Router v6 syntax. Do NOT use '<Switch>'. You MUST use '<Routes>' and '<Route path=\"/\" element={{<Component />}} />'.\n6. CRITICAL COMPONENT RULE: You MUST NOT import any components, contexts, or stores that you did not explicitly generate. If it's not in the blueprint's file_structure, DO NOT IMPORT IT.\n7. POSTGRESQL RULE: If using PostgreSQL, strictly use the connection string 'postgresql://postgres:postgres@localhost:5432/postgres'.\n8. CRITICAL BACKEND DEPENDENCY RULE: Your root 'package.json' MUST include 'express', 'cors', 'pg', 'dotenv', 'concurrently' and any other backend libraries. Its dev script MUST be: '\"dev\": \"concurrently \\\"node server.js\\\" \\\"cd client && npm run dev\\\"\"'.\n9. CRITICAL VITE RULE: The frontend is pre-scaffolded with Vite. You MUST NOT generate 'client/package.json', 'index.html', or 'main.jsx'. You ONLY generate 'client/src/App.jsx' and your custom components (e.g. 'client/src/components/Dashboard.jsx'). Every React file MUST end with '.jsx'."
            else:
                framework_rules = "3. CRITICAL PORT RULE: The app must run on port 3000 for the iframe preview.\n4. CRITICAL FRAMEWORK RULE: Write modular, clean code using the appropriate Python libraries for ML/Data Science (e.g. Pandas, Scikit-learn, PyTorch, Streamlit, FastAPI). Ensure all dependencies are documented in requirements.txt.\n5. Do NOT write React code unless explicitly requested in the blueprint. Use Streamlit for simple UIs.\n6. POSTGRESQL RULE: If using PostgreSQL, you MUST strictly use the connection string 'postgresql://postgres:postgres@localhost:5432/postgres'. Do NOT use environment variables for DB connections."

            system_prompt = f"You are a Senior AI {agent_role}. Given a blueprint and semantic context from past successful projects, write the FULL production-grade content for the requested file: {{target_file}}.\n\nIMPORTANT RULES:\n1. Output the file EXACTLY in this format:\n\n<file path=\"{{target_file}}\">\n[YOUR CODE/CONTENT HERE]\n</file>\n\n2. Do NOT use JSON. Do not use markdown backticks outside of the file tags.\n{framework_rules}\n10. If you receive Review Feedback or a Runtime Error, you must fix the issues mentioned."

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "Blueprint: {blueprint}\nSemantic Context: {context}\nTarget File: {target_file}\nReview Feedback: {review_feedback}\nRuntime Error: {runtime_error}")
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
                        runtime_error=runtime_error
                    )
                    
                    full_content = ""
                    for chunk in self.llm.stream(messages):
                        text_chunk = chunk.content
                        if isinstance(text_chunk, list):
                            text_chunk = "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in text_chunk)
                        
                        full_content += text_chunk
                        if q:
                            q.put({"type": "code_token", "token": text_chunk})
                            
                    import re
                    match = re.search(r'<file\s+path="[^"]+">(.*?)</file>', full_content, re.DOTALL)
                    if match:
                        code = match.group(1).strip()
                        
                        # CODE VALIDATION GATE
                        if target_file.endswith(".py"):
                            ast.parse(code) # Raises SyntaxError if code is fundamentally malformed
                            
                        logger.info(f"   -> [Success] Generated {target_file}")
                        code_files[target_file] = code
                        break
                    else:
                        print(f"   -> [Attempt {attempt+1}] Failed to parse XML tags for {target_file}.")
                        if attempt == max_retries - 1:
                            code_files[target_file] = f"// Error: AiON LLM failed to format {target_file} correctly"
                        
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str and attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 3
                        print(f"      - [WARNING] Rate limit hit for {target_file}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        print(f"      - [ERROR] Exception while generating {target_file}: {e}")
                        code_files[target_file] = f"// Error: AiON encountered an exception: {e}"
                        break
            
        state["code_files"] = code_files
        
        # Clear errors if generation succeeded
        state["error"] = None
        state["review_feedback"] = None
        
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
