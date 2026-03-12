# HealthAI — Intelligent Healthcare Assistant (Unified Version)

HealthAI is an advanced, AI-powered healthcare consultation system designed to automate medical intake, specialist recommendations, clinical analysis, medical coding, and the generation of structured clinical notes.

This "Unified" version combines an interactive frontend and a powerful backend powered by **FastAPI** and **LangGraph**, providing a comprehensive end-to-end medical workflow.

---

## 🚀 Features

*   **Multi-Modal Patient Input**: Accept patient complaints through direct text or file uploads (PDF, TXT, CSV).
*   **AI Generator/Critic Loop**: Employs an iterative AI loop to convert raw patient input into a verified, professional medical summary.
*   **Intelligent Specialist Recommendation**: Automatically recommends the most relevant medical specialists based on the case summary.
*   **Multi-Agent Specialist Consultation**: Uses `LangGraph` to simulate a medical board consultation, gathering insights from various specialized AI agents.
*   **Clinical Data Extraction & Coding**: Automatically extracts conditions and assigns **ICD-10-CM** codes, and extracts medications with **ATC / RxNorm** mappings.
*   **Unified Clinical Note (SOAP)**: Aggregates everything into an editable clinical note, removing generic headings and providing a clean, professional layout.
*   **Report Generation**: Download the final approved clinical note in PDF, HTML, or TXT formats, or print directly from the browser.

## 🛠️ Technology Stack

*   **Backend Application**: Python, FastAPI
*   **Agentic Framework**: [LangGraph](https://python.langchain.com/docs/langgraph/)
*   **LLM Orchestration**: LiteLLM (Supporting OpenAI natively)
*   **Frontend**: Vanilla JavaScript, HTML5, CSS3
*   **Containerization**: Docker, Docker Compose
*   **Web Server**: Nginx

## 🏗️ Project Structure

```text
healthcare-agent-unified/
├── api/                  # FastAPI & LangGraph Backend
│   ├── main.py           # FastAPI endpoints
│   ├── graph.py          # LangGraph definitions (analyze & consult workflows)
│   ├── specialists.py    # Definitions of medical specialists
│   ├── utils.py          # File processing and text extraction utilities
│   ├── requirements.txt  # Python dependencies
│   └── Dockerfile        # Backend container configuration
├── frontend/             # HTML/JS/CSS Web Interface
│   ├── index.html        # Main interface
│   ├── app.js            # Frontend logic & API integrations
│   ├── styles.css        # Responsive styling and glow effects
│   ├── nginx.conf        # Nginx configuration for serving static files
│   └── Dockerfile        # Frontend container configuration
├── docker-compose.yml    # Docker Compose orchestration
├── .env                  # Environment Variables
└── README.md             # Project documentation (this file)
```

## ⚙️ Quick Start

### Prerequisites

*   [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) installed.
*   An OpenAI API Key.

### 1. Configure Environment Variables

Create a `.env` file in the root directory and add your OpenAI API Key:

```bash
OPENAI_API_KEY="your-openai-api-key-here"
```

### 2. Run with Docker Compose

From the root of the project (`healthcare-agent-unified`), run the following command:

```bash
docker-compose up --build
```

### 3. Access the Application

Once the containers are running, you can access the application via your web browser:
*   **Frontend User Interface**: [http://localhost:3000](http://localhost:3000)
*   **FastAPI Backend & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

## 🔄 Workflow

1.  **Complaint**: Input the patient's symptoms or upload clinical case files.
2.  **Summary**: Review the professionally generated case summary by the Agentic Critic loop.
3.  **Specialists**: Adjust the system-recommended medical specialists before proceeding.
4.  **Analysis**: The system concurrently queries the selected specialists, merges their assessments, and performs automated medical extraction & coding (ICD-10 & ATC).
5.  **Clinical Note**: Edit and refine the generated clinical note. Add patient demographic details and doctor's signatures.
6.  **Report**: Format the finalized note as a clean clinical document available for export.

## 📄 License

This project is intended for demonstration, educational, and research purposes. Do not use for real clinical scenarios without direct supervision from licensed medical professionals.
