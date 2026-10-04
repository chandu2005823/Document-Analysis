import json
import shutil

import pytest
from fastapi.testclient import TestClient

from backend.api import app
from backend.dependencies import create_access_token
from database import access_control, audit_log, review_store, versioning


@pytest.fixture(scope="module")
def api_workspace(tmp_path_factory):
    temp_root = tmp_path_factory.mktemp("autoarch-api")
    original_paths = {
        "access": access_control.DATABASE_PATH,
        "audit": audit_log.AUDIT_DB_PATH,
        "review": review_store.PROJECT_ROOT,
        "version": versioning.VERSION_FILE,
    }
    access_control.DATABASE_PATH = temp_root / "access.sqlite3"
    audit_log.AUDIT_DB_PATH = temp_root / "audit.sqlite3"
    review_store.PROJECT_ROOT = temp_root
    versioning.VERSION_FILE = temp_root / "versions.json"
    access_control.init_db()

    admin = access_control.bootstrap_admin("api-admin", "api-admin-password-test-123")
    project_a_id = admin["project_id"]
    project_b = access_control.create_project(admin["user_id"], "Project B")
    user_a = access_control.create_user(
        admin["user_id"], "api-user-a", "api-user-a-password-test-123", "architect"
    )
    user_b = access_control.create_user(
        admin["user_id"], "api-user-b", "api-user-b-password-test-123", "architect"
    )
    viewer = access_control.create_user(
        admin["user_id"], "api-viewer", "api-viewer-password-test-123", "viewer"
    )
    access_control.add_project_member(
        admin["user_id"], project_a_id, user_a["username"], "architect"
    )
    access_control.add_project_member(
        admin["user_id"], project_a_id, viewer["username"], "viewer"
    )
    access_control.add_project_member(
        admin["user_id"], project_b["id"], user_b["username"], "architect"
    )

    documents = {}
    for project_id, user, document_id, filename, entities, relationships in (
        (
            project_a_id,
            user_a,
            "doc-a-v1",
            "project-a.pdf",
            [{"entity": "PPort", "type": "ports", "page": 2}],
            [{"source": "PPort", "relationship": "provides", "target": "Service Instance", "page": 260}],
        ),
        (
            project_a_id,
            user_a,
            "doc-a-v2",
            "project-a-v2.pdf",
            [
                {"entity": "PPort", "type": "ports", "page": 4},
                {"entity": "RPort", "type": "ports", "page": 7},
            ],
            [{"source": "RPort", "relationship": "consumes", "target": "Service Instance", "page": 261}],
        ),
        (
            project_b["id"],
            user_b,
            "doc-b-v1",
            "project-b.pdf",
            [{"entity": "DifferentEntity", "type": "components", "page": 9}],
            [{"source": "BPort", "relationship": "connects", "target": "BService", "page": 9}],
        ),
    ):
        artifact_dir = temp_root / "projects" / str(project_id) / document_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        scoped_entities = [
            {
                **record,
                "user_id": user["id"],
                "project_id": project_id,
                "document_id": document_id,
            }
            for record in entities
        ]
        scoped_relationships = [
            {
                **record,
                "user_id": user["id"],
                "project_id": project_id,
                "document_id": document_id,
            }
            for record in relationships
        ]
        (artifact_dir / "traceability.json").write_text(
            json.dumps(scoped_entities), encoding="utf-8"
        )
        (artifact_dir / "relationships.json").write_text(
            json.dumps(scoped_relationships), encoding="utf-8"
        )
        access_control.create_document_record(
            user["id"],
            project_id,
            document_id=document_id,
            filename=filename,
            version=1,
            page_count=10,
            chunk_count=4,
            traceability_count=len(entities),
            collection_name=f"autosar_project_{project_id}",
            artifact_dir=artifact_dir,
        )
        documents[document_id] = {
            "project_id": project_id,
            "filename": filename,
            "entities": scoped_entities,
            "relationships": scoped_relationships,
        }

    audit_log.log_event(
        "DOCUMENT_UPLOADED",
        document_name="project-a.pdf",
        user_id=user_a["id"],
        username=user_a["username"],
        project_id=project_a_id,
        document_id="doc-a-v1",
    )

    try:
        yield {
            "root": temp_root,
            "admin": admin,
            "user_a": user_a,
            "user_b": user_b,
            "viewer": viewer,
            "project_a_id": project_a_id,
            "project_b_id": project_b["id"],
            "documents": documents,
            "client": TestClient(app),
        }
    finally:
        access_control.DATABASE_PATH = original_paths["access"]
        audit_log.AUDIT_DB_PATH = original_paths["audit"]
        review_store.PROJECT_ROOT = original_paths["review"]
        versioning.VERSION_FILE = original_paths["version"]


def auth_headers(user):
    user_id = user.get("id", user.get("user_id"))
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def test_health_endpoint_is_public(api_workspace):
    response = api_workspace["client"].get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "AutoArch-AI"}


def test_authentication_failure_and_valid_token(api_workspace):
    client = api_workspace["client"]
    failed = client.post(
        "/auth/token", json={"username": "api-user-a", "password": "wrong-password"}
    )
    succeeded = client.post(
        "/auth/token",
        json={"username": "api-user-a", "password": "api-user-a-password-test-123"},
    )

    assert failed.status_code == 401
    assert failed.json()["error"]["code"] == "invalid_credentials"
    assert succeeded.status_code == 200
    assert succeeded.json()["token_type"] == "bearer"
    assert "password" not in succeeded.text
    assert "password_hash" not in succeeded.text
    me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {succeeded.json()['access_token']}"},
    )
    malformed_token = client.get(
        "/auth/me", headers={"Authorization": "Bearer not-a-valid-token"}
    )
    assert me.status_code == 200
    assert me.json()["username"] == "api-user-a"
    assert "password_hash" not in me.json()
    assert malformed_token.status_code == 401


def test_projects_list_create_and_detail_authorization(api_workspace):
    client = api_workspace["client"]
    user_a_headers = auth_headers(api_workspace["user_a"])
    listed = client.get("/projects", headers=user_a_headers)
    created = client.post(
        "/projects",
        headers=auth_headers(api_workspace["admin"]),
        json={"name": "API Created"},
    )
    denied_create = client.post(
        "/projects", headers=user_a_headers, json={"name": "Not Allowed"}
    )
    allowed_detail = client.get(
        f"/projects/{api_workspace['project_a_id']}", headers=user_a_headers
    )
    denied_detail = client.get(
        f"/projects/{api_workspace['project_b_id']}", headers=user_a_headers
    )

    assert [item["id"] for item in listed.json()] == [api_workspace["project_a_id"]]
    assert created.status_code == 201
    assert denied_create.status_code == 403
    assert allowed_detail.status_code == 200
    assert denied_detail.status_code == 403


def test_project_isolation_user_a_and_user_b(api_workspace):
    client = api_workspace["client"]
    user_a = auth_headers(api_workspace["user_a"])
    user_b = auth_headers(api_workspace["user_b"])
    project_a_id = api_workspace["project_a_id"]
    project_b_id = api_workspace["project_b_id"]

    assert client.get(f"/projects/{project_a_id}", headers=user_a).status_code == 200
    assert client.get(f"/projects/{project_b_id}", headers=user_b).status_code == 200
    assert client.get(f"/projects/{project_b_id}", headers=user_a).status_code == 403
    assert client.get(f"/projects/{project_a_id}", headers=user_b).status_code == 403


def test_document_listing_is_project_scoped(api_workspace):
    client = api_workspace["client"]
    response_a = client.get(
        f"/projects/{api_workspace['project_a_id']}/documents",
        headers=auth_headers(api_workspace["user_a"]),
    )
    response_b = client.get(
        f"/projects/{api_workspace['project_b_id']}/documents",
        headers=auth_headers(api_workspace["user_b"]),
    )
    denied = client.get(
        f"/projects/{api_workspace['project_b_id']}/documents",
        headers=auth_headers(api_workspace["user_a"]),
    )

    assert {item["document_id"] for item in response_a.json()} == {"doc-a-v1", "doc-a-v2"}
    assert {item["document_id"] for item in response_b.json()} == {"doc-b-v1"}
    assert denied.status_code == 403


def test_document_upload_route_uses_existing_processor_and_returns_summary(
    api_workspace, monkeypatch
):
    from backend.routes import documents as document_routes

    calls = []
    monkeypatch.setattr(
        document_routes,
        "process_uploaded_pdf",
        lambda upload, **kwargs: calls.append((upload.name, kwargs)) or {
            "filename": upload.name,
            "document_id": "uploaded-doc-v1",
            "version": 1,
            "pages": 269,
            "chunks": 711,
            "traceability_records": 3,
            "relationship_records": 2,
            "version_info": {"upload_timestamp": "2026-09-30T00:00:00Z"},
        },
    )
    project_id = api_workspace["project_a_id"]
    response = api_workspace["client"].post(
        f"/projects/{project_id}/documents",
        headers=auth_headers(api_workspace["user_a"]),
        files={"file": ("new.pdf", b"%PDF-test", "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["pages"] == 269
    assert response.json()["chunks"] == 711
    assert response.json()["relationship_count"] == 2
    assert response.json()["project_id"] == project_id
    assert calls[0][1] == {
        "user_id": api_workspace["user_a"]["id"],
        "project_id": project_id,
    }


def test_query_requires_auth_and_project_membership(api_workspace):
    client = api_workspace["client"]
    unauthorized = client.post(
        f"/projects/{api_workspace['project_a_id']}/query",
        json={"question": "What is a PPort?"},
    )
    cross_project = client.post(
        f"/projects/{api_workspace['project_b_id']}/query",
        headers=auth_headers(api_workspace["user_a"]),
        json={"question": "What is a BPort?"},
    )

    assert unauthorized.status_code == 401
    assert cross_project.status_code == 403


def test_query_success_reuses_rag_and_returns_grounding_provenance(api_workspace, monkeypatch):
    from backend.routes import query as query_route

    monkeypatch.setattr(query_route, "retrieve_context", lambda *_args, **_kwargs: {
        "documents": [["PPort provides a Service Instance."]],
        "metadatas": [[{
            "page_number": 260,
            "chunk_id": 5,
            "document_id": "doc-a-v1",
        }]],
        "distances": [[0.1]],
        "confidence": {"score": 0.91, "level": "High"},
        "relationships": [],
    })
    monkeypatch.setattr(
        query_route, "generate_answer", lambda _prompt: "PPort provides a Service Instance."
    )
    response = api_workspace["client"].post(
        f"/projects/{api_workspace['project_a_id']}/query",
        headers=auth_headers(api_workspace["user_a"]),
        json={"question": "What does PPort provide?"},
    )

    assert response.status_code == 200
    assert response.json()["document_id"] == "doc-a-v1"
    assert response.json()["primary_source"]["page"] == 260
    assert response.json()["retrieval_confidence"]["level"] == "High"
    assert response.json()["grounding"]["supported"] is True


def test_query_without_groq_returns_structured_configuration_error_and_audit(
    api_workspace, monkeypatch
):
    from backend.routes import query as query_route

    monkeypatch.setattr(query_route, "retrieve_context", lambda *_args, **_kwargs: {
        "documents": [["Architecture context from project A."]],
        "metadatas": [[{"page_number": 1, "chunk_id": 0, "document_id": "doc-a-v1"}]],
        "distances": [[0.1]],
        "confidence": {"score": 0.7, "level": "High"},
        "relationships": [],
    })

    def missing_groq_key(_prompt):
        raise RuntimeError("GROQ_API_KEY environment variable is not set.")

    monkeypatch.setattr(query_route, "generate_answer", missing_groq_key)
    response = api_workspace["client"].post(
        f"/projects/{api_workspace['project_a_id']}/query",
        headers=auth_headers(api_workspace["user_a"]),
        json={"question": "What are the main views?"},
    )
    audit = audit_log.read_logs(
        user_id=api_workspace["user_a"]["id"],
        project_id=api_workspace["project_a_id"],
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "groq_api_key_missing"
    assert "GROQ_API_KEY is not configured" in response.json()["error"]["message"]
    assert any(
        event["event_type"] == "DOCUMENT_QUERY" and event["status"] == "error"
        for event in audit
    )


def test_traceability_authorization_and_filters(api_workspace):
    client = api_workspace["client"]
    response = client.get(
        f"/projects/{api_workspace['project_a_id']}/traceability?entity_type=ports&search=RPort",
        headers=auth_headers(api_workspace["user_a"]),
    )
    denied = client.get(
        f"/projects/{api_workspace['project_b_id']}/traceability",
        headers=auth_headers(api_workspace["user_a"]),
    )

    assert response.status_code == 200
    assert [item["entity"] for item in response.json()] == ["RPort"]
    assert response.json()[0]["page"] == 7
    assert denied.status_code == 403


def test_relationship_and_graph_endpoints_are_project_scoped(api_workspace):
    client = api_workspace["client"]
    headers_a = auth_headers(api_workspace["user_a"])
    headers_b = auth_headers(api_workspace["user_b"])
    relationships = client.get(
        f"/projects/{api_workspace['project_a_id']}/relationships?source=RPort",
        headers=headers_a,
    )
    graph_a = client.get(
        f"/projects/{api_workspace['project_a_id']}/relationships/graph",
        headers=headers_a,
    )
    graph_b = client.get(
        f"/projects/{api_workspace['project_b_id']}/relationships/graph",
        headers=headers_b,
    )
    denied = client.get(
        f"/projects/{api_workspace['project_b_id']}/relationships",
        headers=headers_a,
    )

    assert [item["source"] for item in relationships.json()] == ["RPort"]
    assert {node["id"] for node in graph_a.json()["nodes"]} == {"PPort", "RPort", "Service Instance"}
    assert len(graph_a.json()["edges"]) == 2
    assert graph_a.json()["edges"][0]["page"] in {260, 261}
    assert {node["id"] for node in graph_b.json()["nodes"]} == {"BPort", "BService"}
    assert len(graph_b.json()["edges"]) == 1
    assert denied.status_code == 403


def test_comparison_authorization_and_page_changes(api_workspace):
    client = api_workspace["client"]
    payload = {"baseline_document_id": "doc-a-v1", "current_document_id": "doc-a-v2"}
    allowed = client.post(
        f"/projects/{api_workspace['project_a_id']}/compare",
        headers=auth_headers(api_workspace["user_a"]),
        json=payload,
    )
    denied = client.post(
        f"/projects/{api_workspace['project_b_id']}/compare",
        headers=auth_headers(api_workspace["user_a"]),
        json={"baseline_document_id": "doc-a-v1", "current_document_id": "doc-a-v2"},
    )

    assert allowed.status_code == 200
    assert [item["entity"] for item in allowed.json()["added"]] == ["RPort"]
    assert allowed.json()["unchanged"][0]["page_change"] == "2 → 4"
    assert denied.status_code == 403


def test_review_role_checks_and_project_storage(api_workspace):
    client = api_workspace["client"]
    payload = {
        "question": "What is the PPort relationship?",
        "answer": "PPort provides Service Instance.",
        "confidence": {"level": "High", "score": 0.9},
        "review_status": "approved",
    }
    created = client.post(
        f"/projects/{api_workspace['project_a_id']}/reviews",
        headers=auth_headers(api_workspace["user_a"]),
        json=payload,
    )
    denied = client.post(
        f"/projects/{api_workspace['project_a_id']}/reviews",
        headers=auth_headers(api_workspace["viewer"]),
        json=payload,
    )
    review_id = created.json()["review_id"]
    updated = client.patch(
        f"/projects/{api_workspace['project_a_id']}/reviews/{review_id}",
        headers=auth_headers(api_workspace["user_a"]),
        json={"review_status": "needs_review"},
    )
    denied_update = client.patch(
        f"/projects/{api_workspace['project_a_id']}/reviews/{review_id}",
        headers=auth_headers(api_workspace["viewer"]),
        json={"review_status": "approved"},
    )
    listed = client.get(
        f"/projects/{api_workspace['project_a_id']}/reviews",
        headers=auth_headers(api_workspace["viewer"]),
    )

    assert created.status_code == 201
    assert denied.status_code == 403
    assert updated.status_code == 200
    assert updated.json()["review_status"] == "needs_review"
    assert denied_update.status_code == 403
    assert len(listed.json()) == 1
    assert listed.json()[0]["project_id"] == api_workspace["project_a_id"]
    assert listed.json()[0]["review_status"] == "needs_review"


def test_audit_authorization_and_exports(api_workspace):
    client = api_workspace["client"]
    headers_a = auth_headers(api_workspace["user_a"])
    audit_response = client.get(
        f"/projects/{api_workspace['project_a_id']}/audit", headers=headers_a
    )
    audit_denied = client.get(
        f"/projects/{api_workspace['project_b_id']}/audit", headers=headers_a
    )
    json_export = client.get(
        f"/projects/{api_workspace['project_a_id']}/exports/traceability?format=json",
        headers=headers_a,
    )
    csv_export = client.get(
        f"/projects/{api_workspace['project_a_id']}/exports/relationships?format=csv",
        headers=headers_a,
    )
    comparison_json = client.get(
        f"/projects/{api_workspace['project_a_id']}/exports/comparison?format=json&baseline_document_id=doc-a-v1&current_document_id=doc-a-v2",
        headers=headers_a,
    )
    comparison_csv = client.get(
        f"/projects/{api_workspace['project_a_id']}/exports/comparison?format=csv&baseline_document_id=doc-a-v1&current_document_id=doc-a-v2",
        headers=headers_a,
    )

    assert audit_response.status_code == 200
    assert audit_response.json()[0]["user_id"] == api_workspace["user_a"]["id"]
    assert audit_response.json()[0]["project_id"] == api_workspace["project_a_id"]
    assert audit_denied.status_code == 403
    assert json_export.status_code == 200
    assert json_export.headers["content-type"].startswith("application/json")
    assert csv_export.status_code == 200
    assert csv_export.headers["content-type"].startswith("text/csv")
    assert "relationship" in csv_export.text
    assert comparison_json.status_code == 200
    assert any(item["change_type"] == "added" for item in comparison_json.json())
    assert comparison_csv.status_code == 200
    assert "change_type" in comparison_csv.text
