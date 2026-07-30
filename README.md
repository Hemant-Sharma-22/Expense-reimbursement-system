# Production-Ready Expense Reimbursement System Backend & AI Policy Assistant (RAG)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python 3.12](https://img.shields.io/badge/Python-3.12+-3776AB.svg?style=flat&logo=python)](https://python.org)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=python)](https://www.sqlalchemy.org/)
[![Tests](https://img.shields.io/badge/Tests-23%20Passed%20(100%25)-brightgreen.svg)](https://pytest.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A robust, enterprise-grade Expense Reimbursement System backend built using **FastAPI**, **SQLAlchemy ORM (2.0)**, **SQLite**, **Pydantic (v2)**, and an **AI-powered RAG Assistant** that answers corporate expense policy questions grounded strictly in provided policy documents.

---

## 📸 Interactive API Screenshots & System Gallery

### 1. OpenAPI Documentation Header & Features (`/docs`)
![Swagger Header & Description](docs/screenshots/swagger_header_description.png)

### 2. Interactive Endpoint Router Groups
![Swagger Endpoints Overview](docs/screenshots/swagger_endpoints_overview.png)

### 3. OAuth2 Authentication Modal & Login Flow
| OAuth2 Credentials Login Form | OAuth2 Authorized Session State |
|---|---|
| ![OAuth2 Login Form](docs/screenshots/oauth2_login_form.png) | ![OAuth2 Authentication Modal](docs/screenshots/oauth2_authentication_modal.png) |

### 4. API Responses & Payloads
| User Profile Payload (`GET /api/v1/auth/me`) | Department Summary Payload (`GET /api/v1/departments/`) |
|---|---|
| ![User Profile API Response](docs/screenshots/user_profile_response.png) | ![Department List API Response](docs/screenshots/departments_response.png) |

### 5. System Health Check Endpoint (`GET /`)
![System Health Check Response](docs/screenshots/health_check_response.png)

---

## 🧪 CLI Setup & Automated Test Suite

### 1. Database Seeder Script Execution (`seed_data.py`)
![Database Seeding CLI Execution](docs/screenshots/database_seeding_cli.png)

### 2. Automated Test Suite Execution (`pytest -v`)
![Pytest Execution Results](docs/screenshots/pytest_execution_results.png)

---

## 🏛️ Architecture Overview

```mermaid
graph TD
    subgraph Client Layer
        Employee["👤 Employee"]
        Manager["👔 Manager / Admin"]
    end

    subgraph API Gateway & Auth
        FastAPI["⚡ FastAPI Framework"]
        OAuth2["🔐 OAuth2 & JWT Auth Guard"]
        RBAC["🛡️ RBAC Middleware (Employee/Manager/Admin)"]
    end

    subgraph Core Business Services
        ExpenseSvc["🧾 Expense Service"]
        DupSvc["🔍 Duplicate Detector Engine"]
        ManagerSvc["📊 Manager & Analytics Service"]
        AuditSvc["📜 Audit Trail Logger"]
        RAGSvc["🤖 AI Policy Assistant (RAG Engine)"]
    end

    subgraph Persistence & Knowledge Base
        DB[("🗄️ SQLite Database")]
        Uploads["📁 Receipt File Storage"]
        Policies["📚 Policy Documents (Markdown/PDF KB)"]
    end

    Employee -->|HTTP / JSON| OAuth2
    Manager -->|HTTP / JSON| OAuth2
    OAuth2 --> RBAC
    RBAC --> FastAPI

    FastAPI --> ExpenseSvc
    FastAPI --> ManagerSvc
    FastAPI --> RAGSvc

    ExpenseSvc --> DupSvc
    ExpenseSvc --> AuditSvc
    ManagerSvc --> AuditSvc

    ExpenseSvc --> DB
    ExpenseSvc --> Uploads
    ManagerSvc --> DB
    AuditSvc --> DB
    RAGSvc --> Policies
```

---

## 🤖 RAG Engine Architecture & Bonus Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor Employee
    participant API as FastAPI Policy Assistant
    participant RAG as RAG Service Engine
    participant Reranker as 2-Pass RRF Reranker
    participant KB as Policy Documents (Markdown / PDF)
    
    Employee->>API: POST /api/v1/policy-assistant/query ("What is meal limit?")
    API->>RAG: Tokenize & Expand Query (Synonyms)
    RAG->>KB: Hybrid Retrieval (BM25 + Title Boost)
    KB-->>RAG: Return Top Candidate Chunks
    RAG->>Reranker: Apply Reciprocal Rank Fusion (RRF) & Exact Match Reranking
    Reranker-->>RAG: Reranked Top-K Chunks
    alt Relevant Context Found (Score >= Threshold)
        RAG-->>API: Synthesize Grounded Answer + Citations
        API-->>Employee: Grounded Answer + [Document & Section Citations]
    else Missing Context / Low Relevance
        RAG-->>API: Grounded Fallback
        API-->>Employee: "Sufficient information could not be found..."
    end
```

---

## ❓ Sample Questions and Outputs

### Sample Question 1: Daily Meal Allowance Limit Query
**Request**: `POST /api/v1/policy-assistant/query`
```json
{
  "query": "What is the daily meal allowance limit?"
}
```

**Response**:
```json
{
  "answer": "**According to the Expense Policy (Meals & Entertainment):**\nIndividual Meal Allowance: Up to $75.00 USD per day for employee meals during business travel or approved overtime work. Detailed receipts itemizing all food and beverage purchases are mandatory.",
  "citations": [
    {
      "document_name": "Expense Policy",
      "section_title": "Meals & Entertainment",
      "excerpt": "Individual Meal Allowance: Up to $75.00 USD per day for employee meals during business travel or approved overtime work...",
      "relevance_score": 0.942
    }
  ],
  "grounded": true,
  "query": "What is the daily meal allowance limit?"
}
```

---

### Sample Question 2: International Business Class Flight Policy
**Request**: `POST /api/v1/policy-assistant/query`
```json
{
  "query": "Can I book business class for international flights?"
}
```

**Response**:
```json
{
  "answer": "**According to the Travel Policy (Flight Bookings):**\nBusiness class travel is strictly prohibited for domestic flights and short-haul international flights under 8 hours total duration. Business class may be requested only for continuous international flights exceeding 8 hours with VP approval.",
  "citations": [
    {
      "document_name": "Travel Policy",
      "section_title": "Flight Bookings",
      "excerpt": "Business class travel is strictly prohibited for domestic flights and short-haul international flights under 8 hours...",
      "relevance_score": 0.885
    }
  ],
  "grounded": true,
  "query": "Can I book business class for international flights?"
}
```

---

### Sample Question 3: Missing Information / Fallback (Zero Hallucination)
**Request**: `POST /api/v1/policy-assistant/query`
```json
{
  "query": "What is the corporate policy on bringing your pet to work?"
}
```

**Response**:
```json
{
  "answer": "Sufficient information could not be found in the provided policy documents to answer your question.",
  "citations": [],
  "grounded": false,
  "query": "What is the corporate policy on bringing your pet to work?"
}
```

---

## 🎯 Design Decisions

1. **FastAPI & Pydantic v2**: Chosen for lightning-fast async performance, automatic OpenAPI/Swagger schema generation, and strict data validation.
2. **Direct bcrypt Password Hashing**: Directly utilizes `bcrypt.hashpw` and `bcrypt.checkpw` to eliminate Python 3.12 passlib compatibility issues.
3. **Multi-Tier Duplicate Prevention Engine**:
   - Tier 1: SHA-256 cryptographic file digest comparison for uploaded receipt files.
   - Tier 2: Exact tuple matching (`employee_id`, `merchant`, `amount`, `expense_date`).
   - Tier 3: Time-window heuristic match checking (±3 days) to detect overlapping submissions.
4. **Hybrid RAG Retrieval with 2-Pass Reranking**:
   - Stage 1: Sparse keyword matching combined with domain synonym query expansion.
   - Stage 2: Reciprocal Rank Fusion (RRF) and exact phrase alignment reranking.
5. **Atomic Audit Logging**: Implements a dedicated `AuditService` that intercepts all state mutations and logs actor ID, action, resource type, and JSON metadata diffs.

---

## 📝 Assumptions

1. **Currency Standardization**: All expense amounts and policy limits are assumed to be in **USD**.
2. **Policy Knowledge Base Format**: Corporate policy documents are stored as Markdown (`.md`) or PDF (`.pdf`) files inside the `policies/` directory.
3. **Receipt Files**: Receipts are stored locally in the `uploads/` directory with SHA-256 checksums calculated prior to storage.
4. **Department Hierarchy**: Users belong to a primary department (`Engineering`, `Sales`, `Marketing`), and managers approve requests submitted within their department.

---

## ⚖️ Trade-offs

| Decision | Trade-off Made | Rationale |
|---|---|---|
| **In-Memory RAG vs External Vector DB** | Used in-memory BM25 + RRF index over ChromaDB/Qdrant | Zero external daemon dependency, zero setup overhead, instant sub-millisecond execution for policy documents |
| **BM25 + RRF Reranking vs Cross-Encoder** | Used hybrid token matching with RRF reranker over heavy neural Cross-Encoder | Avoids 2GB+ PyTorch model downloads and GPU requirements while delivering high relevance precision |
| **SQLite vs PostgreSQL** | Used SQLite with SQLAlchemy ORM over PostgreSQL | Enables instant out-of-the-box local execution and lightweight embedded testing |

---

## 🚀 Improvements You Would Make with More Time

1. **Persistent Vector Database**: Integrate **Qdrant** or **pgvector** for persistent vector embeddings across millions of policy chunks.
2. **LLM Synthesis Integration**: Connect to Google Gemini API via Firebase AI Logic / Google GenAI SDK for multi-sentence re-synthesis of retrieved contexts.
3. **OCR Engine Integration**: Integrate `pytesseract` or Google Cloud Vision API to perform full OCR on scanned paper receipts and image-only PDF files.
4. **Async Task Queue**: Implement Celery or ARQ with Redis for asynchronous background processing of receipt hashing and document indexing.

---

## 🎯 Bonus Features Summary

- [x] **Hybrid Search**: Sparse term frequency + title relevance scoring.
- [x] **Metadata Filtering**: Scope queries by specific document name (`document_filter`).
- [x] **Query Expansion**: Automatic domain synonym expansion ("flight" -> "airfare/airline", "meal" -> "food/lunch").
- [x] **Reranking**: Reciprocal Rank Fusion (RRF) 2-pass candidate reranker.
- [x] **OCR & PDF Support**: Text extraction from `.pdf` files in knowledge base.
- [x] **Incremental Indexing**: File modification timestamp (`mtime`) tracking.
- [x] **Feedback Mechanism**: User rating & comments endpoint (`POST /api/v1/policy-assistant/feedback`).
- [x] **Streaming Responses**: Server-Sent Events token streaming (`POST /api/v1/policy-assistant/stream`).

---

## ⚡ Setup & Run Instructions

### 1. Environment Setup

```bash
cd expense_reimbursement_system
python -m venv .venv

# Activate venv:
.venv\Scripts\activate      # Windows
source .venv/bin/activate    # Linux/macOS

pip install -r requirements.txt
```

### 2. Seed Database

```bash
python seed_data.py
```

### 3. Run Automated Test Suite (23 Passed)

```bash
pytest -v
```

### 4. Launch Application Server

```bash
uvicorn app.main:app --reload --port 8000
```

- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`
