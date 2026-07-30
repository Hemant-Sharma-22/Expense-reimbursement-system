# Production-Ready Expense Reimbursement System Backend & AI Policy Assistant (RAG)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python 3.12](https://img.shields.io/badge/Python-3.12+-3776AB.svg?style=flat&logo=python)](https://python.org)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=python)](https://www.sqlalchemy.org/)
[![Tests](https://img.shields.io/badge/Tests-22%20Passed%20(100%25)-brightgreen.svg)](https://pytest.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A robust, enterprise-grade Expense Reimbursement System backend built using **FastAPI**, **SQLAlchemy ORM (2.0)**, **SQLite**, **Pydantic (v2)**, and an **AI-powered RAG Assistant**.

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

## 🏛️ System Architecture Overview

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
        Policies["📚 Policy Documents (Markdown KB)"]
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

## 🔄 Expense Reimbursement & Duplicate Prevention Flow

```mermaid
stateDiagram-v2
    [*] --> DRAFT : Create Expense
    DRAFT --> DRAFT : Upload Receipt (SHA-256 Hashed)
    DRAFT --> SUBMITTED : Submit for Reimbursement
    
    state SUBMITTED {
        [*] --> DuplicateCheck
        DuplicateCheck --> FlaggedDuplicate : Matching Hash / Time-Window
        DuplicateCheck --> ValidSubmission : Unique Submission
    }

    SUBMITTED --> APPROVED : Manager Approves
    SUBMITTED --> REJECTED : Manager Rejects
    
    REJECTED --> DRAFT : Employee Re-edits
    APPROVED --> [*] : Processed for Payout
```

---

## 🤖 AI Policy Assistant (RAG Architecture)

```mermaid
sequenceDiagram
    autonumber
    actor Employee
    participant API as FastAPI Policy Assistant
    participant RAG as RAG Service Engine
    participant KB as Policy Knowledge Base
    
    Employee->>API: POST /api/v1/policy-assistant/query ("What is meal limit?")
    API->>RAG: Tokenize & Expand Query (Synonyms)
    RAG->>KB: Hybrid Retrieval (Keyword BM25 + Section Relevance)
    KB-->>RAG: Return Top Matching Policy Sections
    alt Relevant Context Found
        RAG-->>API: Synthesize Grounded Answer + Citations
        API-->>Employee: Return Answer with [Document & Section Citations]
    else Low Relevance / Missing Policy
        RAG-->>API: Missing Context Fallback
        API-->>Employee: "Sufficient information could not be found..."
    end
```

---

## ✨ Key Features

- **🔐 OAuth2 Authentication & Role-Based Access Control (RBAC)**: Secure JWT token authentication with role enforcement (`EMPLOYEE`, `MANAGER`, `ADMIN`).
- **🤖 RAG-Powered AI Policy Assistant**:
  - Processes and indexes corporate policy documents (`Expense Policy`, `Travel Policy`, `Finance Policy`, `Employee Handbook`).
  - **Hybrid Search**: Combines sparse keyword matching and dense token similarity.
  - **Document Citations**: Includes explicit policy document and section citations with every answer.
  - **Query Expansion**: Synonym expansion for natural language query variations.
  - **Metadata Filtering**: Option to scope query search to specific policy documents.
  - **Missing Information Fallback**: Explicitly states when information is unavailable rather than hallucinating.
  - **Streaming Responses**: Token streaming endpoint via Server-Sent Events (SSE).
- **🧾 Comprehensive Expense Management**: Create, update, delete, search, filter, and categorize expenses with receipt file attachments.
- **🛡️ Multi-Tier Duplicate Prevention Engine**: Cryptographic SHA-256 receipt hashing, exact attribute matching, and time-window heuristic overlap checks (±3 days).
- **📑 Manager Approval Workflow**: Real-time review queue, approve/reject actions with comments, and state transition enforcement.
- **📊 Department Analytics & Summaries**: Real-time aggregation of department budgets, approved/pending/rejected totals, and category breakdowns.
- **📜 Complete Immutable Audit Trail**: Detailed audit logging for all mutations with JSON diffs and actor tracking.

---

## 📋 Policy Documents Indexed

1. **`Expense Policy`**: Receipts rules, categories ($75 meal cap, $300 team dinner limit, $500 hardware limit).
2. **`Travel Policy`**: 14-day advance booking, economy class, 8-hour flight business class exception, hotel caps ($250 standard / $400 tier-1 cities).
3. **`Finance Policy`**: 30-day submission deadline, approval hierarchy ($1k manager / $5k director / >$5k VP & CFO), 5-day direct deposit SLA.
4. **`Employee Handbook`**: Working hours, remote stipend ($500 setup + $50 monthly internet), continuing education allowance ($1,500/yr), wellness benefit ($50/mo).

---

## 🔌 API Endpoints Summary

| Category | Method | Endpoint | Description |
|---|---|---|---|
| **AI Policy Assistant** | `POST` | `/api/v1/policy-assistant/query` | RAG query with grounded answer & citations |
| **AI Policy Assistant** | `POST` | `/api/v1/policy-assistant/stream` | Real-time streaming RAG answer response |
| **AI Policy Assistant** | `GET`  | `/api/v1/policy-assistant/documents` | List indexed policy documents and sections |
| **Auth** | `POST` | `/api/v1/auth/register` | Register new user |
| **Auth** | `POST` | `/api/v1/auth/login` | OAuth2 token login |
| **Auth** | `GET`  | `/api/v1/auth/me` | Current user profile |
| **Expenses** | `GET`  | `/api/v1/expenses/` | List, search & filter expenses (paginated) |
| **Expenses** | `POST` | `/api/v1/expenses/` | Create expense draft (with receipt file) |
| **Expenses** | `POST` | `/api/v1/expenses/{id}/receipt` | Upload receipt image or PDF |
| **Expenses** | `PUT`  | `/api/v1/expenses/{id}` | Update draft or rejected expense |
| **Expenses** | `DELETE` | `/api/v1/expenses/{id}` | Delete draft expense |
| **Requests** | `POST` | `/api/v1/requests/submit` | Submit expense for reimbursement review |
| **Requests** | `GET`  | `/api/v1/requests/my-requests` | Track employee request status |
| **Manager** | `GET`  | `/api/v1/manager/pending-requests` | View pending requests for department |
| **Manager** | `POST` | `/api/v1/manager/requests/{id}/review` | Approve/Reject request with comments |
| **Manager** | `GET`  | `/api/v1/manager/department-summary/{id}` | Department analytics & budget breakdown |
| **Audit** | `GET`  | `/api/v1/audit-logs/` | Query immutable audit log history |

---

## ⚡ Quickstart Guide

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

### 3. Run Automated Tests (22 Passed)

```bash
pytest -v
```

### 4. Launch Application Server

```bash
uvicorn app.main:app --reload --port 8000
```

- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`
