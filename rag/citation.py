def format_sources(results):
    """
    Generate source references directly from
    ChromaDB metadata.
    """

    sources = []

    metadatas = results["metadatas"][0]

    for i, metadata in enumerate(metadatas):

        source = {
            "source_number": i + 1,
            "page": metadata["page_number"],
            "chunk_id": metadata["chunk_id"]
        }

        sources.append(source)

    return sources


def display_sources(results):

    sources = format_sources(results)

    print("\n" + "=" * 70)
    print("SOURCES")
    print("=" * 70)

    for source in sources:

        print(
            f"[{source['source_number']}] "
            f"Page {source['page']} | "
            f"Chunk {source['chunk_id']}"
        )