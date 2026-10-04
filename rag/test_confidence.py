from retriever import search_documents
from reranker import rerank_results
from confidence import calculate_confidence
from database.access_control import prompt_for_user_project


def main():
    user, project = prompt_for_user_project()
    query = "What are the main views used to describe the Adaptive Platform architecture?"

    print("\nRetrieving candidates...")

    results = search_documents(
        query,
        top_k=8,
        max_distance=1.0,
        user_id=user["id"],
        project_id=project["id"],
    )

    print("\nReranking candidates...")

    ranked_results = rerank_results(results)

    print("\nCalculating confidence...")

    confidence = calculate_confidence(
        ranked_results
    )

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

    print(
        f"\nTop Result Score : "
        f"{ranked_results[0]['final_score']:.4f}"
    )

    if len(ranked_results) > 1:

        print(
            f"Second Result Score : "
            f"{ranked_results[1]['final_score']:.4f}"
        )

        print(
            f"Score Separation : "
            f"{ranked_results[0]['final_score'] - ranked_results[1]['final_score']:.4f}"
        )


if __name__ == "__main__":
    main()