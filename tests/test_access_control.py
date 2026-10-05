import sqlite3
from pathlib import Path

import pytest

from database import access_control


@pytest.fixture
def access_db(tmp_path, monkeypatch):
    monkeypatch.setattr(access_control, "DATABASE_PATH", tmp_path / "access.sqlite3")
    access_control.init_db()
    admin = access_control.bootstrap_admin(
        "project-admin", "admin-password-for-tests-1"
    )
    architect = access_control.create_user(
        admin["user_id"], "project-architect", "architect-password-test-1", "architect"
    )
    viewer = access_control.create_user(
        admin["user_id"], "project-viewer", "viewer-password-for-tests-1", "viewer"
    )
    outsider = access_control.create_user(
        admin["user_id"], "project-outsider", "outsider-password-for-test-1", "viewer"
    )
    project = access_control.create_project(admin["user_id"], "Isolation Test")
    access_control.add_project_member(
        admin["user_id"], project["id"], architect["username"], "architect"
    )
    access_control.add_project_member(
        admin["user_id"], project["id"], viewer["username"], "viewer"
    )
    return {
        "admin": admin,
        "architect": architect,
        "viewer": viewer,
        "outsider": outsider,
        "project": project,
    }


def test_passwords_are_salted_hashed_and_verified():
    first = access_control.hash_password("strong-password-for-test-1")
    second = access_control.hash_password("strong-password-for-test-1")

    assert first.startswith("pbkdf2_sha256$")
    assert first != second
    assert "strong-password-for-test-1" not in first
    assert access_control.verify_password("strong-password-for-test-1", first)
    assert not access_control.verify_password("incorrect-password", first)


def test_authentication_succeeds_and_fails_without_returning_hash(access_db):
    user = access_control.authenticate_user(
        "PROJECT-ADMIN", "admin-password-for-tests-1"
    )
    assert user["id"] == access_db["admin"]["user_id"]
    assert "password_hash" not in user
    assert access_control.authenticate_user("project-admin", "wrong-password-123") is None
    assert access_control.authenticate_user("unknown-user", "wrong-password-123") is None


def test_admin_password_reset_requires_an_active_admin_and_changes_credentials(
    access_db,
):
    reset_user = access_control.reset_admin_password(
        "PROJECT-ADMIN", "new-admin-password-for-test-1"
    )

    assert reset_user["username"] == "project-admin"
    assert "password_hash" not in reset_user
    assert access_control.authenticate_user(
        "project-admin", "new-admin-password-for-test-1"
    )["id"] == access_db["admin"]["user_id"]
    assert access_control.authenticate_user(
        "project-admin", "admin-password-for-tests-1"
    ) is None
    with pytest.raises(ValueError, match="active admin account"):
        access_control.reset_admin_password(
            "project-viewer", "another-new-password-123"
        )
    with pytest.raises(ValueError, match="12 characters"):
        access_control.reset_admin_password("project-admin", "short")


def test_roles_and_project_membership_are_enforced(access_db):
    project_id = access_db["project"]["id"]
    architect_id = access_db["architect"]["id"]
    viewer_id = access_db["viewer"]["id"]

    assert access_control.can_upload(architect_id, project_id)
    assert access_control.can_query(viewer_id, project_id)
    assert not access_control.can_upload(viewer_id, project_id)
    assert access_control.can_export(architect_id, project_id)
    assert not access_control.can_review(viewer_id, project_id)
    assert access_control.require_project_access(viewer_id, project_id)["role"] == "viewer"


def test_membership_is_required_even_for_admin_users(access_db):
    other_project = access_control.create_project(
        access_db["admin"]["user_id"], "Other Project"
    )
    with pytest.raises(access_control.AuthorizationError):
        access_control.require_project_access(
            access_db["architect"]["id"], other_project["id"]
        )
    with pytest.raises(access_control.AuthorizationError):
        access_control.require_project_access(
            access_db["admin"]["user_id"], f"{other_project['id']}.5"
        )


def test_admin_user_management_never_returns_hash_and_prevents_last_admin_lockout(access_db):
    admin_id = access_db["admin"]["user_id"]
    users = access_control.list_users(admin_id)

    assert len(users) == 4
    assert all("password_hash" not in user for user in users)
    with pytest.raises(ValueError):
        access_control.update_user(admin_id, admin_id, active=False)

    updated = access_control.update_user(
        admin_id, access_db["outsider"]["id"], role="architect", active=False
    )
    assert updated["role"] == "architect"
    assert not updated["active"]


def test_documents_are_stored_and_listed_within_their_project(access_db):
    admin_id = access_db["admin"]["user_id"]
    project_id = access_db["project"]["id"]
    document = access_control.create_document_record(
        admin_id,
        project_id,
        document_id="doc-a-v1",
        filename="architecture.pdf",
        version=1,
        page_count=12,
        chunk_count=8,
    )

    assert document["project_id"] == project_id
    assert [item["document_id"] for item in access_control.list_project_documents(admin_id, project_id)] == ["doc-a-v1"]
    with pytest.raises(access_control.AuthorizationError):
        access_control.get_project_document(
            access_db["outsider"]["id"], project_id, "doc-a-v1"
        )
    with pytest.raises(access_control.AuthorizationError):
        access_control.create_document_record(
            admin_id,
            project_id,
            document_id="doc-bad-collection",
            filename="outside.pdf",
            version=1,
            page_count=1,
            chunk_count=1,
            collection_name="uploaded_autosar_documents",
        )


def test_document_artifact_paths_survive_workspace_moves(
    access_db, monkeypatch, tmp_path
):
    project_root = tmp_path / "workspace"
    monkeypatch.setattr(access_control, "PROJECT_ROOT", project_root)
    project_id = access_db["project"]["id"]
    admin_id = access_db["admin"]["user_id"]
    document_id = "p1_architecture_v1"
    current_artifact_dir = (
        project_root
        / "data"
        / "processed"
        / "projects"
        / str(project_id)
        / document_id
    )
    current_artifact_dir.mkdir(parents=True)
    (current_artifact_dir / "chunks.json").write_text("{}", encoding="utf-8")

    document = access_control.create_document_record(
        admin_id,
        project_id,
        document_id=document_id,
        filename="architecture.pdf",
        version=1,
        page_count=1,
        chunk_count=1,
        artifact_dir=tmp_path / "old-workspace" / "data" / "processed" / "old-doc",
    )

    assert document["artifact_dir"] == str(current_artifact_dir)
    assert access_control.get_project_document(
        admin_id, project_id, document_id
    )["artifact_dir"] == str(current_artifact_dir)
    assert access_control.list_project_documents(
        admin_id, project_id
    )[0]["artifact_dir"] == str(current_artifact_dir)

    new_document_id = "p1_new_document_v1"
    new_artifact_dir = (
        project_root
        / "data"
        / "processed"
        / "projects"
        / str(project_id)
        / new_document_id
    )
    new_artifact_dir.mkdir(parents=True)
    access_control.create_document_record(
        admin_id,
        project_id,
        document_id=new_document_id,
        filename="new-document.pdf",
        version=1,
        page_count=1,
        chunk_count=1,
        artifact_dir=new_artifact_dir,
    )
    with sqlite3.connect(access_control.DATABASE_PATH) as connection:
        stored_path = connection.execute(
            "SELECT artifact_dir FROM documents WHERE document_id = ?",
            (new_document_id,),
        ).fetchone()[0]

    assert not Path(stored_path).is_absolute()


def test_review_writes_require_project_role_and_context(access_db, monkeypatch, tmp_path):
    from database import review_store

    monkeypatch.setattr(review_store, "REVIEW_FILE", tmp_path / "global-review.json")
    monkeypatch.setattr(review_store, "PROJECT_ROOT", tmp_path)
    project_id = access_db["project"]["id"]
    architect_id = access_db["architect"]["id"]
    viewer_id = access_db["viewer"]["id"]

    with pytest.raises(PermissionError):
        review_store.save_review("Q", "A", {}, "approved")
    with pytest.raises(PermissionError):
        review_store.save_review(
            "Q", "A", {}, "approved", user_id=viewer_id, project_id=project_id
        )
    review = review_store.save_review(
        "Q", "A", {}, "approved", user_id=architect_id, project_id=project_id
    )

    assert review["user_id"] == architect_id
    assert review["project_id"] == project_id
    assert review_store.list_reviews(user_id=viewer_id, project_id=project_id) == [review]


def test_collection_names_are_derived_from_authorized_numeric_project_ids(access_db):
    project_id = access_db["project"]["id"]
    assert access_control.project_collection_name(
        access_db["architect"]["id"], project_id
    ) == f"autosar_project_{project_id}"
    with pytest.raises(access_control.AuthorizationError):
        access_control.project_collection_name(access_db["viewer"]["id"], "autosar_project_1")