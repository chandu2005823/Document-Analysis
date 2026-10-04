from architecture_extractor import extract_architecture_entities


def extract_traceable_entities(pages):
    """
    Extract architecture entities while preserving
    their document page numbers.
    """

    traceability = []

    for page in pages:

        page_number = page["page_number"]
        text = page["text"]

        if not text:
            continue

        entities = extract_architecture_entities(text)

        for entity_type, values in entities.items():

            for value in values:

                traceability.append({
                    "entity": value,
                    "type": entity_type,
                    "page": page_number
                })

    return traceability