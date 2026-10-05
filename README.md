# AutoArch-AI

## AI-Powered AUTOSAR HLD Document Analysis & Architecture Traceability Assistant

AutoArch-AI is an AI-assisted platform for analyzing AUTOSAR High-Level Design (HLD) documents and turning large architecture documents into searchable, traceable, and reviewable engineering knowledge.

The system combines document ingestion, architecture/entity extraction, source-grounded RAG, traceability, architecture relationship exploration, document comparison, review workflows, audit logging, and role-based project isolation in one application.

---

## Key Features

### 1. Document Ingestion
- Upload AUTOSAR HLD PDF documents
- Extract page-level text using PyMuPDF
- OCR fallback for image-based pages
- Detect and extract tables using pdfplumber
- Split documents into searchable chunks
- Preserve page-level provenance

### 2. AI-Powered Q&A
- Ask natural-language questions about uploaded documents
- Retrieval-Augmented Generation (RAG)
- Semantic retrieval using embeddings
- Source-grounded answers
- Page/source citations
- Confidence and grounding checks
- Clear error handling when the language model is unavailable

### 3. Architecture Traceability
- Search architecture entities such as components, ports, interfaces, and other extracted entities
- View linked source pages
- Inspect source evidence from the original document
- Trace extracted entities back to their document evidence

### 4. Architecture Explorer
- Explore extracted architecture relationships
- Search/filter by entity and relationship
- View relationships such as:
  - `PPort → provides → Service Instance`
  - `RPort → consumes → Service Instance`
- Interactive architecture visualization
- Relationship inspector with source page information

### 5. Document Comparison
- Compare document versions
- Identify changes in extracted architecture information
- Support architecture lifecycle and change analysis

### 6. Review & Approval
- Review extracted/AI-generated information
- Support human verification before relying on results

### 7. Project Isolation & RBAC
The system supports three roles:

- **Admin** — manage users, projects, memberships, and workspace controls
- **Architect** — analyze documents and use architecture/review features
- **Viewer** — view available project information without modification privileges

Project-level authorization is applied to application data and retrieval operations.

### 8. Audit Logging
- Record important application actions
- Support traceability of user and project activity
- Protect sensitive credential information through redaction

---

## System Architecture

```text
                    ┌──────────────────────────┐
                    │       Streamlit UI       │
                    │  Dashboard / Documents   │
                    │ Q&A / Traceability       │
                    │ Architecture / Compare   │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │       FastAPI Backend     │
                    │ Auth / Projects / Docs   │
                    │ Query / Traceability      │
                    │ Relationships / Review   │
                    │ Comparison / Audit        │
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
      ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
      │ PDF / OCR    │   │ Architecture │   │   SQLite     │
      │  Ingestion   │   │  Extraction  │   │ Auth/Audit/  │
      │  Chunking    │   │ Traceability │   │ Projects     │
      │  Tables      │   │ Relationships│   │ Versions     │
      └──────┬───────┘   └──────┬───────┘   └──────────────┘
             │                  │
             └──────────┬───────┘
                        ▼
               ┌──────────────────┐
               │   RAG Pipeline   │
               │ Embeddings       │
               │ Retrieval        │
               │ Reranking        │
               │ Grounding        │
               │ Citations        │
               └────────┬─────────┘
                        ▼
               ┌──────────────────┐
               │ Chroma Vector DB │
               └────────┬─────────┘
                        │
                        ▼
               ┌──────────────────┐
               │   Groq LLM       │
               │   Optional Q&A   │
               └──────────────────┘
```

---

## Technology Stack

### Frontend
- Streamlit

### Backend
- FastAPI
- Python

### Document Processing
- PyMuPDF
- pdfplumber
- Tesseract OCR integration

### AI / RAG
- Sentence Transformers
- ChromaDB
- Retrieval-Augmented Generation
- Groq API / LLM
- Grounding and citation validation

### Data & Security
- SQLite
- PBKDF2 password hashing
- Role-Based Access Control (RBAC)
- Project-level isolation
- Audit logging

### Visualization
- PyVis

### Testing
- pytest

---

## Project Structure

```text
AutoArch-AI/
│
├── analysis/
│   └── document_comparison.py
│
├── backend/
│   ├── api.py
│   ├── dependencies.py
│   ├── schemas.py
│   ├── services.py
│   └── routes/
│       ├── audit.py
│       ├── auth.py
│       ├── comparison.py
│       ├── documents.py
│       ├── exports.py
│       ├── projects.py
│       ├── query.py
│       ├── relationships.py
│       ├── review.py
│       └── traceability.py
│
├── database/
│   ├── access_control.py
│   ├── audit_log.py
│   ├── project_bootstrap.py
│   ├── review_store.py
│   ├── traceability_store.py
│   └── versioning.py
│
├── extraction/
│   ├── architecture_extractor.py
│   ├── relationship_extractor.py
│   ├── traceability.py
│   └── traceability_store.py
│
├── frontend/
│   ├── app.py
│   ├── document_processor.py
│   ├── relationship_graph.py
│   ├── shell.py
│   └── assets/
│
├── ingestion/
│   ├── pdf_parser.py
│   ├── table_extractor.py
│   ├── chunker.py
│   ├── process_uploaded.py
│   └── save_chunks.py
│
├── rag/
│   ├── embeddings.py
│   ├── retriever.py
│   ├── reranker.py
│   ├── context_builder.py
│   ├── rag_pipeline.py
│   ├── citation.py
│   ├── confidence.py
│   ├── grounding_guard.py
│   ├── groq_client.py
│   └── vector_store.py
│
├── tests/
│
├── conftest.py
├── pytest.ini
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Requirements

- Python 3.11+ recommended
- Git
- Internet connection for installing Python packages
- Tesseract OCR executable for OCR fallback workflows
- Optional Groq API key for AI-generated Q&A responses

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/chandu2005823/-Document-Analysis-Assistant-.git AutoArch-AI
cd AutoArch-AI
```

### 2. Create a virtual environment

From the repository root, on Windows:

```powershell
python -m venv venv
.\venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file from the committed template:

```powershell
copy .env.example .env
```

Set `GROQ_API_KEY` in `.env` to enable AI-generated Q&A responses. The app
loads `.env` from the repository root; values in `.env.example` are
placeholders, not working credentials.

`AUTOARCH_API_SECRET` is optional for local development. Set it to a random
value of at least 32 characters to keep issued API tokens valid across backend
restarts. `TESSERACT_CMD` is optional and is only needed when scanned PDFs need
OCR and Tesseract is not available on `PATH`. Tesseract is an external program
and is not installed by `pip`.

### Local data and models

SQLite databases, processed artifacts, and Chroma vector indexes are generated
under `data/` and are intentionally not committed. Uploaded PDFs are staged
temporarily in the operating system's temp directory; processed document
artifacts are written under `data/processed/`. The
`sentence-transformers/all-MiniLM-L6-v2` embedding model is downloaded
automatically by Sentence Transformers the first time it is needed, so that
first run requires internet access. No sample AUTOSAR PDF or prebuilt index is
included; create a project and upload a PDF you are authorized to use.

---

## Initialize the Admin Account

Use the application's existing database bootstrap flow:

```bash
python -m database.access_control setup-admin
```

Follow the prompts to configure the administrator account.

Do not store administrator passwords inside the source code.

To reset the password for an existing active admin account, run this command
from the project root and follow the non-echoing prompts:

```powershell
.\venv\Scripts\python.exe -m database.access_control reset-admin-password
```

The command updates only the selected admin account and stores the password
as a salted PBKDF2 hash.

---

## Run the Application

Run the FastAPI backend from the repository root:

```powershell
uvicorn backend.api:app --reload
```

The API documentation is available at `http://127.0.0.1:8000/docs`.

In a second terminal, activate the same virtual environment and start the
Streamlit frontend:

```bash
streamlit run frontend/app.py
```

The Streamlit UI will open in your browser.

Both commands should be run from the repository root. The Streamlit interface
uses the application services directly; the FastAPI service is also available
for API clients.

---

## Typical Usage Workflow

```text
Login
  ↓
Create / Select Project
  ↓
Upload AUTOSAR HLD PDF
  ↓
Process Document
  ↓
Document Extraction
  ↓
Architecture Entity & Relationship Extraction
  ↓
Embedding / Vector Indexing
  ↓
Q&A / Traceability / Architecture
  ↓
Review / Compare / Export / Audit
```

---

## Example Architecture Analysis

For a supported AUTOSAR architecture document, the Architecture Explorer can surface relationships such as:

```text
PPort
  │
  └── provides ──► Service Instance

RPort
  │
  └── consumes ──► Service Instance
```

The Traceability workspace links extracted entities back to source pages and evidence from the original document.

---

## Testing

Run the full test suite with:

```bash
python -m pytest -q
```

The test suite covers areas including:

- authentication and access control
- project isolation
- document processing
- PDF parsing
- table extraction
- architecture extraction
- traceability
- relationships
- retrieval and RAG
- document comparison
- graph functionality

---

## Security Notes

The repository intentionally excludes local runtime data such as:

- virtual environments
- `.env` files
- SQLite databases
- local Chroma/vector-store data
- processed document data
- uploaded PDFs
- logs and temporary files

These files are intended to remain local to the development environment.

Never commit:

```text
GROQ_API_KEY
passwords
tokens
database credentials
```

---

## Project Objective

AutoArch-AI aims to reduce the effort required to understand and maintain large AUTOSAR HLD documents by making architecture information:

- searchable
- traceable
- source-grounded
- easier to compare
- easier to review
- isolated by project and role

The system is designed to assist engineers rather than replace human architectural review.

---

## Author

**Chandra Lekha**

Computer Science Engineering  
Dayananda Sagar University

GitHub:  
https://github.com/chandu2005823

---

## Repository

https://github.com/chandu2005823/AUTOSAR-Document-Analyzer

**Last Updated:** October 4, 2026 - All functionalities verified and working
