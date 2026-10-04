import csv
import io
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
for module_path in (PROJECT_ROOT / "rag", PROJECT_ROOT / "ingestion", PROJECT_ROOT / "extraction"):
    if str(module_path) not in sys.path:
        sys.path.insert(0, str(module_path))

from database.access_control import (
    get_project_document,
    list_project_documents,
    require_project_access,
)
from frontend.relationship_graph import build_relationship_graph
from rag.rag_pipeline import load_relationships


def _read_json_list(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return payload if isinstance(payload, list) else []


def get_project_traceability(user_id, project_id, *, entity_type=None, search=None):
    project = require_project_access(user_id, project_id)
    documents = list_project_documents(user_id, project["id"])
    records = []
    for document in documents:
        artifact_dir = document.get("artifact_dir")
        if not artifact_dir:
            continue
        for record in _read_json_list(Path(artifact_dir) / "traceability.json"):
            if record.get("project_id") != project["id"]:
                continue
            if record.get("document_id") != document["document_id"]:
                continue
            if entity_type and str(record.get("type", "")).casefold() != entity_type.casefold():
                continue
            if search and search.casefold() not in str(record.get("entity", "")).casefold():
                continue
            records.append(record)
    return records


def get_project_relationships(user_id, project_id, *, source=None, relationship=None, target=None):
    project = require_project_access(user_id, project_id)
    documents = list_project_documents(user_id, project["id"])
    allowed_documents = {document["document_id"] for document in documents}
    records = load_relationships(user_id=user_id, project_id=project["id"])
    filters = (source, relationship, target)
    fields = ("source", "relationship", "target")
    return [
        record
        for record in records
        if record.get("project_id") == project["id"]
        and record.get("document_id") in allowed_documents
        and all(
            not value or str(value).casefold() in str(record.get(field, "")).casefold()
            for field, value in zip(fields, filters)
        )
    ]


def get_project_graph_data(user_id, project_id):
    relationships = get_project_relationships(user_id, project_id)
    graph = build_relationship_graph(relationships)
    return {
        "nodes": [
            {"id": node["id"], "label": node["label"]}
            for node in graph.nodes
        ],
        "edges": [
            {
                "id": edge["id"],
                "source": edge["from"],
                "target": edge["to"],
                "relationship": edge["label"],
                "page": edge.get("page"),
                "project_id": edge.get("project_id"),
                "document_id": edge.get("document_id"),
            }
            for edge in graph.edges
        ],
    }


def get_document_traceability(user_id, project_id, document_id):
    document = get_project_document(user_id, project_id, document_id)
    artifact_dir = document.get("artifact_dir")
    if not artifact_dir:
        return document, []
    records = _read_json_list(Path(artifact_dir) / "traceability.json")
    scoped = [
        record for record in records
        if record.get("project_id") == int(project_id)
        and record.get("document_id") == document_id
    ]
    return document, scoped


def get_traceability_csv(records):
    output = io.StringIO()
    columns = ("entity", "type", "page", "document_id", "project_id")
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue()