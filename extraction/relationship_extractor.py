import re


def extract_relationships(pages):
    relationships = []

    for page in pages:
        page_number = page["page_number"]
        text = page["text"]

        if not text:
            continue

        text_lower = text.lower()

        # PPort provides Service Instance
        if "pport" in text_lower and "provides a service instance" in text_lower:
            relationships.append({
                "source": "PPort",
                "relationship": "provides",
                "target": "Service Instance",
                "page": page_number
            })

        # RPort consumes Service Instance
        if "rport" in text_lower and "consumes a service instance" in text_lower:
            relationships.append({
                "source": "RPort",
                "relationship": "consumes",
                "target": "Service Instance",
                "page": page_number
            })

        # Port typed by Service Interface defines Service Instance
        if (
            "port" in text_lower
            and "typed by a service interface" in text_lower
            and "defines a service instance" in text_lower
        ):
            relationships.append({
                "source": "Port",
                "relationship": "typed_by",
                "target": "Service Interface",
                "page": page_number
            })

    return relationships