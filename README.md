# AiON: The Autonomous Multi-Agent Software Engineer

### 🧠 Summary: The Big Picture

AiON is a Python-based **multi-agent system** that uses LangGraph for orchestration, a **React** frontend, and a **Node.js/PostgreSQL** backend stack. To use it, you'll need a modern computer, an internet connection for AI models (unless you go fully offline), and to install specific software.

---

### 💻 1. Hardware Requirements

| Component | Minimum | Recommended | Why? |
| :--- | :--- | :--- | :--- |
| **Processor (CPU)** | Intel Core i5 (8th gen) / AMD Ryzen 5 (3000+) | Intel Core i7 / AMD Ryzen 7 (or newer) | For running the backend agents and the Node.js server. |
| **Memory (RAM)** | 16 GB | 32 GB+ | For running the orchestrator, multiple agents, and databases simultaneously. |
| **Storage** | 50 GB free space | 150 GB+ SSD | For the project, databases (PostgreSQL, ChromaDB), and large AI models if you run them locally. |
| **Graphics (GPU)** | Not strictly required (cloud APIs are recommended) | NVIDIA GPU with 8-12GB+ VRAM | Essential if you plan to run large AI models (like Llama 3) entirely offline using Ollama. |

### 🛠️ 2. Core Software Requirements

**A. Development Environment**
*   **Python**: Version **3.11 or higher**.
*   **Node.js & npm**: Version **20+** for the backend and frontend.
*   **Git**: For version control and cloning the project.
*   **A Code Editor**: Like VS Code or Cursor itself.

**B. AiON's Technology Stack**
*   **Backend Framework**: **FastAPI** (Python).
*   **Database**: **PostgreSQL**.
*   **Cache & Message Broker**: **Redis**.
*   **Frontend**: **React** with **Vite** as the build tool.

### 🔑 3. API & Model Requirements

The core of AiON is its AI agents, which need to be powered by LLMs. You have two paths:

*   **Option 1: Cloud APIs (Recommended for Simplicity)**
    You will need at least one active API key from a provider. Popular choices include:
    *   **NVIDIA NIM**: Offers a generous free tier with access to models like Llama 3.1 70B.
    *   **OpenAI**: For access to models like GPT-4o.
    *   **Groq**: Known for its extremely fast inference, with a good free tier.
    *   **Google Gemini**: Another strong option with a free tier.

*   **Option 2: Offline (Local) Models (Requires More Power)**
    If you want to run everything offline without API costs, you can use a local LLM runner like **Ollama**. This will require a powerful machine (as mentioned in the Hardware section) and downloading large model files (often ~10GB+ per model).

### 🐳 4. Infrastructure & Deployment Requirements

*   **Docker & Docker Compose**: Highly recommended for an easier setup of dependencies like PostgreSQL and Redis.
*   **Cloud Account (Optional)**: If you want to deploy the final app to the cloud for others to see, you'll need accounts with services like Vercel, AWS, or Railway.

### 🧩 5. Project-Specific Dependencies

The project will have its own Python and JavaScript dependencies, which are usually managed via:

*   **Python**: `pip install -r requirements.txt` (this will include libraries like `langchain`, `langgraph`, `fastapi`, `neo4j`, `sqlalchemy`, `redis`, etc.).
*   **Node.js**: `npm install` in both the root and `client/` directories.

### 📊 6. Other Important Requirements

*   **Internet Connection**: Necessary for downloading dependencies and using cloud-based AI APIs.
*   **A GitHub Account (Optional)**: Useful for version control and pushing the generated projects automatically.
