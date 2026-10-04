import json
from io import BytesIO
from pathlib import Path

import chromadb
import numpy as np
import pytest

from database import access_control, audit_log
from database import project_bootstrap
from rag import retriever, uploaded_document_db
from rag import rag_pipeline
from rag.rag_pipeline import load_relationships
from frontend import document_processor
from frontend.relationship_graph import build_relationship_graph


@pytest.fixture(scope="module")
def two_project_users(tmp_path_factory):
    temp_path = tmp_path_factory.mktemp("project-isolation")
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(access_control, "DATABASE_PATH", temp_path / "access.sqlite3")
        access_control.init_db()
        admin = access_control.bootstrap_admin(
            "isolation-admin", "isolation-admin-password-1"
        )
        user_a = access_control.create_user(
            admin["user_id"], "isolation-user-a", "isolation-user-a-password-1", "architect"
        )
        user_b = access_control.create_user(
            admin["user_id"], "isolation-user-b", "isolation-user-b-password-1", "architect"
        )
        project_a_id = admin["project_id"]
        project_b = access_control.create_project(admin["user_id"], "Project B")
        access_control.add_project_member(
            admin["user_id"], project_a_id, user_a["username"], "architect"
        )
        access_control.add_project_member(
            admin["user_id"], project_b["id"], user_b["username"], "architect"
        )
        yield {
            "path": temp_path,
            "admin_id": admin["user_id"],
            "user_a": user_a,
            "user_b": user_b,
            "project_a_id": project_a_id,
            "project_b_id": project_b["id"],
        }


class FakeEmbeddingModel:
    def encode(self, texts):
        return np.asarray([[1.0, 0.0] for _ in texts], dtype=np.float32)


def test_project_scoped_chroma_retrieval_and_cross_project_denial(two_project_users, monkeypatch):
    fixture = two_project_users
    chroma_path = fixture["path"] / "chroma"
    client = chromadb.PersistentClient(path=str(chroma_path))
    project_documents = (
        (fixture["project_a_id"], fixture["user_a"], "Document A", "project-a-document", "Project A secret architecture"),
        (fixture["project_b_id"], fixture["user_b"], "Document B", "project-b-document", "Project B secret architecture"),
    )
    for project_id, user, filename, document_id, text in project_documents:
        access_control.create_document_record(
            user["id"],
            project_id,
            document_id=document_id,
            filename=filename,
            version=1,
            page_count=1,
            chunk_count=1,
        )
        collection = client.get_or_create_collection(
            name=f"autosar_project_{project_id}"
        )
        collection.add(
            ids=[f"doc-{project_id}"],
            documents=[text],
            embeddings=[[1.0, 0.0]],
            metadatas=[{"project_id": project_id, "user_id": user["id"], "page_number": 1}],
        )

    monkeypatch.setattr(retriever, "CHROMA_DIR", str(chroma_path))
    monkeypatch.setattr(retriever, "EmbeddingModel", FakeEmbeddingModel)

    result_a = retriever.search_documents(
        "architecture", user_id=fixture["user_a"]["id"], project_id=fixture["project_a_id"]
    )
    result_b = retriever.search_documents(
        "architecture", user_id=fixture["user_b"]["id"], project_id=fixture["project_b_id"]
    )

    assert result_a["documents"][0] == ["Project A secret architecture"]
    assert result_b["documents"][0] == ["Project B secret architecture"]
    assert result_a["collection_name"] == f"autosar_project_{fixture['project_a_id']}"
    assert result_b["collection_name"] == f"autosar_project_{fixture['project_b_id']}"
    assert [
        document["filename"]
        for document in access_control.list_project_documents(
            fixture["user_a"]["id"], fixture["project_a_id"]
        )
    ] == ["Document A"]
    assert [
        document["filename"]
        for document in access_control.list_project_documents(
            fixture["user_b"]["id"], fixture["project_b_id"]
        )
    ] == ["Document B"]

    with pytest.raises(access_control.AuthorizationError):
        retriever.search_documents(
            "architecture", user_id=fixture["user_a"]["id"], project_id=fixture["project_b_id"]
        )
    with pytest.raises(access_control.AuthorizationError):
        retriever.search_documents("architecture", collection_name="uploaded_autosar_documents")
    with pytest.raises(access_control.AuthorizationError):
        retriever.search_documents("architecture")
    with pytest.raises(access_control.AuthorizationError):
        access_control.list_project_documents(
            fixture["user_a"]["id"], fixture["project_b_id"]
        )


def test_rag_pipeline_forwards_project_scope_and_denies_cross_project(
    two_project_users, monkeypatch
):
    fixture = two_project_users
    calls = []

    def scoped_search(query, **kwargs):
        calls.append(kwargs)
        return {
            "documents": [["Project A grounded content"]],
            "metadatas": [[{"page_number": 1, "chunk_id": 0}]],
            "distances": [[0.1]],
            "query": query,
            "collection_name": f"autosar_project_{kwargs['project_id']}",
        }

    monkeypatch.setattr(rag_pipeline, "search_documents", scoped_search)
    monkeypatch.setattr(
        rag_pipeline,
        "rerank_results",
        lambda results: [{
            "document": results["documents"][0][0],
            "metadata": results["metadatas"][0][0],
            "distance": results["distances"][0][0],
            "final_score": 0.9,
        }],
    )

    result = rag_pipeline.retrieve_context(
        "question",
        user_id=fixture["user_a"]["id"],
        project_id=fixture["project_a_id"],
    )

    assert result["documents"][0] == ["Project A grounded content"]
    assert calls[0]["user_id"] == fixture["user_a"]["id"]
    assert calls[0]["project_id"] == fixture["project_a_id"]
    with pytest.raises(access_control.AuthorizationError):
        rag_pipeline.retrieve_context(
            "question",
            user_id=fixture["user_a"]["id"],
            project_id=fixture["project_b_id"],
        )
    assert len(calls) == 1


def test_project_upload_indexer_writes_only_to_authorized_collection(two_project_users, monkeypatch, tmp_path):
    fixture = two_project_users
    monkeypatch.setattr(uploaded_document_db, "CHROMA_DIR", str(tmp_path / "index-chroma"))
    monkeypatch.setattr(uploaded_document_db, "EmbeddingModel", FakeEmbeddingModel)
    project_id = fixture["project_a_id"]
    user_id = fixture["user_a"]["id"]
    chunks_file = tmp_path / "chunks.json"
    chunks_file.write_text(json.dumps({
        "source_file": "document-a.pdf",
        "project_id": project_id,
        "document_id": "p1_document_a_v1",
        "version": 1,
        "chunks": [{
            "text": "Project A only",
            "page_number": 3,
            "chunk_id": 0,
            "chunk_type": "text",
            "extraction_method": "ocr",
        }],
    }), encoding="utf-8")

    collection_name = uploaded_document_db.build_uploaded_database(
        chunks_file, user_id=user_id, project_id=project_id
    )
    client = chromadb.PersistentClient(path=str(tmp_path / "index-chroma"))
    metadata = client.get_collection(collection_name).get(include=["metadatas"])["metadatas"][0]

    assert collection_name == f"autosar_project_{project_id}"
    assert metadata["project_id"] == project_id
    assert metadata["user_id"] == user_id
    assert metadata["extraction_method"] == "ocr"

    with pytest.raises(access_control.AuthorizationError):
        uploaded_document_db.build_uploaded_database(
            chunks_file, user_id=user_id, project_id=fixture["project_b_id"]
        )


def test_relationship_artifacts_are_loaded_only_for_authorized_project(two_project_users, tmp_path):
    fixture = two_project_users
    project_relationships = (
        (fixture["project_a_id"], fixture["user_a"], "relationship-a", "PPort"),
        (fixture["project_b_id"], fixture["user_b"], "relationship-b", "RPort"),
    )
    for project_id, user, document_id, source in project_relationships:
        artifact_dir = tmp_path / str(project_id) / document_id
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "relationships.json").write_text(
            json.dumps([{
                "source": source,
                "relationship": "provides",
                "target": "Service Instance",
                "page": 1,
                "project_id": project_id,
            }]),
            encoding="utf-8",
        )
        access_control.create_document_record(
            user["id"],
            project_id,
            document_id=document_id,
            filename=f"{document_id}.pdf",
            version=1,
            page_count=1,
            chunk_count=1,
            artifact_dir=artifact_dir,
        )

    result_a = load_relationships(
        user_id=fixture["user_a"]["id"], project_id=fixture["project_a_id"]
    )
    result_b = load_relationships(
        user_id=fixture["user_b"]["id"], project_id=fixture["project_b_id"]
    )
    graph_a = build_relationship_graph(result_a)
    graph_b = build_relationship_graph(result_b)

    assert [item["source"] for item in result_a] == ["PPort"]
    assert [item["source"] for item in result_b] == ["RPort"]
    assert {edge["from"] for edge in graph_a.edges} == {"PPort"}
    assert {edge["from"] for edge in graph_b.edges} == {"RPort"}
    with pytest.raises(access_control.AuthorizationError):
        load_relationships(
            user_id=fixture["user_a"]["id"], project_id=fixture["project_b_id"]
        )


def test_audit_entries_are_project_scoped_and_redact_secrets(two_project_users, monkeypatch, tmp_path):
    fixture = two_project_users
    monkeypatch.setattr(audit_log, "AUDIT_DB_PATH", tmp_path / "audit.sqlite3")
    audit_log.log_event(
        "DOCUMENT_QUERIED",
        question="token=token-value-should-not-persist; GROQ_API_KEY=fake-groq-key-should-not-persist",
        details={
            "password": "password-value-should-not-persist",
            "groq_api_key": "fake-groq-key-field-should-not-persist",
            "credential": "sk-1234567890abcdef",
            "note": "secret=inline-secret-value",
        },
        user_id=fixture["user_a"]["id"],
        username=fixture["user_a"]["username"],
        project_id=fixture["project_a_id"],
        document_id="document-a",
    )

    records = audit_log.read_logs(
        user_id=fixture["user_a"]["id"], project_id=fixture["project_a_id"]
    )
    raw_database = (tmp_path / "audit.sqlite3").read_text(encoding="latin-1")

    assert records[0]["user_id"] == fixture["user_a"]["id"]
    assert records[0]["username"] == fixture["user_a"]["username"]
    assert records[0]["project_id"] == fixture["project_a_id"]
    assert records[0]["document_id"] == "document-a"
    assert records[0]["details"]["password"] == "[REDACTED]"
    assert records[0]["details"]["groq_api_key"] == "[REDACTED]"
    assert "token-value-should-not-persist" not in raw_database
    assert "password-value-should-not-persist" not in raw_database
    assert "fake-groq-key-should-not-persist" not in raw_database
    assert "fake-groq-key-field-should-not-persist" not in raw_database
    assert "1234567890abcdef" not in raw_database
    with pytest.raises(access_control.AuthorizationError):
        audit_log.read_logs(
            user_id=fixture["user_a"]["id"], project_id=fixture["project_b_id"]
        )


def test_canonical_vectors_are_copied_to_demo_project_without_deleting_source(
    two_project_users, monkeypatch, tmp_path
):
    fixture = two_project_users
    chroma_path = tmp_path / "canonical-chroma"
    monkeypatch.setattr(project_bootstrap, "CHROMA_DIR", chroma_path)
    monkeypatch.setattr(project_bootstrap, "PROJECT_ROOT", tmp_path)
    from database import versioning

    monkeypatch.setattr(versioning, "VERSION_FILE", tmp_path / "versions.json")
    client = chromadb.PersistentClient(path=str(chroma_path))
    canonical = client.get_or_create_collection("autosar_documents")
    canonical.add(
        ids=["autosar_chunk_0"],
        documents=["Canonical AUTOSAR demo content"],
        embeddings=[[1.0, 0.0]],
        metadatas=[{"page_number": 1, "chunk_id": 0}],
    )

    from extraction import relationship_extractor, traceability
    from ingestion import pdf_parser

    monkeypatch.setattr(
        pdf_parser, "extract_text_from_pdf",
        lambda _path: [{"page_number": 1, "text": "PPort provides Service Instance", "extraction_method": "text"}],
    )
    monkeypatch.setattr(
        traceability, "extract_traceable_entities",
        lambda _pages: [{"entity": "PPort", "type": "ports", "page": 1}],
    )
    monkeypatch.setattr(
        relationship_extractor, "extract_relationships",
        lambda _pages: [{"source": "PPort", "relationship": "provides", "target": "Service Instance", "page": 1}],
    )

    seeded = project_bootstrap.seed_canonical_demo_project(
        fixture["admin_id"], fixture["project_a_id"]
    )
    project_collection = client.get_collection(
        f"autosar_project_{fixture['project_a_id']}"
    )

    assert seeded["chunks"] == 1
    assert canonical.count() == 1
    assert project_collection.count() == 1
    assert project_collection.get(include=["metadatas"])["metadatas"][0]["project_id"] == fixture["project_a_id"]
    versions = versioning.list_document_versions(
        "AUTOSAR_AP_EXP_SWArchitecture.pdf",
        user_id=fixture["admin_id"],
        project_id=fixture["project_a_id"],
    )
    assert versions[0]["document_id"] == seeded["document_id"]
    next_version = versioning.get_document_version(
        "AUTOSAR_AP_EXP_SWArchitecture.pdf",
        1,
        1,
        user_id=fixture["admin_id"],
        project_id=fixture["project_a_id"],
    )
    assert next_version["version"] == 2
    assert next_version["document_id"] != seeded["document_id"]


def test_document_processor_persists_active_user_and_project_scope(
    two_project_users, monkeypatch, tmp_path
):
    fixture = two_project_users
    monkeypatch.setattr(document_processor, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        "database.versioning.VERSION_FILE", tmp_path / "versions.json"
    )
    monkeypatch.setattr(
        document_processor, "extract_text_from_pdf",
        lambda _path: [{"page_number": 1, "text": "OCR text content", "extraction_method": "ocr"}],
    )
    monkeypatch.setattr(document_processor, "extract_tables_from_pdf", lambda _path: [])
    monkeypatch.setattr(
        document_processor,
        "extract_traceable_entities",
        lambda _pages: [{"entity": "PPort", "type": "ports", "page": 1}],
    )
    monkeypatch.setattr(
        document_processor,
        "extract_relationships",
        lambda _pages: [{"source": "PPort", "relationship": "provides", "target": "Service Instance", "page": 1}],
    )
    indexed = {}
    monkeypatch.setattr(
        document_processor,
        "build_uploaded_database",
        lambda path, **kwargs: indexed.update(path=path, **kwargs),
    )
    monkeypatch.setattr(document_processor.tempfile, "gettempdir", lambda: str(tmp_path))

    upload = BytesIO(b"controlled test upload")
    upload.name = "private-design.pdf"
    result = document_processor.process_uploaded_pdf(
        upload, user_id=fixture["user_a"]["id"], project_id=fixture["project_a_id"]
    )

    with open(Path(result["artifact_dir"]) / "chunks.json", encoding="utf-8") as file:
        payload = json.load(file)
    with open(Path(result["traceability_path"]), encoding="utf-8") as file:
        traceability = json.load(file)
    with open(Path(result["relationship_path"]), encoding="utf-8") as file:
        relationships = json.load(file)
    assert result["project_id"] == fixture["project_a_id"]
    assert payload["user_id"] == fixture["user_a"]["id"]
    assert payload["project_id"] == fixture["project_a_id"]
    assert payload["chunks"][0]["extraction_method"] == "ocr"
    assert indexed["project_id"] == fixture["project_a_id"]
    assert traceability[0]["project_id"] == fixture["project_a_id"]
    assert relationships[0]["document_id"] == result["document_id"]
    with pytest.raises(access_control.AuthorizationError):
        access_control.get_project_document(
            fixture["user_b"]["id"], fixture["project_a_id"], result["document_id"]
        )