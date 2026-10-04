import argparse
import base64
from contextlib import contextmanager
import getpass
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = Path(os.environ.get(
    "AUTOARCH_DB_PATH",
    PROJECT_ROOT / "data" / "processed" / "access_control.sqlite3",
))
PASSWORD_ITERATIONS = 600_000
VALID_ROLES = {"admin", "architect", "viewer"}
ROLE_LEVEL = {"viewer": 1, "architect": 2, "admin": 3}
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.@-]{3,64}$")


class AuthorizationError(PermissionError):
    pass


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def _connect():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_db():
    with _connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'architect', 'viewer')),
                created_at TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
            );
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                owner_user_id INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS project_memberships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK (role IN ('admin', 'architect', 'viewer')),
                UNIQUE(project_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL UNIQUE,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                version INTEGER NOT NULL,
                upload_timestamp TEXT NOT NULL,
                page_count INTEGER NOT NULL,
                chunk_count INTEGER NOT NULL,
                traceability_count INTEGER NOT NULL DEFAULT 0,
                collection_name TEXT NOT NULL,
                uploader_user_id INTEGER REFERENCES users(id),
                artifact_dir TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_memberships_user ON project_memberships(user_id);
            CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);
            """
        )


def hash_password(password):
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError("Passwords must contain at least 12 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password, encoded_hash):
    try:
        algorithm, iterations, salt, expected = encoded_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            base64.urlsafe_b64decode(salt.encode("ascii")),
            int(iterations),
        )
        actual = base64.urlsafe_b64encode(digest).decode("ascii")
        return hmac.compare_digest(actual, expected)
    except (AttributeError, TypeError, ValueError, UnicodeError):
        return False


def _public_user(row):
    if row is None:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "created_at": row["created_at"],
        "active": bool(row["active"]),
    }


def authenticate_user(username, password):
    init_db()
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
            (str(username or "").strip(),),
        ).fetchone()
    if row is None:
        hash_password(password if isinstance(password, str) and len(password) >= 12 else "invalid-login-attempt")
        return None
    if not row["active"] or not verify_password(password, row["password_hash"]):
        return None
    return _public_user(row)


def require_login(user_id):
    if user_id is None:
        raise AuthorizationError("Please log in to continue.")
    init_db()
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE id = ? AND active = 1", (user_id,)
        ).fetchone()
    if row is None:
        raise AuthorizationError("Your account is inactive or no longer exists.")
    return _public_user(row)


def _insert_user(connection, username, password, role):
    username = str(username or "").strip()
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError("Usernames must be 3-64 characters using letters, numbers, '.', '_', '@' or '-'.")
    if role not in VALID_ROLES:
        raise ValueError("Unknown user role.")
    cursor = connection.execute(
        "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
        (username, hash_password(password), role, _now()),
    )
    return cursor.lastrowid


def bootstrap_admin(username, password, project_name="AUTOSAR Demo"):
    init_db()
    with _connect() as connection:
        if connection.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            raise ValueError("An account already exists; use an admin account to manage users.")
        user_id = _insert_user(connection, username, password, "admin")
        cursor = connection.execute(
            "INSERT INTO projects (name, owner_user_id, created_at) VALUES (?, ?, ?)",
            (str(project_name).strip(), user_id, _now()),
        )
        project_id = cursor.lastrowid
        connection.execute(
            "INSERT INTO project_memberships (project_id, user_id, role) VALUES (?, ?, 'admin')",
            (project_id, user_id),
        )
    return {"user_id": user_id, "project_id": project_id}


def create_user(actor_user_id, username, password, role="viewer"):
    require_role(actor_user_id, "admin")
    with _connect() as connection:
        user_id = _insert_user(connection, username, password, role)
        row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _public_user(row)


def list_users(actor_user_id):
    require_role(actor_user_id, "admin")
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM users ORDER BY username COLLATE NOCASE"
        ).fetchall()
    return [_public_user(row) for row in rows]


def update_user(actor_user_id, target_user_id, *, role=None, active=None):
    require_role(actor_user_id, "admin")
    actor = require_login(actor_user_id)
    if role is not None and role not in VALID_ROLES:
        raise ValueError("Unknown user role.")
    if active is not None and not isinstance(active, bool):
        raise ValueError("Account active state must be true or false.")
    if actor["id"] == int(target_user_id) and (
        role not in (None, "admin") or active is False
    ):
        raise ValueError("You cannot demote or deactivate your own active admin account.")

    with _connect() as connection:
        current = connection.execute(
            "SELECT * FROM users WHERE id = ?", (int(target_user_id),)
        ).fetchone()
        if current is None:
            raise ValueError("User not found.")
        next_role = role or current["role"]
        next_active = current["active"] if active is None else int(active)
        if current["active"] and current["role"] == "admin" and (
            next_role != "admin" or not next_active
        ):
            active_admins = connection.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND active = 1"
            ).fetchone()[0]
            if active_admins <= 1:
                raise ValueError("The last active admin cannot be demoted or deactivated.")
        connection.execute(
            "UPDATE users SET role = ?, active = ? WHERE id = ?",
            (next_role, next_active, int(target_user_id)),
        )
        updated = connection.execute(
            "SELECT * FROM users WHERE id = ?", (int(target_user_id),)
        ).fetchone()
    return _public_user(updated)


def create_project(user_id, name):
    user = require_role(user_id, "admin")
    name = str(name or "").strip()
    if not name or len(name) > 120:
        raise ValueError("Project names must contain 1-120 characters.")
    with _connect() as connection:
        cursor = connection.execute(
            "INSERT INTO projects (name, owner_user_id, created_at) VALUES (?, ?, ?)",
            (name, user["id"], _now()),
        )
        project_id = cursor.lastrowid
        connection.execute(
            "INSERT INTO project_memberships (project_id, user_id, role) VALUES (?, ?, 'admin')",
            (project_id, user["id"]),
        )
    return {"id": project_id, "name": name, "role": "admin"}


def add_project_member(actor_user_id, project_id, username, role):
    require_role(actor_user_id, "admin", project_id=project_id)
    if role not in VALID_ROLES:
        raise ValueError("Unknown project role.")
    with _connect() as connection:
        user = connection.execute(
            "SELECT id, active FROM users WHERE username = ? COLLATE NOCASE",
            (str(username or "").strip(),),
        ).fetchone()
        if user is None or not user["active"]:
            raise ValueError("No active user exists with that username.")
        connection.execute(
            """INSERT INTO project_memberships (project_id, user_id, role)
               VALUES (?, ?, ?)
               ON CONFLICT(project_id, user_id) DO UPDATE SET role = excluded.role""",
            (project_id, user["id"], role),
        )
    return require_project_access(user["id"], project_id)


def require_project_access(user_id, project_id):
    user = require_login(user_id)
    if isinstance(project_id, bool) or not str(project_id).isdigit():
        raise AuthorizationError("Project access denied.") from None
    project_id = int(project_id)
    with _connect() as connection:
        row = connection.execute(
            """SELECT p.id AS project_id, p.name, p.owner_user_id, pm.role AS membership_role
               FROM projects p
               JOIN project_memberships pm ON pm.project_id = p.id
               WHERE p.id = ? AND pm.user_id = ?""",
            (project_id, user["id"]),
        ).fetchone()
    if row is None:
        raise AuthorizationError("You are not a member of this project.")
    effective_role = min(
        (user["role"], row["membership_role"]), key=lambda role: ROLE_LEVEL[role]
    )
    return {
        "id": row["project_id"],
        "name": row["name"],
        "owner_user_id": row["owner_user_id"],
        "role": effective_role,
        "user_id": user["id"],
        "username": user["username"],
    }


def require_role(user_id, *allowed_roles, project_id=None):
    if len(allowed_roles) == 1 and not isinstance(allowed_roles[0], str):
        allowed_roles = tuple(allowed_roles[0])
    user = require_login(user_id)
    role = (
        require_project_access(user["id"], project_id)["role"]
        if project_id is not None
        else user["role"]
    )
    if role not in allowed_roles:
        raise AuthorizationError("Your role is not allowed to perform this operation.")
    return user


def can_upload(user_id, project_id):
    try:
        require_role(user_id, "admin", "architect", project_id=project_id)
        return True
    except AuthorizationError:
        return False


def can_query(user_id, project_id):
    try:
        require_project_access(user_id, project_id)
        return True
    except AuthorizationError:
        return False


def can_compare(user_id, project_id):
    return can_upload(user_id, project_id)


def can_export(user_id, project_id):
    return can_upload(user_id, project_id)


def can_review(user_id, project_id):
    return can_upload(user_id, project_id)


def list_user_projects(user_id):
    user = require_login(user_id)
    with _connect() as connection:
        rows = connection.execute(
            """SELECT p.id, p.name, pm.role AS membership_role
               FROM projects p
               JOIN project_memberships pm ON pm.project_id = p.id
               WHERE pm.user_id = ? ORDER BY p.name COLLATE NOCASE""",
            (user["id"],),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "role": min(
                (user["role"], row["membership_role"]),
                key=lambda role: ROLE_LEVEL[role],
            ),
        }
        for row in rows
    ]


def prompt_for_user_project():
    """Authenticate a local CLI caller and return a project they may access."""
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    user = authenticate_user(username, password)
    if user is None:
        raise AuthorizationError("Invalid username or password.")
    projects = list_user_projects(user["id"])
    if not projects:
        raise AuthorizationError("This account is not a member of any project.")
    for index, project in enumerate(projects, start=1):
        print(f"{index}. {project['name']} ({project['role']})")
    choice = input("Project number: ").strip()
    try:
        project = projects[int(choice) - 1]
    except (ValueError, IndexError):
        raise AuthorizationError("Invalid project selection.") from None
    require_project_access(user["id"], project["id"])
    return user, project


def project_collection_name(user_id, project_id):
    project = require_project_access(user_id, project_id)
    return f"autosar_project_{project['id']}"


def create_document_record(
    user_id,
    project_id,
    *,
    document_id,
    filename,
    version,
    page_count,
    chunk_count,
    traceability_count=0,
    collection_name=None,
    artifact_dir=None,
):
    if not can_upload(user_id, project_id):
        raise AuthorizationError("Your role cannot upload documents to this project.")
    project = require_project_access(user_id, project_id)
    authorized_collection = f"autosar_project_{project['id']}"
    if collection_name is not None and collection_name != authorized_collection:
        raise AuthorizationError("Document collection does not match the authorized project.")
    collection_name = authorized_collection
    timestamp = _now()
    with _connect() as connection:
        cursor = connection.execute(
            """INSERT INTO documents (
                document_id, project_id, filename, version, upload_timestamp,
                page_count, chunk_count, traceability_count, collection_name,
                uploader_user_id, artifact_dir
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                document_id,
                project["id"],
                filename,
                int(version),
                timestamp,
                int(page_count),
                int(chunk_count),
                int(traceability_count),
                collection_name,
                user_id,
                str(artifact_dir) if artifact_dir else None,
            ),
        )
        row = connection.execute(
            "SELECT * FROM documents WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return dict(row)


def list_project_documents(user_id, project_id):
    project = require_project_access(user_id, project_id)
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM documents WHERE project_id = ? ORDER BY id DESC",
            (project["id"],),
        ).fetchall()
    return [dict(row) for row in rows]


def get_project_document(user_id, project_id, document_id):
    project = require_project_access(user_id, project_id)
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM documents WHERE project_id = ? AND document_id = ?",
            (project["id"], document_id),
        ).fetchone()
    if row is None:
        raise AuthorizationError("Document access denied.")
    return dict(row)


def _setup_local_admin():
    username = input("Admin username: ").strip()
    password = getpass.getpass("Admin password (12+ characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords did not match.")
    result = bootstrap_admin(username, password)
    print(f"Created local admin {username!r} and project AUTOSAR Demo (id {result['project_id']}).")
    print("The password was stored only as a salted PBKDF2 hash.")
    try:
        from database.project_bootstrap import seed_canonical_demo_project

        seeded = seed_canonical_demo_project(result["user_id"], result["project_id"])
        if seeded:
            print(f"Copied {seeded['chunks']} existing AUTOSAR vectors into {seeded['collection_name']}.")
        else:
            print("No canonical AUTOSAR vectors were available to seed; upload a PDF from the app.")
    except Exception:
        print("The account is ready, but the canonical project could not be seeded; upload a PDF from the app.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoArch-AI local account setup")
    parser.add_argument("command", choices=["setup-admin"])
    parser.parse_args()
    _setup_local_admin()