import json
from pathlib import Path

import chromadb

from rag.embeddings import EmbeddingModel


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHUNKS_FILE = PROJECT_ROOT / "data" / "processed" / "autosar_chunks.json"
CHROMA_DIR = PROJECT_ROOT / "data" / "chroma"


def load_chunks():
    """Load AUTOSAR chunks from JSON."""

    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(
            f"AUTOSAR chunks file was not found at {CHUNKS_FILE}. "
            "Add a PDF under data/documents and run `python -m ingestion.save_chunks`, "
            "or upload a PDF through the application."
        )

    with CHUNKS_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return data["chunks"]


def create_vector_database():

    print("Loading AUTOSAR chunks...")

    chunks = load_chunks()

    print(f"Loaded {len(chunks)} AUTOSAR chunks.")

    # Load embedding model
    embedding_model = EmbeddingModel()

    # Persistent ChromaDB
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    # Separate collection for AUTOSAR
    collection = client.get_or_create_collection(
        name="autosar_documents"
    )

    print("Generating AUTOSAR embeddings...")

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = embedding_model.encode(texts)

    print("Storing vectors in ChromaDB...")

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

    print("AUTOSAR vector database created successfully.")
    print(
        f"Documents stored: {collection.count()}"
    )


if __name__ == "__main__":
    create_vector_database()