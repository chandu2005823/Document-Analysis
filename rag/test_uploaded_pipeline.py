from rag_pipeline import retrieve_context
from database.access_control import prompt_for_user_project


def main():
    user, project = prompt_for_user_project()
    query = input("\nEnter your question: ")

    results = retrieve_context(
        query,
        top_k=5,
        user_id=user["id"],
        project_id=project["id"],
    )


    print("\n" + "=" * 70)
    print("UPLOADED DOCUMENT RAG PIPELINE")
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


    print("\n" + "=" * 70)
    print("COLLECTION")
    print("=" * 70)

    print(
        results["collection_name"]
    )


if __name__ == "__main__":
    main()