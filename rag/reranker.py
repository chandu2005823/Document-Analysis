import re


STOP_WORDS = {
    "what",
    "are",
    "the",
    "is",
    "used",
    "to",
    "describe",
    "main",
    "of",
    "and",
    "in",
    "for",
    "a",
    "an",
    "does",
    "do",
    "how",
    "which"
}


IMPORTANT_TERMS = {
    "architecture",
    "architectural",
    "structural",
    "behavioral",
    "views",
    "approach",
    "platform",
    "service",
    "communication",
    "interface"
}


def tokenize(text):

    words = re.findall(r"\b[^\W\d_]{3,}\b", text.lower(), flags=re.UNICODE)

    return {
        word
        for word in words
        if word not in STOP_WORDS
    }


def calculate_keyword_score(query, document):

    query_words = tokenize(query)
    document_words = tokenize(document)

    if not query_words:
        return 0.0

    matched = query_words.intersection(document_words)

    return len(matched) / len(query_words)


def calculate_important_term_score(query, document):

    query_words = tokenize(query)
    document_words = tokenize(document)

    important_query_terms = {
        word
        for word in query_words
        if word in IMPORTANT_TERMS
    }

    if not important_query_terms:
        return 0.0

    matched = (
        important_query_terms
        .intersection(document_words)
    )

    return len(matched) / len(important_query_terms)


def calculate_architecture_evidence_score(document):

    document_lower = document.lower()

    evidence_terms = [
        "structural architecture",
        "behavioral architecture",
        "architecture views",
        "architectural approach",
        "architecture description"
    ]

    matches = 0

    for term in evidence_terms:

        if term in document_lower:
            matches += 1

    return matches / len(evidence_terms)


def rerank_results(results):

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    query = results.get("query", "")
    metadata_query_type = results.get("metadata_query_type")

    ranked = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances
    ):

        semantic_score = 1 / (1 + distance)

        keyword_score = calculate_keyword_score(
            query,
            document
        )

        important_term_score = (
            calculate_important_term_score(
                query,
                document
            )
        )

        evidence_score = (
            calculate_architecture_evidence_score(
                document
            )
        )

        metadata_score = 0.0
        if metadata_query_type == "title":
            metadata_score = 1.0 if metadata.get("page_number", 0) <= 2 else 0.0
        elif metadata_query_type == "author":
            metadata_score = 1.0 if metadata.get("page_number", 0) <= 3 else 0.0
        elif metadata_query_type == "publication":
            metadata_score = 1.0 if metadata.get("page_number", 0) <= 5 else 0.0

        final_score = (
            0.60 * semantic_score
            + 0.15 * keyword_score
            + 0.10 * important_term_score
            + 0.05 * evidence_score
            + 0.10 * metadata_score
        )

        ranked.append({
            "document": document,
            "metadata": metadata,
            "distance": distance,
            "semantic_score": semantic_score,
            "keyword_score": keyword_score,
            "important_term_score": important_term_score,
            "evidence_score": evidence_score,
            "final_score": final_score
        })

    ranked.sort(
        key=lambda x: x["final_score"],
        reverse=True
    )

    return ranked