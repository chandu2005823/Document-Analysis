import re

import chromadb

from embeddings import EmbeddingModel
from database.access_control import (
    AuthorizationError,
    list_project_documents,
    project_collection_name,
)
from database.access_control import prompt_for_user_project


CHROMA_DIR = "data/chroma"

DEFAULT_COLLECTION = "autosar_documents"
LEXICAL_STOP_WORDS = {
    "what", "are", "the", "main", "used", "describe", "described", "about",
    "this", "that", "from", "with", "into", "does", "how", "which", "who",
    "is", "a", "an", "of", "and", "in", "for", "to",
}


def search_documents(
    query,
    top_k=5,
    max_distance=None,
    collection_name=DEFAULT_COLLECTION,
    *,
    user_id=None,
    project_id=None,
):

    if user_id is None or project_id is None:
        raise AuthorizationError("Retrieval requires both a user and an authorized project.")
    collection_name = project_collection_name(user_id, project_id)

    client = chromadb.PersistentClient(
        path=CHROMA_DIR
    )

    collection = client.get_collection(
        name=collection_name
    )

    project_documents = list_project_documents(user_id, project_id)
    latest_document_id = project_documents[0]["document_id"] if project_documents else None
    collection_sample = collection.get(limit=1, include=["metadatas"])
    metadata_has_document_ids = bool(
        collection_sample.get("metadatas")
        and collection_sample["metadatas"][0].get("document_id")
    )

    embedding_model = EmbeddingModel()

    query_embedding = embedding_model.encode(
        [query]
    )

    query_options = {
        "query_embeddings": query_embedding.tolist(),
        "n_results": 8,
        "include": ["documents", "metadatas", "distances"],
    }
    if latest_document_id and metadata_has_document_ids:
        query_options["where"] = {"document_id": latest_document_id}
    results = collection.query(**query_options)

    filtered_documents = []
    filtered_metadatas = []
    filtered_distances = []

    for document, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):

        if max_distance is None or distance <= max_distance:

            filtered_documents.append(document)
            filtered_metadatas.append(metadata)
            filtered_distances.append(distance)

    semantic_ids = {
        (metadata.get("document_id"), metadata.get("chunk_id"))
        for metadata in filtered_metadatas
    }
    query_terms = {
        term
        for term in re.findall(r"\b[^\W\d_]{3,}\b", query.lower(), flags=re.UNICODE)
        if term not in LEXICAL_STOP_WORDS
    }
    if query_terms:
        lexical_options = {"include": ["documents", "metadatas"]}
        if latest_document_id and metadata_has_document_ids:
            lexical_options["where"] = {"document_id": latest_document_id}
        lexical_records = collection.get(**lexical_options)
        lexical_matches = []
        for document, metadata in zip(
            lexical_records["documents"], lexical_records["metadatas"]
        ):
            key = (metadata.get("document_id"), metadata.get("chunk_id"))
            if key in semantic_ids:
                continue
            matched_terms = sum(term in document.lower() for term in query_terms)
            if matched_terms:
                lexical_matches.append((matched_terms / len(query_terms), document, metadata))
        lexical_matches.sort(key=lambda item: item[0], reverse=True)
        lexical_matches = lexical_matches[:top_k]
        for _score, document, metadata in lexical_matches:
            filtered_documents.append(document)
            filtered_metadatas.append(metadata)
            filtered_distances.append(1.0)

    candidate_limit = top_k + len(lexical_matches) if query_terms else top_k

    return {
        "documents": [
            filtered_documents[:candidate_limit]
        ],

        "metadatas": [
            filtered_metadatas[:candidate_limit]
        ],

        "distances": [
            filtered_distances[:candidate_limit]
        ],

        "query": query,

        "collection_name": collection_name
    }


def search_document_metadata(query, top_k=8, *, user_id=None, project_id=None):
    """Retrieve early-page context for document metadata questions."""
    if user_id is None or project_id is None:
        raise AuthorizationError("Retrieval requires both a user and an authorized project.")

    collection_name = project_collection_name(user_id, project_id)
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(name=collection_name)
    documents = list_project_documents(user_id, project_id)
    latest_document_id = documents[0]["document_id"] if documents else None
    where = {"page_number": {"$lte": 5}}
    if latest_document_id:
        where = {
            "$and": [
                {"document_id": latest_document_id},
                {"page_number": {"$lte": 5}},
            ]
        }
    results = collection.get(
        where=where,
        include=["documents", "metadatas"],
    )
    records = sorted(
        zip(results["documents"], results["metadatas"]),
        key=lambda item: (item[1].get("page_number", 0), item[1].get("chunk_id", 0)),
    )
    selected = records[: max(top_k * 4, 20)]
    return {
        "documents": [[item[0] for item in selected]],
        "metadatas": [[item[1] for item in selected]],
        "distances": [[0.0 for _ in selected]],
        "query": query,
        "collection_name": collection_name,
        "metadata_query": True,
    }


def display_results(results):

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    print("\n" + "=" * 70)
    print("SEMANTIC RETRIEVAL RESULTS")
    print("=" * 70)

    if not documents:

        print("\nNo sufficiently relevant results found.")

        return

    for i in range(len(documents)):

        print("\n" + "-" * 70)

        print(f"Rank       : {i + 1}")
        print(
            f"Page       : "
            f"{metadatas[i]['page_number']}"
        )

        print(
            f"Chunk ID    : "
            f"{metadatas[i]['chunk_id']}"
        )

        print(
            f"Distance   : "
            f"{distances[i]:.4f}"
        )

        print("\nRetrieved Context:")

        print(documents[i])


if __name__ == "__main__":

    user, project = prompt_for_user_project()
    query = input(
        "\nEnter your question: "
    )

    results = search_documents(
        query,
        top_k=5,
        max_distance=0.90,
        user_id=user["id"],
        project_id=project["id"],
    )

    display_results(results)