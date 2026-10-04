from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    def __init__(self):
        print("Loading embedding model...")

        self.model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

        print("Embedding model loaded.")

    def encode(self, texts):
        """
        Convert text into numerical embeddings.
        """
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        )


if __name__ == "__main__":

    embedding_model = EmbeddingModel()

    sample_text = [
        "The system provides personalized travel recommendations."
    ]

    embeddings = embedding_model.encode(sample_text)

    print("Embedding generated successfully.")
    print("Embedding shape:", embeddings.shape)
    print("First 10 values:")
    print(embeddings[0][:10])