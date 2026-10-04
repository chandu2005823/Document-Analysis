import json
import chromadb

from embeddings import EmbeddingModel


CHUNKS_FILE = "data/processed/autosar_chunks.json"
CHROMA_DIR = "data/chroma"


def rebuild_database():

    print("Loading AUTOSAR chunks...")

    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = data["chunks"]

    print(f"Loaded {len(chunks)} chunks.")

    client = chromadb.PersistentClient(
        path=CHROMA_DIR
    )

    # Delete old AUTOSAR collection
    try:
        client.delete_collection(
            name="autosar_documents"
        )
        print("Old AUTOSAR collection deleted.")
    except Exception:
        print("No existing AUTOSAR collection found.")

    # Create fresh collection
    collection = client.create_collection(
        name="autosar_documents"
    )

    # Load embedding model
    embedding_model = EmbeddingModel()

    print("Generating embeddings...")

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = embedding_model.encode(texts)

    print("Storing vectors...")

    collection.add(
        ids=[
            f"autosar_chunk_{chunk['chunk_id']}"
            for chunk in chunks
        ],
        documents=texts,
        embeddings=embeddings.tolist(),
        metadatas=[
            {
                "page_number": chunk["page_number"],
                "chunk_id": chunk["chunk_id"],
                "document": "AUTOSAR_AP_EXP_SWArchitecture_R25-11",
                "platform": "AUTOSAR Adaptive Platform",
                "release": "R25-11"
            }
            for chunk in chunks
        ]
    )

    print()
    print("=" * 60)
    print("AUTOSAR DATABASE REBUILT")
    print("=" * 60)
    print(f"Documents stored: {collection.count()}")


if __name__ == "__main__":
    rebuild_database()