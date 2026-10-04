def build_context(results):
    """
    Convert ChromaDB search results into
    structured context for an LLM.
    """

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    context_parts = []

    for i in range(len(documents)):

        page = metadatas[i]["page_number"]
        chunk_id = metadatas[i]["chunk_id"]
        distance = distances[i]

        context_parts.append(
            f"""
SOURCE {i + 1}
Page: {page}
Chunk ID: {chunk_id}
Distance: {distance:.4f}

CONTENT:
{documents[i]}
"""
        )

    return "\n".join(context_parts)


if __name__ == "__main__":

    sample_results = {
        "documents": [["Example document text"]],
        "metadatas": [[{
            "page_number": 1,
            "chunk_id": 0
        }]],
        "distances": [[0.5]]
    }

    context = build_context(sample_results)

    print(context)