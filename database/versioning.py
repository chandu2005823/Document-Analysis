import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "data" / "processed" / "document_versions.json"


def _safe_document_id(filename: str) -> str:
    cleaned = Path(filename).stem
    return "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in cleaned).strip("_") or "document"


def _project_key(project_id, filename):
    return f"project:{project_id}:{filename}"


def get_document_version(
    filename: str,
    page_count: int,
    chunk_count: int,
    *,
    user_id=None,
    project_id=None,
) -> dict:
    if user_id is None or project_id is None:
        raise ValueError("Document versions require an authorized user and project.")
    from database.access_control import can_upload, require_project_access

    if not can_upload(user_id, project_id):
        raise PermissionError("Uploads are not permitted for this project.")
    project = require_project_access(user_id, project_id)
    VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)

    if VERSION_FILE.exists():
        with open(VERSION_FILE, "r", encoding="utf-8") as file:
            history = json.load(file)
    else:
        history = {}

    key = _project_key(project["id"], filename)
    existing = history.get(key, [])
    version_number = len(existing) + 1
    document_id = f"p{project['id']}_{_safe_document_id(filename)}_v{version_number}"

    entry = {
        "document_name": filename,
        "project_id": project["id"],
        "uploader_user_id": user_id,
        "document_id": document_id,
        "version": version_number,
        "upload_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "page_count": int(page_count),
        "chunk_count": int(chunk_count),
        "collection_name": f"autosar_project_{project['id']}",
    }

    history.setdefault(key, []).append(entry)

    with open(VERSION_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=4, ensure_ascii=False)

    return entry


def list_document_versions(
    filename: str | None = None,
    *,
    user_id=None,
    project_id=None,
) -> list[dict]:
    if user_id is None or project_id is None:
        raise ValueError("Document version reads require an authorized user and project.")
    from database.access_control import require_project_access

    project = require_project_access(user_id, project_id)
    if not VERSION_FILE.exists():
        return []

    with open(VERSION_FILE, "r", encoding="utf-8") as file:
        history = json.load(file)

    if filename:
        return history.get(_project_key(project["id"], filename), [])

    versions = []
    prefix = f"project:{project['id']}:"
    for key, documents in history.items():
        if key.startswith(prefix):
            versions.extend(documents)
    return versions
