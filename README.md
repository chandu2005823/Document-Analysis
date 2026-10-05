# AutoArch-AI

AI-Powered AUTOSAR HLD Document Analysis & Architecture Traceability Assistant

AutoArch-AI is an AI-assisted platform for analyzing AUTOSAR High-Level Design (HLD) documents and turning large architecture documents into searchable, traceable, and reviewable engineering knowledge.

The system combines document ingestion, architecture/entity extraction, source-grounded RAG, traceability, architecture relationship exploration, document comparison, review workflows, audit logging, and role-based project isolation in one application.

Key Features

1. Document Ingestion

- Upload AUTOSAR HLD PDF documents

- Extract page-level text using PyMuPDF

- OCR fallback for image-based pages

- Detect and extract tables using pdfplumber

- Split documents into searchable chunks

- Preserve page-level provenance

2. AI-Powered Q&A

- Ask natural-language questions about uploaded documents

- Retrieval-Augmented Generation (RAG)

- Semantic retrieval using embeddings

- Source-grounded answers

- Page/source citations

- Confidence and grounding checks

- Clear error handling when the language model is unavailable

3. Architecture Traceability

- Search architecture entities such as components, ports, interfaces, and other extracted entities

- View linked source pages

- Inspect source evidence from the original document

- Trace extracted entities back to their document evidence

4. Architecture Explorer

- Explore extracted architecture relationships

- Search/filter by entity and relationship

- View relationships such as:

  - PPort → provides → Service Instance

  - RPort → consumes → Service Instance

- Interactive architecture visualization

- Relationship inspector with source page information

5. Document Comparison

- Compare document versions

- Identify changes in extracted architecture information

- Support architecture lifecycle and change analysis

6. Review & Approval

- Review extracted/AI-generated information

- Support human verification before relying on results

7. Project Isolation & RBAC

The system supports three roles:

- Admin — manage users, projects, memberships, and workspace controls

- Architect — analyze documents and use architecture/review features

- Viewer — view available project information without modification privileges

Project-level authorization is applied to application data and retrieval operations.

8. Audit Logging

- Record important application actions

- Support traceability of user and project activity

- Protect sensitive credential information through redaction

System Architecture


                    ┌──────────────────────────┐

                    │       Streamlit UI       │

                    │  Dashboard / Documents   │

                    │ Q&A / Traceability       │

                    │ Architecture / Compare   │

                    └────────────┬─────────────┘

                                 │

                                 ▼

                    ┌──────────────────────────┐

                    │       FastAPI Backend     │

                    │ Auth / Projects / Docs   │

                    │ Query / Traceability      │

                    │ Relationships / Review   │

                    │ Comparison / Audit        │

                    └────────────┬─────────────┘

                                 │

              ┌──────────────────┼──────────────────┐

              ▼                  ▼                  ▼

      ┌──────────────┐   ┌──────────────┐   ┌──────────────┐

      │ PDF / OCR    │   │ Architecture │   │   SQLite     │

      │  Ingestion   │   │  Extraction  │   │ Auth/Audit/  │

      │  Chunking    │   │ Traceability │   │ Projects     │

      │  Tables      │   │ Relationships│   │ Versions     │

      └──────┬───────┘   └──────┬───────┘   └──────────────┘

             │                  │

             └──────────┬───────┘

                        ▼

               ┌──────────────────┐

               │   RAG Pipeline   │

               │ Embeddings       │

               │ Retrieval        │

               │ Reranking        │

               │ Grounding        │

               │ Citations        │

               └────────┬─────────┘

                        ▼

               ┌──────────────────┐

               │ Chroma Vector DB │

               └────────┬─────────┘

                        │

                        ▼

               ┌──────────────────┐

               │   Groq LLM       │

               │   Optional Q&A   │

               └──────────────────┘


Technology Stack

Frontend

- Streamlit

Backend

- FastAPI

- Python

Document Processing

- PyMuPDF

- pdfplumber

- Tesseract OCR integration

AI / RAG

- Sentence Transformers

- ChromaDB

- Retrieval-Augmented Generation

- Groq API / LLM

- Grounding and citation validation

Data & Security

- SQLite

- PBKDF2 password hashing

- Role-Based Access Control (RBAC)

- Project-level isolation

- Audit logging

Visualization

- PyVis

Testing

- pytest

Project Structure


Document-Analysis/

│

├── analysis/

│   └── document_comparison.py

│

├── backend/

│   ├── api.py

│   ├── dependencies.py

│   ├── schemas.py

│   ├── services.py

│   └── routes/

│       ├── audit.py

│       ├── auth.py

│       ├── comparison.py

│       ├── documents.py

│       ├── exports.py

│       ├── projects.py

│       ├── query.py

│       ├── relationships.py

│       ├── review.py

│       └── traceability.py

│

├── database/

│   ├── access_control.py

│   ├── audit_log.py

│   ├── project_bootstrap.py

│   ├── review_store.py

│   ├── traceability_store.py

│   └── versioning.py

│

├── extraction/

│   ├── architecture_extractor.py

│   ├── relationship_extractor.py

│   ├── traceability.py

│   └── traceability_store.py

│

├── frontend/

│   ├── app.py

│   ├── document_processor.py

│   ├── relationship_graph.py

│   ├── shell.py

│   └── assets/

│

├── ingestion/

│   ├── pdf_parser.py

│   ├── table_extractor.py

│   ├── chunker.py

│   ├── process_uploaded.py

│   └── save_chunks.py

│

├── rag/

│   ├── embeddings.py

│   ├── retriever.py

│   ├── reranker.py

│   ├── context_builder.py

│   ├── rag_pipeline.py

│   ├── citation.py

│   ├── confidence.py

│   ├── grounding_guard.py

│   ├── groq_client.py

│   └── vector_store.py

│

├── tests/

│

├── conftest.py

├── pytest.ini

├── requirements.txt

├── .gitignore

└── README.md


Requirements

- Python 3.13 recommended

- Git

- Internet connection for installing Python packages

- Tesseract OCR executable for OCR fallback workflows

- Optional Groq API key for AI-generated Q&A responses

**## ⚡ Quick Start (Windows)

If you want the shortest path from download to running the application:

git clone https://github.com/chandu2005823/Document-Analysis.git
cd Document-Analysis

py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt

copy .env.example .env

Open .env and set:

GROQ_API_KEY=your_groq_api_key_here


Then start the backend:

uvicorn backend.api:app --reload

Open a second terminal, activate the environment again, and start Streamlit:

cd Document-Analysis
.\venv\Scripts\Activate.ps1
streamlit run frontend/app.py

Open the Streamlit URL shown in the terminal, usually:

http://localhost:8501


For the first test, download the Recommended Test Document listed below and upload it to the application.

Installation

1. Clone the repository

git clone https://github.com/chandu2005823/Document-Analysis.git
cd Document-Analysis

2. Create and activate a virtual environment

Windows PowerShell:

py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1

Linux / macOS:

python3 -m venv venv
source venv/bin/activate

3. Install dependencies

pip install -r requirements.txt

4. Configure environment variables

Create your local .env file:

copy .env.example .env

Open .env and add your Groq API key:

GROQ_API_KEY=your_groq_api_key_here

The Groq key is required for AI-generated Q&A responses. The values in .env.example are placeholders and must not be committed as real credentials.

Optional settings:

AUTOARCH_API_SECRET — keeps issued API tokens valid across backend restarts.

TESSERACT_CMD — use only when Tesseract is installed but is not available on PATH.

Note: Tesseract is an external application and is not installed by pip.

5. Local data and models

The application creates SQLite databases, processed documents, and Chroma vector indexes under data/. These files are intentionally excluded from Git.

The sentence-transformers/all-MiniLM-L6-v2 embedding model is downloaded automatically the first time it is needed, so the first run requires internet access.

Initialize the Admin Account

Use the application's existing database bootstrap flow:


python -m database.access_control setup-admin


Follow the prompts to configure the administrator account.

Do not store administrator passwords inside the source code.

To reset the password for an existing active admin account, run this command

from the project root and follow the non-echoing prompts:


.\venv\Scripts\python.exe -m database.access_control reset-admin-password


The command updates only the selected admin account and stores the password

as a salted PBKDF2 hash.

Run the Application

Run the FastAPI backend from the repository root:


uvicorn backend.api\:app --reload


The API documentation is available at http://127.0.0.1:8000/docs.

In a second terminal, activate the same virtual environment and start the

Streamlit frontend:


streamlit run frontend/app.py


The Streamlit UI will open in your browser.

Both commands should be run from the repository root. The Streamlit interface

uses the application services directly; the FastAPI service is also available

for API clients.

**## 📌 Supported Document Scope

This project is a domain-specific AUTOSAR HLD / architecture analysis assistant.

Use an AUTOSAR HLD or AUTOSAR architecture document when testing:

Architecture entity extraction

Component / interface / port / service relationships

Architecture Explorer

Traceability

RAG-based Q&A

Document comparison

A general architecture-history or design document is not guaranteed to produce AUTOSAR relationships.

Typical Usage Workflow**


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


Example Architecture Analysis

For a supported AUTOSAR architecture document, the Architecture Explorer can surface relationships such as:


PPort

  │

  └── provides ──► Service Instance

RPort

  │

  └── consumes ──► Service Instance


The Traceability workspace links extracted entities back to source pages and evidence from the original document.

Testing

Run the full test suite with:


python -m pytest -q


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

Security Notes

The repository intentionally excludes local runtime data such as:

- virtual environments

- .env files

- SQLite databases

- local Chroma/vector-store data

- processed document data

- uploaded PDFs

- logs and temporary files

These files are intended to remain local to the development environment.

Never commit:


GROQ_API_KEY

passwords

tokens

database credentials


Project Objective

AutoArch-AI aims to reduce the effort required to understand and maintain large AUTOSAR HLD documents by making architecture information:

- searchable

- traceable

- source-grounded

- easier to compare

- easier to review

- isolated by project and role

The system is designed to assist engineers rather than replace human architectural review.

Author

Chandra Lekha

Computer Science Engineering  

Dayananda Sagar University

GitHub:  

https://github.com/chandu2005823

Repository

https://github.com/chandu2005823/Document-Analysis

Last Updated: October 4, 2026 - All functionalities verified and working
