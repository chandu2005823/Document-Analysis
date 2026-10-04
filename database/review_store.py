import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from database.access_control import can_review, require_project_access

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REVIEW_FILE = PROJECT_ROOT / "data" / "processed" / "review_log.json"


def _review_file(project_id=None):
    if project_id is None:
        return REVIEW_FILE
    return PROJECT_ROOT / "data" / "processed" / "projects" / str(project_id) / "review_log.json"


def save_review(
    question: str,
    answer: str,
    confidence: dict | None,
    review_status: str,
    *,
    user_id=None,
    project_id=None,
):
    if user_id is None or project_id is None or not can_review(user_id, project_id):
        raise PermissionError("Review requires an authorized project architect or admin.")
    project = require_project_access(user_id, project_id)
    review_file = _review_file(project["id"])
    review_file.parent.mkdir(parents=True, exist_ok=True)
    if review_file.exists():
        with open(review_file, "r", encoding="utf-8") as file:
            try:
                entries = json.load(file)
            except json.JSONDecodeError:
                entries = []
    else:
        entries = []

    entries.append(
        {
            "question": question,
            "answer": answer,
            "confidence": confidence or {},
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "review_status": review_status,
            "review_id": uuid.uuid4().hex,
            "user_id": user_id,
            "project_id": project["id"],
        }
    )

    with open(review_file, "w", encoding="utf-8") as file:
        json.dump(entries, file, indent=4, ensure_ascii=False)

    return entries[-1]


def update_review_status(review_id: str, review_status: str, *, user_id=None, project_id=None):
    if review_status not in {"approved", "needs_review"}:
        raise ValueError("Review status must be approved or needs_review.")
    if user_id is None or project_id is None or not can_review(user_id, project_id):
        raise PermissionError("Review requires an authorized project architect or admin.")
    project = require_project_access(user_id, project_id)
    review_file = _review_file(project["id"])
    if not review_file.exists():
        raise KeyError("Review not found.")
    with review_file.open("r", encoding="utf-8") as file:
        try:
            entries = json.load(file)
        except json.JSONDecodeError:
            entries = []
    review = next((entry for entry in entries if entry.get("review_id") == review_id), None)
    if review is None:
        raise KeyError("Review not found.")
    review["review_status"] = review_status
    review["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    review["updated_by"] = user_id
    with review_file.open("w", encoding="utf-8") as file:
        json.dump(entries, file, indent=4, ensure_ascii=False)
    return review


def list_reviews(limit: int = 20, *, user_id=None, project_id=None):
    if user_id is None or project_id is None:
        raise ValueError("Review reads require an authorized user and project.")
    project = require_project_access(user_id, project_id)
    review_file = _review_file(project["id"])
    if not review_file.exists():
        return []

    with open(review_file, "r", encoding="utf-8") as file:
        try:
            entries = json.load(file)
        except json.JSONDecodeError:
            entries = []

    return entries[-limit:]
