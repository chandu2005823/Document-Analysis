import hashlib
import json
import sys
from pathlib import Path

import chromadb

from database.access_control import (
    create_document_record,
    project_collection_name,
    require_role,
)


CODE_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = CODE_ROOT
CHROMA_DIR = PROJECT_ROOT / "data" / "chroma"
CANONICAL_COLLECTION = "autosar_documents"
DEMO_FILENAME = "AUTOSAR_AP_EXP_SWArchitecture.pdf"


def seed_canonical_demo_project(user_id, project_id):
    """Copy existing canonical vectors and source artifacts into a new demo project."""
    require_role(user_id, "admin", project_id=project_id)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        source = client.get_collection(CANONICAL_COLLECTION)
    except Exception:
        return None
    if source.count() == 0:
        return None

    collection_name = project_collection_name(user_id, project_id)
    target = client.get_or_create_collection(name=collection_name)
    if target.count() > 0:
        return None

    records = source.get(include=["documents", "metadatas", "embeddings"])
    source_file = PROJECT_ROOT / "data" / "documents" / DEMO_FILENAME

    for module_path in (CODE_ROOT, CODE_ROOT / "extraction"):
        if str(module_path) not in sys.path:
            sys.path.insert(0, str(module_path))

    from ingestion.pdf_parser import extract_text_from_pdf
    from extraction.traceability import extract_traceable_entities
    from extraction.relationship_extractor import extract_relationships
    from database.versioning import get_document_version

    pages = extract_text_from_pdf(source_file) if source_file.exists() else []
    version_info = get_document_version(
        DEMO_FILENAME,
        len(pages),
        source.count(),
        user_id=user_id,
        project_id=project_id,
    )
    document_id = version_info["document_id"]
    artifact_dir = PROJECT_ROOT / "data" / "processed" / "projects" / str(project_id) / document_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    traceability = extract_traceable_entities(pages)
    relationships = extract_relationships(pages)
    scoped_pages = [
        {
            **page,
            "user_id": int(user_id),
            "project_id": int(project_id),
            "document_id": document_id,
        }
        for page in pages
    ]
    page_methods = {
        page["page_number"]: page.get("extraction_method", "text")
        for page in pages
    }
    scoped_traceability = [
        {
            **record,
            "user_id": int(user_id),
            "project_id": int(project_id),
            "document_id": document_id,
        }
        for record in traceability
    ]
    scoped_relationships = [
        {
            **record,
            "user_id": int(user_id),
            "project_id": int(project_id),
            "document_id": document_id,
        }
        for record in relationships
    ]

    sorted_records = sorted(
        zip(records["ids"], records["documents"], records["metadatas"], records["embeddings"]),
        key=lambda item: item[2].get("chunk_id", 0),
    )
    digest = hashlib.sha256(document_id.encode("utf-8")).hexdigest()[:24]
    chunks = []
    vector_ids = []
    vector_texts = []
    vector_embeddings = []
    vector_metadatas = []
    for index, (_source_id, text, metadata, embedding) in enumerate(sorted_records):
        chunk_id = int(metadata.get("chunk_id", index))
        page_number = int(metadata.get("page_number", 1))
        extraction_method = metadata.get(
            "extraction_method", page_methods.get(page_number, "text")
        )
        chunk_type = metadata.get("chunk_type", "text")
        chunks.append({
            "text": text,
            "page_number": page_number,
            "chunk_id": chunk_id,
            "chunk_type": chunk_type,
            "source_file": DEMO_FILENAME,
            "extraction_method": extraction_method,
            "user_id": int(user_id),
            "project_id": int(project_id),
            "document_id": document_id,
        })
        vector_ids.append(f"doc_{digest}_{chunk_id}")
        vector_texts.append(text)
        vector_embeddings.append(embedding.tolist())
        vector_metadatas.append({
            **{key: value for key, value in metadata.items() if value is not None},
            "project_id": int(project_id),
            "user_id": int(user_id),
            "document_id": document_id,
            "document": DEMO_FILENAME,
            "version": version_info["version"],
            "chunk_type": chunk_type,
            "extraction_method": extraction_method,
        })

    payload = {
        "source_file": DEMO_FILENAME,
        "filename": DEMO_FILENAME,
        "user_id": int(user_id),
        "project_id": int(project_id),
        "document_id": document_id,
        "version": version_info["version"],
        "collection_name": collection_name,
        "total_pages": len(pages),
        "total_chunks": len(chunks),
        "chunks": chunks,
        "tables": [],
    }
    for filename, data in (
        ("chunks.json", payload),
        ("pages.json", scoped_pages),
        ("traceability.json", scoped_traceability),
        ("relationships.json", scoped_relationships),
    ):
        with (artifact_dir / filename).open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)

    target.upsert(
        ids=vector_ids,
        documents=vector_texts,
        embeddings=vector_embeddings,
        metadatas=vector_metadatas,
    )
    create_document_record(
        user_id,
        project_id,
        document_id=document_id,
        filename=DEMO_FILENAME,
        version=version_info["version"],
        page_count=len(pages),
        chunk_count=len(chunks),
        traceability_count=len(scoped_traceability),
        collection_name=collection_name,
        artifact_dir=artifact_dir,
    )
    return {"document_id": document_id, "collection_name": collection_name, "chunks": len(chunks)}
