import json
from pathlib import Path

import chromadb

from embeddings import EmbeddingModel
from database.access_control import AuthorizationError, project_collection_name
from database.access_control import prompt_for_user_project


CHROMA_DIR = "data/chroma"
DEFAULT_COLLECTION = "uploaded_autosar_documents"


def build_uploaded_database(json_path, *, user_id=None, project_id=None, collection_name=None):
    if user_id is None or project_id is None:
        raise AuthorizationError("Project-scoped indexing requires an authorized user and project.")
    authorized_collection = project_collection_name(user_id, project_id)
    if collection_name is not None and collection_name != authorized_collection:
        raise AuthorizationError("The requested vector collection is outside the authorized project.")

    json_path = Path(json_path)

    if not json_path.exists():
        raise FileNotFoundError(f"Processed JSON not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if int(data.get("project_id", -1)) != int(project_id):
        raise AuthorizationError("The processed document belongs to a different project.")

    chunks = data["chunks"]
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    collection = client.get_or_create_collection(name=authorized_collection)
    if not chunks:
        return authorized_collection
    embedding_model = EmbeddingModel()
    texts = [chunk["text"] for chunk in chunks]
    embeddings = embedding_model.encode(texts)
    document_id = str(data["document_id"])
    import hashlib

    document_key = hashlib.sha256(document_id.encode("utf-8")).hexdigest()[:24]
    ids = [f"doc_{document_key}_{chunk['chunk_id']}" for chunk in chunks]
    metadatas = []
    for chunk in chunks:
        metadata = {
            "page_number": chunk["page_number"],
            "chunk_id": chunk["chunk_id"],
            "document": data["source_file"],
            "document_id": document_id,
            "version": data.get("version"),
            "project_id": int(project_id),
            "user_id": int(user_id),
            "chunk_type": chunk.get("chunk_type", "text"),
            "extraction_method": chunk.get("extraction_method", "text"),
            "document_title": data.get("document_title"),
            "author": data.get("author"),
            "page_count": data.get("page_count", data.get("total_pages")),
        }
        metadatas.append({key: value for key, value in metadata.items() if value is not None})

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
    )

    return authorized_collection


if __name__ == "__main__":
    user, project = prompt_for_user_project()
    build_uploaded_database(
        "data/processed/uploaded_chunks.json",
        user_id=user["id"],
        project_id=project["id"],
    )
    