# 🌾 Tamil Nadu Government Agricultural Schemes Knowledge Graph RAG (KG-RAG)

An enterprise-grade, deterministic Knowledge Graph Retrieval-Augmented Generation (KG-RAG) system built for citizen inquiries regarding Tamil Nadu Government Agriculture & Farmers Welfare Department schemes.

The pipeline scrapes official government scheme documents, structures them into typed graph entities and relationships via LLM function calling, persists them into a dual-storage backend (Neo4j AuraDB primary and NetworkX in-memory fallback), enforces a three-tier guardrail validation defense, benchmarks retrieval quality using DeepEval, and serves grounded answers through a FastAPI REST service and a Streamlit UI.

---

## 🏛️ System Architecture

```text
 ┌────────────────────────────────────────────────────────┐
 │ Official TN Agriculture Portal (tn.gov.in)             │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼  [Step 1: Playwright Deep Crawler]
 ┌────────────────────────────────────────────────────────┐
 │ Raw Scheme Data (data/raw/tn_agriculture_schemes.json) │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼  [Step 2: LLM Structured Triple Extractor]
 ┌────────────────────────────────────────────────────────┐
 │ Typed Knowledge Graph Triples                          │
 │ (Scheme, Department, Beneficiary, Benefit, Criteria)   │
 └───────────────────────────┬────────────────────────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   [ Neo4j AuraDB Store ]          [ NetworkX Memory Store ]
   • Cloud graph persistence       • In-memory MultiDiGraph
   • Schema constraints & Cypher   • Zero-cloud local fallback
            │                                 │
            └────────────────┬────────────────┘
                             │
                             ▼  [Step 3: BaseGraphStore Abstract Interface]
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ 3-Tier Guardrail Verification Pipeline                                  │
 │                                                                         │
 │  1. Input Guardrail     ──► Blocks prompt/Cypher injections & OOD queries│
 │  2. Retrieval Guardrail ──► Enforces tn.gov.in domain & evidence checks │
 │  3. Output Guardrail    ──► Eliminates hallucinations against subgraphs │
 └───────────────────────────┬─────────────────────────────────────────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
  [ FastAPI REST Engine ]           [ Streamlit Interactive UI ]
  • GET  /health (monitoring)       • Real-time graph store toggle
  • POST /query  (KG-RAG execution) • Guardrail audit inspector
  • POST /ingest (async background) • Subgraph triples & citations
```

---

## ✨ Key Features

- **Playwright Dynamic Crawler**: Resilient headless browser scraping handling department pagination, dynamic tables, and scheme detail extraction.
- **Pydantic Structured Graph Modeling**: Deterministic triple generation mapping schemes, government departments, beneficiary demographics, eligibility rules, and procedural application steps.
- **Dual-Storage Engine (`BaseGraphStore`)**:
  - **Neo4j AuraDB**: Cloud graph database using `MERGE` upserts, uniqueness constraints, and targeted Cypher traversals.
  - **NetworkX**: In-memory Directed Multigraph supporting local zero-cloud execution and JSON disk persistence.
- **3-Tier Production Guardrails**:
  - **Input**: Heuristic and semantic detection of adversarial injections, Cypher syntax tampering, and out-of-scope inquiries.
  - **Retrieval**: Validation of extracted context against authorized government domains (`tn.gov.in`).
  - **Output**: Subgraph-grounding auditor ensuring zero hallucinations and mandatory official citations.
- **Scientific Evaluation**: DeepEval test suite benchmarking Answer Relevancy, Faithfulness, and Contextual Relevancy.
- **Async Execution**: Non-blocking background worker for on-demand web crawling and knowledge graph updates.
- **Interactive UI**: Streamlit web frontend featuring live backend switching, chat clearing, and audit metadata inspection.

---

## 📁 Repository Structure

```text
KG_RAG/
├── api/
│   ├── __init__.py
│   └── app.py                     # FastAPI REST API with lifespan context & endpoints
├── config/
│   ├── __init__.py
│   └── settings.py                # Pydantic Settings management (.env loader)
├── data/
│   └── raw/
│       ├── tn_agriculture_schemes.json    # Scraped government scheme documents
│       ├── knowledge_graph_extracted.json # Extracted nodes and relationships
│       └── networkx_graph.json            # Persisted NetworkX graph state
├── extraction/
│   ├── __init__.py
│   ├── schemas.py                 # Pydantic entity and relation schemas
│   └── extractor.py               # Structured LLM triple extraction pipeline
├── evaluation/
│   ├── __init__.py
│   └── evaluate_rag.py            # DeepEval quantitative benchmarking harness
├── frontend/
│   └── app.py                     # Streamlit web user interface
├── generation/
│   ├── __init__.py
│   └── chain.py                   # Context synthesis chain with guardrail orchestration
├── graph/
│   ├── __init__.py
│   ├── base.py                    # BaseGraphStore abstract interface
│   ├── neo4j_store.py             # Neo4j AuraDB implementation with Cypher queries
│   ├── networkx_store.py          # NetworkX in-memory graph store implementation
│   ├── ingest_neo4j.py            # CLI script to load extracted graph into Neo4j
│   └── ingest_networkx.py         # CLI script to load extracted graph into NetworkX
├── guardrails/
│   ├── __init__.py
│   └── validator.py               # 3-tier validation (Input, Retrieval, Output)
├── ingestion/
│   ├── __init__.py
│   └── tn_scraper.py              # Playwright deep crawler for TN schemes
├── tests/
│   ├── __init__.py
│   └── test_api.py                # Automated pytest API & guardrail test suite
├── conftest.py                    # Pytest environment & path configuration
├── run_all_tests.py               # Unified test runner with terminal reporting
├── requirements.txt               # Pinned project dependencies
└── .env                           # Environment configuration file
```

---

## 🛠️ Prerequisites & Installation

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.10 through 3.14)
- An active **OpenAI API Key**
- A **Neo4j AuraDB** instance (free tier available at [neo4j.com/cloud/aura](https://neo4j.com/cloud/aura/))

### 2. Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/your-username/KG_RAG.git
cd KG_RAG

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```env
# OpenAI LLM
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL_NAME=gpt-4o-mini
TEMPERATURE=0.0

# Neo4j AuraDB Cloud
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-secure-database-password

# Application Settings
DATA_DIR=data/raw
API_PORT=8000
```

---

## 🚀 Step-by-Step Pipeline Execution

### Step 1: Scrape Scheme Records
Crawl the Tamil Nadu Government portal to collect official agricultural schemes:
```bash
python -m ingestion.tn_scraper
```
*Output: `data/raw/tn_agriculture_schemes.json`*

### Step 2: Extract Knowledge Graph Triples
Execute structured LLM extraction to generate typed nodes and relationships:
```bash
python -m extraction.extractor
```
*Output: `data/raw/knowledge_graph_extracted.json`*

### Step 3: Populate Graph Stores

**Load into Neo4j AuraDB:**
```bash
python -m graph.ingest_neo4j
```

**Load into NetworkX In-Memory Store:**
```bash
python -m graph.ingest_networkx
```
*Output: `data/raw/networkx_graph.json`*

### Step 4: Run DeepEval Quality Benchmarks
Evaluate Answer Relevancy, Faithfulness, and Contextual Relevancy against gold-standard test sets:
```bash
python -m evaluation.evaluate_rag
```

---

## 🧪 Automated Testing

Execute the test suite covering health probes, factual queries across both backends, prompt injection defenses, Cypher attacks, and out-of-scope refusals:

```bash
python run_all_tests.py
```

*Or run via pytest directly:*
```bash
python -m pytest tests/test_api.py -v
```

---

## 🌐 Running the Application

### 1. Launch FastAPI Backend
```bash
uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload
```
- **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 2. Launch Streamlit Frontend
In a second terminal (with virtual environment active):
```bash
streamlit run frontend/app.py
```
- **Streamlit Web UI**: [http://localhost:8501](http://localhost:8501)

---

## 📡 API Reference

### 1. Health Probe
```http
GET /health?backend={neo4j|networkx}
```
**Sample Response:**
```json
{
  "status": "healthy",
  "backend": "neo4j",
  "stats": {
    "total_nodes": 20,
    "total_relationships": 28,
    "labels": ["Scheme", "Department", "BeneficiaryGroup", "Benefit", "EligibilityCriteria", "ApplicationStep"]
  }
}
```

### 2. Query Knowledge Graph
```http
POST /query
Content-Type: application/json

{
  "question": "What are the eligibility criteria and benefits of Training to Farmers?",
  "backend": "neo4j"
}
```
**Sample Response:**
```json
{
  "question": "What are the eligibility criteria and benefits of Training to Farmers?",
  "answer": "All maize-growing farmers across designated districts are eligible with preference to small/marginal farmers, ensuring 24% flow to SC/ST and 20% to women farmers. The scheme provides a Rs.300 subsidy per farmer for 2 days.",
  "guardrail_status": "PASSED_ALL_GUARDRAILS",
  "schemes_matched": ["Training to Farmers"],
  "source_urls": ["https://www.tn.gov.in/scheme_details.php?id=MTU2Ng=="],
  "backend_used": "neo4j"
}
```

### 3. Background Ingestion
```http
POST /ingest?limit=5
```
**Sample Response:**
```json
{
  "status": "accepted",
  "message": "Scheme ingestion task initiated in background.",
  "target_schemes_limit": 5
}
```

---

## 🛡️ Guardrail Rules & Policy

| Guardrail Layer | Detection Scope | Action on Violation |
|---|---|---|
| **Input Guardrail** | Prompt injection attacks, Cypher manipulation (`MATCH (n) DETACH DELETE`), system overrides, inputs `< 3` or `> 800` characters | Return `BLOCKED_INPUT` with sanitized security notification |
| **Retrieval Guardrail** | Unauthorized source domains (outside `*.tn.gov.in`), empty graph retrieval results | Return `BLOCKED_RETRIEVAL` with standard insufficient-information fallback |
| **Output Guardrail** | Unsupported claims, fabricated subsidies, ungrounded procedural advice | Flag `BLOCKED_OUTPUT_HALLUCINATION` and emit strict grounded fallback |

---

## 📄 License
This project is licensed under the Apache 2.0 License.