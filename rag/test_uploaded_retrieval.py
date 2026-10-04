from database.access_control import prompt_for_user_project
from retriever import search_documents


def search_uploaded_document(query, top_k=5, *, user_id, project_id):
    return search_documents(
        query,
        top_k=top_k,
        user_id=user_id,
        project_id=project_id,
    )


if __name__ == "__main__":

    user, project = prompt_for_user_project()
    query = input(
        "\nEnter your question: "
    )

    results = search_uploaded_document(
        query,
        top_k=5,
        user_id=user["id"],
        project_id=project["id"],
    )

    print("\n" + "=" * 70)
    print("UPLOADED DOCUMENT RETRIEVAL")
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