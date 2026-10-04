from retriever import search_document_metadata, search_documents
from reranker import rerank_results
from confidence import calculate_confidence
import json
from pathlib import Path
from database.access_control import list_project_documents, require_project_access
from database.access_control import prompt_for_user_project


METADATA_QUERY_TERMS = {
    "title": "title",
    "book": "title",
    "document name": "title",
    "called": "title",
    "author": "author",
    "writer": "author",
    "publication": "publication",
    "published": "publication",
    "isbn": "publication",
}


def metadata_query_type(query):
    normalized = query.lower()
    for term, query_type in METADATA_QUERY_TERMS.items():
        if term in normalized:
            return query_type
    return None

def load_relationships(*, user_id=None, project_id=None):
    if user_id is None or project_id is None:
        return []
    project = require_project_access(user_id, project_id)
    relationships = []
    for document in list_project_documents(user_id, project["id"]):
        artifact_dir = document.get("artifact_dir")
        if not artifact_dir:
            continue
        relationship_path = Path(artifact_dir) / "relationships.json"
        if relationship_path.exists():
            with relationship_path.open("r", encoding="utf-8") as file:
                relationships.extend(json.load(file))
    return relationships
    
def retrieve_context(
    query,
    top_k=5,
    collection_name="autosar_documents",
    *,
    user_id=None,
    project_id=None,
):

    if user_id is None or project_id is None:
        from database.access_control import AuthorizationError

        raise AuthorizationError("Retrieval requires both a user and an authorized project.")
    require_project_access(user_id, project_id)

    # Metadata questions need early-page context because title and author
    # pages are not always nearest to natural-language metadata questions.
    query_type = metadata_query_type(query)
    if query_type:
        results = search_document_metadata(
            query,
            top_k=8,
            user_id=user_id,
            project_id=project_id,
        )
        results["metadata_query_type"] = query_type
    else:
        results = search_documents(
            query,
            top_k=8,
            max_distance=None,
            collection_name=collection_name,
            user_id=user_id,
            project_id=project_id,
        )

    # Step 2: Rerank
    ranked_results = rerank_results(results)

    # Step 3: Calculate confidence
    confidence = calculate_confidence(
        ranked_results
    )
    relationships = load_relationships(user_id=user_id, project_id=project_id)

    # Step 4: Select best results
    selected = ranked_results[:top_k]

    documents = [
        result["document"]
        for result in selected
    ]

    metadatas = [
        result["metadata"]
        for result in selected
    ]

    distances = [
        result["distance"]
        for result in selected
    ]

    return {
    "documents": [documents],
    "metadatas": [metadatas],
    "distances": [distances],
    "ranked_results": selected,
    "confidence": confidence,
    "collection_name": collection_name,
        "relationships": relationships,
        "metadata_query_type": query_type,
}


if __name__ == "__main__":

    user, project = prompt_for_user_project()
    query = input(
        "\nEnter your question: "
    )

    results = retrieve_context(
        query,
        top_k=5,
        user_id=user["id"],
        project_id=project["id"],
    )

    print("\n" + "=" * 70)
    print("RERANKED RAG CONTEXT")
    print("=" * 70)

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for i in range(len(documents)):

        print("\n" + "-" * 70)

        print(f"Rank     : {i + 1}")
        print(
            f"Page     : "
            f"{metadatas[i]['page_number']}"
        )
        print(
            f"Chunk ID : "
            f"{metadatas[i]['chunk_id']}"
        )
        print(
            f"Distance : "
            f"{distances[i]:.4f}"
        )

        print("\nContext:")
        print(documents[i])

    confidence = results["confidence"]

    print("\n" + "=" * 70)
    print("RETRIEVAL CONFIDENCE")
    print("=" * 70)

    print(
        f"\nConfidence Score : "
        f"{confidence['score']:.4f}"
    )

    print(
        f"Confidence Level : "
        f"{confidence['level']}"
    )