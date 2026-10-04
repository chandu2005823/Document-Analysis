from retriever import search_documents
from reranker import rerank_results
from database.access_control import prompt_for_user_project


def retrieve_context(query, top_k=5, *, user_id, project_id):

    # Retrieve a larger candidate set
    results = search_documents(
        query,
        top_k=8,
        max_distance=1.0,
        user_id=user_id,
        project_id=project_id,
    )

    # Rerank candidates
    ranked_results = rerank_results(results)

    # Keep the strongest results
    selected = ranked_results[:top_k]

    # Convert reranked results back into the structure
    # expected by the context builder
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

    reranked_results = {
        "documents": [documents],
        "metadatas": [metadatas],
        "distances": [distances]
    }

    return reranked_results


if __name__ == "__main__":

    user, project = prompt_for_user_project()
    query = input("\nEnter your question: ")

    results = retrieve_context(
        query,
        top_k=5,
        user_id=user["id"],
        project_id=project["id"],
    )

    print("\n" + "=" * 70)
    print("RERANKED RAG CONTEXT")
    print("=" * 70)

    for i, document in enumerate(
        results["documents"][0],
        start=1
    ):

        metadata = results["metadatas"][0][i - 1]

        print("\n" + "-" * 70)

        print(f"Rank  : {i}")
        print(f"Page  : {metadata['page_number']}")
        print(f"Chunk : {metadata['chunk_id']}")

        print("\nContext:")
        print(document)