import json
import asyncio
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.base import BaseAgent
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class DomainOrchestrator(BaseAgent):
    """
    The yAI Quantum Orchestrator (formerly DomainOrchestrator).
    Implements Dynamic Swarm Synthesis, Fractal Planning (DAG), and Meta-Cognitive verification.
    """
    def __init__(self):
        super().__init__()
        from backend.agents.router import ModelRouter
        self.fast_llm = ModelRouter.get_optimal_llm("DomainOrchestrator", complexity="fast")
        self.smart_llm = ModelRouter.get_optimal_llm("DomainOrchestrator", complexity="smart")

    async def _generate_fractal_plan(self, request: str, context: str) -> Dict[str, Any]:
        """Dynamically synthesizes a JSON Directed Acyclic Graph (DAG) of micro-agents."""
        sys_prompt = """You are the yAI Fractal Planning Engine.
Your job is to analyze the user's complex request and synthesize a Dynamic Swarm of hyper-specialized micro-agents to solve it.
You MUST output a valid JSON dependency graph (DAG) representing the plan.

Schema Requirements:
{
  "nodes": [
    {
      "id": "agent_identifier_string",
      "role": "Highly specific expert role (e.g., Database_Schema_Architect, Auth_Security_Specialist)",
      "task": "Specific instructions for what this agent must produce.",
      "depends_on": ["list_of_agent_ids_this_node_waits_for"]
    }
  ]
}

Rules:
1. Break down the request into 3 to 6 highly specialized agents. Do not just use generic roles.
2. Ensure the `depends_on` arrays create a logical execution order. (e.g., frontend depends on API design).
3. At least one node should have an empty `depends_on` array to start the graph.
4. Output ONLY valid JSON."""

        try:
            response = await self.fast_llm.ainvoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"User Request: {request}\nContext: {context}")
            ])
            content = response.content.strip()
            
            # Clean formatting
            if content.startswith("```json"): content = content[7:]
            elif content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
                
            plan = json.loads(content.strip())
            return plan
        except Exception as e:
            logger.warning(f"[QuantumOrchestrator] Fractal planning failed: {e}. Defaulting to basic plan.")
            return {
                "nodes": [
                    {"id": "software_architect", "role": "Principal Software Architect", "task": "Analyze the request and provide a comprehensive architectural solution.", "depends_on": []}
                ]
            }

    async def _run_micro_agent(self, node: Dict[str, Any], request: str, context: str, message_bus: Dict[str, str]) -> str:
        """Executes a single dynamically synthesized micro-agent."""
        agent_id = node['id']
        role = node['role']
        task = node['task']
        dependencies = node.get('depends_on', [])
        
        # Pull data from upstream agents via the Message Bus
        dependency_data = ""
        if dependencies:
            dependency_data = "\n".join([f"--- INPUT FROM {dep} ---\n{message_bus.get(dep, '')}" for dep in dependencies])

        sys_prompt = f"""ROLE: {role}
You are a highly specialized micro-agent running inside the yAI Quantum Orchestrator.
Your specific task in the greater plan is: {task}

GLOBAL PROJECT REQUEST: {request}
GLOBAL CONTEXT: {context}

DEPENDENCY INPUTS (Read carefully, you must integrate with this upstream work):
{dependency_data}

Provide highly structured, expert-level output that strictly fulfills your assigned task."""

        try:
            response = await self.smart_llm.ainvoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content="Execute your assigned task.")
            ])
            return response.content.strip()
        except Exception as e:
            logger.error(f"[QuantumOrchestrator] Micro-Agent {agent_id} failed: {e}")
            return f"[Error: {agent_id} failed to generate output]"

    async def _overseer_verify(self, node: Dict[str, Any], output: str) -> Dict[str, Any]:
        """Meta-Cognitive Overseer checks if the agent hallucinated or failed its task."""
        sys_prompt = f"""You are the Meta-Cognitive Overseer.
Your job is to verify if a micro-agent successfully completed its assigned task without hallucinating or going off-topic.

Agent Role: {node['role']}
Assigned Task: {node['task']}

Review the Agent's Output and respond with valid JSON:
{{
  "verified": true or false,
  "feedback": "If false, explain exactly what the agent missed or did wrong so it can retry. If true, leave empty."
}}"""
        try:
            response = await self.fast_llm.ainvoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"Agent Output:\n{output}")
            ])
            content = response.content.strip()
            if content.startswith("```json"): content = content[7:]
            elif content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            return json.loads(content.strip())
        except Exception as e:
            logger.warning(f"[QuantumOrchestrator] Overseer failed: {e}. Defaulting to verified.")
            return {"verified": True, "feedback": ""}

    async def fuse_knowledge(self, request: str, message_bus: Dict[str, str]) -> str:
        """Fuses all message bus outputs into the final beautifully formatted response."""
        all_reports = "\n\n".join([f"=== {agent_id} ===\n{output}" for agent_id, output in message_bus.items()])
        sys_prompt = """ROLE: Knowledge Fusion Engine
GOAL: You have received outputs from a dynamic swarm of specialized micro-agents regarding the user's request. Your job is to merge them into one highly coherent, logically organized, and visually stunning final response.
RULES:
1. Resolve any conflicting data.
2. Structure the output brilliantly using rich Markdown (Headers, bold text, code blocks, tables).
3. Do not just paste the reports back-to-back. Synthesize the knowledge so it reads like a single master architectural blueprint or expert consultation.
4. Ensure no critical domain advice is lost.
"""
        try:
            response = await self.smart_llm.ainvoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"User Request: {request}\n\nSWARM OUTPUTS:\n{all_reports}")
            ])
            return response.content.strip()
        except Exception as e:
            logger.error(f"[QuantumOrchestrator] Fusion failed: {e}")
            return all_reports

    async def execute_parallel_experts(self, request: str, context: str = "") -> dict:
        """
        Executes the Quantum Orchestrator Pipeline (Fractal DAG execution).
        Returns a dict with chosen experts and the fused final response.
        """
        logger.info(f"[QuantumOrchestrator] Generating Fractal Plan...")
        
        # 1. Fractal Planning
        plan = await self._generate_fractal_plan(request, context)
        nodes = plan.get("nodes", [])
        
        if not nodes:
             nodes = [{"id": "software_architect", "role": "Principal Software Architect", "task": "Analyze request.", "depends_on": []}]
             
        # Extract expert roles for UI
        experts_list = [node['role'] for node in nodes]
        logger.info(f"[QuantumOrchestrator] Synthesized Micro-Agents: {experts_list}")
        
        # 2. Graph Execution Loop & Message Bus
        message_bus = {}
        completed_nodes = set()
        pending_nodes = {node['id']: node for node in nodes}
        
        async def execute_node_with_retry(node: Dict[str, Any], max_retries: int = 2):
            agent_id = node['id']
            for attempt in range(max_retries):
                logger.info(f"[QuantumOrchestrator] Running {agent_id} (Attempt {attempt+1})")
                output = await self._run_micro_agent(node, request, context, message_bus)
                
                # Verify
                verification = await self._overseer_verify(node, output)
                if verification.get("verified", True):
                    message_bus[agent_id] = output
                    completed_nodes.add(agent_id)
                    logger.info(f"[QuantumOrchestrator] {agent_id} verified and completed.")
                    return
                else:
                    logger.warning(f"[QuantumOrchestrator] {agent_id} failed verification: {verification.get('feedback')}")
            
            # If all retries fail, accept the last output anyway to prevent hanging
            logger.error(f"[QuantumOrchestrator] {agent_id} exhausted retries. Forcing completion.")
            message_bus[agent_id] = output
            completed_nodes.add(agent_id)

        # Execution Engine
        while pending_nodes:
            ready_to_run = []
            for node_id, node in pending_nodes.items():
                dependencies = node.get("depends_on", [])
                if all(dep in completed_nodes for dep in dependencies):
                    ready_to_run.append(node_id)
            
            if not ready_to_run:
                logger.error("[QuantumOrchestrator] Deadlock detected in DAG. Forcing completion of remaining nodes.")
                break
                
            tasks = []
            for node_id in ready_to_run:
                tasks.append(execute_node_with_retry(pending_nodes[node_id]))
                
            await asyncio.gather(*tasks)
            
            for node_id in ready_to_run:
                del pending_nodes[node_id]

        # 3. Knowledge Fusion
        logger.info("[QuantumOrchestrator] Fusing Knowledge...")
        fused_response = await self.fuse_knowledge(request, message_bus)
            
        return {
            "experts": experts_list,
            "fused_response": fused_response
        }
