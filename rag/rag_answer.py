from rag.citation import format_sources
from rag.groq_client import generate_answer
from rag.rag_pipeline import retrieve_context
from database.access_control import prompt_for_user_project


def build_context(results):

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    context_parts = []

    for i, (document, metadata) in enumerate(
        zip(documents, metadatas),
        start=1
    ):

        context_parts.append(
            f"""
SOURCE {i}

Page: {metadata['page_number']}
Chunk ID: {metadata['chunk_id']}

CONTENT:
{document}
"""
        )

    return "\n".join(context_parts)


def answer_question(query, top_k=5, *, user_id, project_id):

    # Retrieve context and confidence
    results = retrieve_context(
        query,
        top_k=top_k,
        user_id=user_id,
        project_id=project_id,
    )

    confidence = results["confidence"]

    # Build document context
    context = build_context(results)

    # Grounded generation prompt
    prompt = f"""
You are an engineering document analysis assistant.

Answer the user's question ONLY using the
provided AUTOSAR document context.

Rules:

- Use only information explicitly supported by the context.
- Do not use outside knowledge.
- Do not invent information.
- Do not expand or interpret statements beyond what
  the document says.
- If the context supports only a short answer,
  give only the short answer.
- If the context does not contain enough information,
  say:
  "I could not find enough information in the document."
- Keep the answer concise and technically accurate.
- Do not create citations yourself.
- The application will add citations separately.

DOCUMENT CONTEXT:

{context}

USER QUESTION:

{query}
"""

    answer = generate_answer(prompt)

    sources = format_sources(results)

    return answer, sources, confidence


if __name__ == "__main__":

    user, project = prompt_for_user_project()
    query = input("\nEnter your question: ")

    answer, sources, confidence = answer_question(
        query,
        top_k=5,
        user_id=user["id"],
        project_id=project["id"],
    )

    print("\n" + "=" * 70)
    print("RAG ANSWER")
    print("=" * 70)

    print(answer)

    print("\n" + "=" * 70)
    print("RETRIEVAL CONFIDENCE")
    print("=" * 70)

    print(
        f"Confidence Score : {confidence['score']:.4f}"
    )

    print(
        f"Confidence Level : {confidence['level']}"
    )

    print("\n" + "=" * 70)
    print("SOURCES")
    print("=" * 70)

    for source in sources:

        print(
            f"[{source['source_number']}] "
            f"Page {source['page']} | "
            f"Chunk {source['chunk_id']}"
        )