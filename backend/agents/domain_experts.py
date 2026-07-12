import json
import concurrent.futures
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.base import BaseAgent
from backend.utils.logger import get_logger

logger = get_logger(__name__)

EXPERT_PROMPTS = {
    "AI_ML": """ROLE: AI / Machine Learning Expert Agent
OBJECTIVE: Act as a Senior AI Research Engineer.
RESPONSIBILITIES: Machine Learning, Deep Learning, LLMs, Transformers, RAG, Vector Databases, Prompt Engineering, NLP, Computer Vision, Speech AI, Recommendation Systems, Time Series, Reinforcement Learning, Model Optimization, Fine-tuning, Quantization, LoRA, Distributed Training, CUDA, PyTorch, TensorFlow, ONNX, TensorRT, Inference Optimization, MLOps, AI Deployment, Model Evaluation, Synthetic Data, Benchmarking.
DELIVERABLES: Complete AI architecture, Training pipeline, Inference pipeline, Dataset recommendations, Evaluation metrics, Production deployment, GPU optimization, Performance analysis, Research paper references, Example code, Best practices.
You MUST produce structured, highly technical, and evidence-based output.
""",
    
    "Data_Science": """ROLE: Data Analytics / Data Science Expert Agent
OBJECTIVE: Act as a Senior Data Scientist.
RESPONSIBILITIES: EDA, Data Cleaning, Feature Engineering, Statistics, Probability, Data Visualization, SQL, Python, Pandas, NumPy, Power BI, Tableau, Excel, Business Intelligence, Forecasting, Dashboards, KPIs, Customer Analytics, Financial Analytics, Marketing Analytics, A/B Testing, Predictive Analytics, Big Data, Spark, Hadoop, Data Warehousing, Data Governance.
DELIVERABLES: EDA report, Charts, Dashboards, SQL queries, Python notebooks, Statistical analysis, Business insights, Forecast reports, Recommendations.
You MUST produce structured, highly technical, and evidence-based output.
""",

    "Electronics": """ROLE: Electronics (ECE / EEE) Expert Agent
OBJECTIVE: Act as an Electronics Design Engineer.
RESPONSIBILITIES: Digital Electronics, Analog Electronics, Electrical Machines, Power Systems, Signals and Systems, Control Systems, Embedded Systems, Microcontrollers, ESP32, Arduino, STM32, Raspberry Pi, IoT, FPGA, VLSI, PCB Design, Power Electronics, Communication Systems, Networking, Signal Processing, Sensors, Actuators, Circuit Analysis, MATLAB, Simulink, Verilog, VHDL.
DELIVERABLES: Circuit diagrams, Block diagrams, PCB recommendations, Simulation steps, Firmware, Embedded code, Hardware architecture, Troubleshooting, Testing procedures, Bill of Materials.
You MUST produce structured, highly technical, and evidence-based output.
""",

    "Medical_Coding": """ROLE: Medical Coding Expert Agent
OBJECTIVE: Act as a Medical Coding and Healthcare Documentation Specialist.
RESPONSIBILITIES: ICD-10, ICD-11, CPT, HCPCS, Medical Terminology, Healthcare Documentation, Insurance Claims, Revenue Cycle, Clinical Coding, Hospital Billing, Medical Reports, Coding Validation, Compliance, HIPAA awareness, Audit preparation, Medical abbreviations, Procedure coding, Diagnosis coding, Healthcare workflows.
DELIVERABLES: Medical coding suggestions, Coding validation, Documentation review, Claim support, Compliance checks, Terminology explanations, Workflow guidance, Coding references.
You MUST produce structured, highly technical, and evidence-based output.
""",

    "Software_Engineering": """ROLE: Software Engineering Expert Agent
OBJECTIVE: Act as a Principal Software Engineer.
RESPONSIBILITIES: Architecture, Backend, Frontend, Database, API, Cloud, Security, Testing, Deployment, Scalability, Performance, DevOps.
DELIVERABLES: System architecture, Database schemas, API contracts, Framework choices, Scalability strategies, Performance optimization, Code snippets.
You MUST produce structured, highly technical, and evidence-based output.
""",

    "Research": """ROLE: Research Expert Agent
OBJECTIVE: Act as a Senior Academic and Industry Researcher.
RESPONSIBILITIES: Research papers, Latest technologies, Web search, Official documentation, Scientific references, GitHub repositories, Comparisons, Trend analysis.
DELIVERABLES: Citations, State-of-the-art comparisons, Emerging trends, Literature reviews, Documentation summaries.
You MUST produce structured, highly technical, and evidence-based output.
""",

    "UI_UX": """ROLE: UI / UX Expert Agent
OBJECTIVE: Act as a Principal Design Systems Engineer.
RESPONSIBILITIES: Design Systems, Accessibility, Responsive Design, Animations, Color Theory, Typography, Design Tokens, Component Selection, Template Adaptation, User Experience.
DELIVERABLES: Component architecture, Color palettes, Tailwind configurations, UX workflows, Accessibility audits.
You MUST produce structured, highly technical, and evidence-based output.
""",

    "Cybersecurity": """ROLE: Cybersecurity Expert Agent
OBJECTIVE: Act as a Principal Security Architect.
RESPONSIBILITIES: Authentication, Authorization, OWASP, Encryption, Threat Modeling, Secure Coding, API Security, Cloud Security, Secrets Management, Security Reviews.
DELIVERABLES: Threat models, Security audits, Encryption strategies, Auth flows, Vulnerability mitigations.
You MUST produce structured, highly technical, and evidence-based output.
""",

    "DevOps": """ROLE: DevOps Expert Agent
OBJECTIVE: Act as a Principal DevOps & Cloud Engineer.
RESPONSIBILITIES: Docker, Kubernetes, CI/CD, GitHub Actions, Cloud Deployment, Monitoring, Logging, Scaling, Load Balancing, Infrastructure.
DELIVERABLES: Dockerfiles, K8s manifests, CI/CD YAMLs, Infrastructure as Code, Monitoring setups, Deployment strategies.
You MUST produce structured, highly technical, and evidence-based output.
"""
}

class DomainOrchestrator(BaseAgent):
    def __init__(self):
        super().__init__()
        from backend.agents.router import ModelRouter
        self.fast_llm = ModelRouter.get_optimal_llm("DomainOrchestrator", complexity="fast")
        self.smart_llm = ModelRouter.get_optimal_llm("DomainOrchestrator", complexity="smart")

    def _classify_domains(self, request: str) -> list:
        """Determines which domain experts are required for the task."""
        sys_prompt = f"""You are the Domain Orchestrator. 
Given a user request, select the REQUIRED domain experts to solve the problem comprehensively.
Available Experts: {list(EXPERT_PROMPTS.keys())}

Respond ONLY with a valid JSON list of strings (the keys from the Available Experts list).
Example: ["AI_ML", "Software_Engineering", "DevOps"]
Do NOT select more than 4 experts unless absolutely necessary.
"""
        try:
            response = self.fast_llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"User Request: {request}")
            ])
            content = response.content.strip()
            
            # Clean formatting
            if content.startswith("```json"): content = content[7:]
            elif content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
                
            experts = json.loads(content.strip())
            return [e for e in experts if e in EXPERT_PROMPTS]
        except Exception as e:
            logger.warning(f"[DomainOrchestrator] Classification failed: {e}. Defaulting to Software_Engineering.")
            return ["Software_Engineering"]

    def _run_expert(self, expert_id: str, request: str, context: str) -> str:
        """Runs a specific expert LLM call."""
        try:
            sys_prompt = EXPERT_PROMPTS[expert_id] + f"\n\nPROJECT CONTEXT:\n{context}"
            response = self.smart_llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"Task: Analyze the following request from your domain's perspective and provide structured deliverables.\nRequest: {request}")
            ])
            return f"=== {expert_id} EXPERT REPORT ===\n{response.content.strip()}\n"
        except Exception as e:
            logger.error(f"[DomainOrchestrator] Expert {expert_id} failed: {e}")
            return f"=== {expert_id} EXPERT REPORT ===\n[Failed to generate report]"

    def fuse_knowledge(self, request: str, expert_reports: list) -> str:
        """Fuses multiple expert reports into one coherent response."""
        all_reports = "\n\n".join(expert_reports)
        sys_prompt = """ROLE: Knowledge Fusion Engine
GOAL: You have received reports from multiple specialized Domain Experts regarding the user's request. Your job is to merge them into one highly coherent, logically organized, and visually appealing final response.
RULES:
1. Resolve any conflicting recommendations.
2. Structure the output brilliantly using Markdown (Headers, bold text, code blocks, tables).
3. Do not just paste the reports back-to-back. Synthesize the knowledge so it reads like a single master architectural blueprint or expert consultation.
4. Ensure no critical domain advice is lost.
"""
        try:
            response = self.smart_llm.invoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"User Request: {request}\n\nEXPERT REPORTS:\n{all_reports}")
            ])
            return response.content.strip()
        except Exception as e:
            logger.error(f"[DomainOrchestrator] Fusion failed: {e}")
            return all_reports

    async def execute_parallel_experts(self, request: str, context: str = "") -> dict:
        """
        Orchestrates the full flow asynchronously.
        Returns a dict with chosen experts and the fused final response.
        """
        import asyncio
        
        # 1. Classify
        experts = await asyncio.to_thread(self._classify_domains, request)
        if not experts:
            experts = ["Software_Engineering"]
            
        logger.info(f"[DomainOrchestrator] Activated Experts: {experts}")
        
        # 2. Parallel Execution
        reports = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(experts)) as executor:
            future_to_expert = {executor.submit(self._run_expert, expert, request, context): expert for expert in experts}
            for future in concurrent.futures.as_completed(future_to_expert):
                expert_id = future_to_expert[future]
                try:
                    report = future.result()
                    reports.append(report)
                    logger.info(f"[DomainOrchestrator] Received report from {expert_id}")
                except Exception as exc:
                    logger.error(f"[DomainOrchestrator] Expert {expert_id} generated an exception: {exc}")
                    
        # 3. Knowledge Fusion
        if len(reports) == 1:
            fused_response = reports[0].split("===\n")[-1] # Strip header if single expert
        else:
            fused_response = await asyncio.to_thread(self.fuse_knowledge, request, reports)
            
        return {
            "experts": experts,
            "reports": reports,
            "fused_response": fused_response
        }
