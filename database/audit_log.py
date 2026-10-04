import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDIT_DB_PATH = PROJECT_ROOT / "data" / "processed" / "audit_log.sqlite3"


def _ensure_db() -> sqlite3.Connection:
    AUDIT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(AUDIT_DB_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            document_name TEXT,
            question TEXT,
            status TEXT NOT NULL,
            details TEXT
        )
        """
    )
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(audit_log)").fetchall()
    }
    for column, definition in {
        "user_id": "INTEGER",
        "username": "TEXT",
        "project_id": "INTEGER",
        "document_id": "TEXT",
    }.items():
        if column not in columns:
            connection.execute(f"ALTER TABLE audit_log ADD COLUMN {column} {definition}")
    connection.commit()
    return connection


_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b((?:groq[_-])?(?:password|token|secret|api[\s_-]?key))\s*[:=]\s*([^\s,;]+)"
)
_GROQ_TOKEN = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")


def _sanitize(value):
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if re.search(r"(?i)password|token|secret|api[\s_-]?key", str(key))
            else _sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        value = _SECRET_ASSIGNMENT.sub(r"\1=[REDACTED]", value)
        return _GROQ_TOKEN.sub("[REDACTED]", value)
    return value


def log_event(
    event_type: str,
    document_name: Optional[str] = None,
    question: Optional[str] = None,
    status: str = "success",
    details: Optional[dict[str, Any]] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    project_id: Optional[int] = None,
    document_id: Optional[str] = None,
) -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {
        "timestamp": timestamp,
        "event_type": event_type,
        "document_name": document_name,
        "question": question,
        "status": status,
        "user_id": user_id,
        "username": _sanitize(username),
        "project_id": project_id,
        "document_id": _sanitize(document_id),
        "details": json.dumps(_sanitize(details or {}), ensure_ascii=False),
        "question": _sanitize(question),
        "document_name": _sanitize(document_name),
    }

    connection = _ensure_db()
    connection.execute(
        """
        INSERT INTO audit_log (
            timestamp, event_type, document_name, question, status, details,
            user_id, username, project_id, document_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry["timestamp"],
            entry["event_type"],
            entry["document_name"],
            entry["question"],
            entry["status"],
            entry["details"],
            entry["user_id"],
            entry["username"],
            entry["project_id"],
            entry["document_id"],
        ),
    )
    connection.commit()
    connection.close()
    return entry


def read_logs(
    limit: int = 50,
    *,
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    if user_id is None or project_id is None:
        raise ValueError("Audit log reads require an authorized user and project.")
    from database.access_control import require_project_access

    project = require_project_access(user_id, project_id)
    connection = _ensure_db()
    rows = connection.execute(
        """
        SELECT timestamp, event_type, document_name, question, status, details,
               user_id, username, project_id, document_id
        FROM audit_log
        WHERE project_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (project["id"], limit),
    ).fetchall()
    connection.close()

    logs = []
    for (
        timestamp, event_type, document_name, question, status, details,
        user_id, username, project_id, document_id,
    ) in rows:
        payload = json.loads(details) if details else {}
        logs.append(
            {
                "timestamp": timestamp,
                "event_type": event_type,
                "document_name": document_name,
                "question": question,
                "status": status,
                "details": payload,
                "user_id": user_id,
                "username": username,
                "project_id": project_id,
                "document_id": document_id,
            }
        )
    return logs
