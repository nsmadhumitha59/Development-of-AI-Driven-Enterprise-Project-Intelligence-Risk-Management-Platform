# AI Project Intelligence & Risk Advisor (Milestones 1 & 2)

> **Milestones 1 & 2 Deliverables**: Document Ingestion (PDF, DOCX, CSV, TXT), RAG Retrieval with ChromaDB & SentenceTransformers, Scope & Deliverable Extraction Agent, Risk Detection & Delivery Forecasting Agent, Blocker & Action Item Agent, REST API, Web Portal, and CLI.

---

## 🌟 Capabilities Overview

### Milestone 1: Core Ingestion & RAG Subsystem
- **Multi-Format Ingestion**: PDF, DOCX, CSV, TXT / Markdown.
- **Content Normalizer**: Unicode NFKC normalization, whitespace sanitization, and structural boundary preservation ([`src/ingestion/normalizer.py`](file:///src/ingestion/normalizer.py)).
- **Chunking & Vector Indexing**: Hierarchical text splitter, SentenceTransformers (`all-MiniLM-L6-v2`, 384-dim), and persistent ChromaDB vector storage ([`src/rag/`](file:///src/rag/)).
- **Semantic Retrieval**: Cosine similarity search with score thresholding and metadata filtering ([`src/rag/retriever.py`](file:///src/rag/retriever.py)).

### Milestone 2: Specialized Intelligence Agents
1. **Scope and Deliverable Extraction Agent** ([`src/agents/scope_agent.py`](file:///src/agents/scope_agent.py)):
   - Extracts: Project goals with priority, Scope boundaries (in-scope, out-of-scope, constraints), Deliverables, Milestones, Deadlines, and Responsibility assignments.
   - Structured JSON response: `ScopeExtractionResult` with provenance tracking.
2. **Risk Detection and Delivery Forecasting Agent** ([`src/agents/risk_forecast_agent.py`](file:///src/agents/risk_forecast_agent.py)):
   - Identifies: Schedule risks, dependency bottlenecks, missing specifications, delivery challenges, and deadline risks.
   - Assigns severity: `Critical`, `High`, `Medium`, `Low` with supporting rationale and mitigations.
   - Delivery Forecast: Overall status (`On Track` / `At Risk` / `Delayed`), slippage probability percentage, and forecast factors.
3. **Blocker and Action Item Identification Agent** ([`src/agents/blocker_action_agent.py`](file:///src/agents/blocker_action_agent.py)):
   - Extracts: Active blockers, pending architectural/product decisions, unresolved issues, and action items with assignees and due dates.
4. **Milestone 2 Multi-Agent Orchestrator** ([`src/agents/orchestrator.py`](file:///src/agents/orchestrator.py)):
   - Combines and synthesizes all 3 agents into a unified project intelligence report with executive summary.

---

## 🚀 Quickstart Guide

### 1. Launching the Web Portal & API Server

```bash
python run.py serve --port 8000
```

- **Interactive Web Portal**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger API Interactive Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Specification**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🛠️ Command-Line Interface (CLI)

```bash
# Ingest documents
python run.py ingest path/to/document.pdf
python run.py ingest path/to/sprint_tasks.csv

# Run Milestone 2 Agents directly from CLI
python run.py agent scope                     # Run Scope & Deliverable Agent
python run.py agent risk                      # Run Risk Detection & Delivery Forecast Agent
python run.py agent blockers                  # Run Blocker & Action Item Agent
python run.py agent all --focus "Sprint 4"    # Run Full Multi-Agent Pipeline with focus

# Perform semantic search
python run.py query "Who is responsible for the authentication module?" --top-k 5

# View system knowledge base stats
python run.py stats
```

---

## 📡 REST API Reference

### Milestone 1 Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/documents/upload` | Upload & index documents (PDF, DOCX, CSV, TXT) |
| `GET` | `/api/v1/documents` | List all ingested documents |
| `GET` | `/api/v1/documents/{id}` | Get document metadata and preview |
| `DELETE` | `/api/v1/documents/{id}` | Delete document and vector embeddings |
| `POST` | `/api/v1/rag/query` | Semantic vector retrieval with scores |
| `GET` | `/api/v1/health` | System health and vector metrics |

### Milestone 2 Agent Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/agents/scope` | Run Scope & Deliverable Extraction Agent |
| `POST` | `/api/v1/agents/risk-forecast` | Run Risk Detection & Delivery Forecasting Agent |
| `POST` | `/api/v1/agents/blockers-actions` | Run Blocker & Action Item Identification Agent |
| `POST` | `/api/v1/agents/analyze-all` | Run all 3 agents and get unified synthesis |

---

## 🧪 Automated Testing (27 Tests Passing)

Run the full automated test suite with pytest:

```bash
.venv\Scripts\pytest -v
```

### Test Coverage Summary:
- **`tests/test_agent_api.py`**: API endpoint tests for `/api/v1/agents/scope`, `/api/v1/agents/risk-forecast`, `/api/v1/agents/blockers-actions`, `/api/v1/agents/analyze-all`.
- **`tests/test_agent_validation.py`**: Multi-format validation across PDF, DOCX, CSV, TXT and grounding reference verification.
- **`tests/test_scope_agent.py`**: Goal extraction, scope boundaries, deliverables, and milestones.
- **`tests/test_risk_forecast_agent.py`**: Risk categorization, severity scoring, mitigations, and delivery forecasting.
- **`tests/test_blocker_action_agent.py`**: Active blockers, pending decisions, and action items with assignees/dates.
- **`tests/test_ingestion.py`**, **`test_chunking.py`**, **`test_embeddings.py`**, **`test_vectorstore.py`**, **`test_retrieval.py`**, **`test_api.py`**: Core Milestone 1 test suite.

---

## 🛡️ Milestone Boundary Compliance

- **Implemented**: Milestone 1 (Document Ingestion & RAG) and Milestone 2 (Scope Extraction Agent, Risk & Delivery Forecast Agent, Blocker & Action Item Agent, Multi-Agent Orchestrator, Grounding Validation, REST API, Web UI, Test Suite).
- **Excluded (Deferred to Milestone 3)**: Project Health Scoring, Documentation Generation, and Conversational Assistant.
