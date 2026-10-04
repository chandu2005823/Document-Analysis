def create_chunks(pages, chunk_size=1000, overlap=150, source_file=None):
    chunks = []

    for page in pages:
        page_number = page["page_number"]
        text = page["text"]

        if not text:
            continue

        start = 0

        while start < len(text):

            end = start + chunk_size

            chunk_text = text[start:end]

            chunk = {
                "text": chunk_text,
                "page_number": page_number,
                "chunk_id": len(chunks),
                "chunk_type": "text",
                "extraction_method": page.get("extraction_method", "text"),
            }
            chunk_source = page.get("source_file", source_file)
            if chunk_source is not None:
                chunk["source_file"] = chunk_source
            chunks.append(chunk)

            start = end - overlap

    return chunks