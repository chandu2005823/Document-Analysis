def _normalize_record(record):
    entity = str(record.get("entity", "")).strip()
    entity_type = str(record.get("type", "")).strip()
    page = record.get("page")
    if page is None:
        page = record.get("new_page") or record.get("old_page")
    return {
        "entity": entity,
        "type": entity_type,
        "page": page,
    }


def compare_entities(old_records, new_records):
    old_by_key = {}
    for record in old_records:
        normalized = _normalize_record(record)
        key = (normalized["entity"], normalized["type"])
        old_by_key[key] = normalized

    new_by_key = {}
    for record in new_records:
        normalized = _normalize_record(record)
        key = (normalized["entity"], normalized["type"])
        new_by_key[key] = normalized

    added = []
    for key in sorted(new_by_key.keys() - old_by_key.keys()):
        record = new_by_key[key]
        added.append(
            {
                "entity": record["entity"],
                "type": record["type"],
                "new_page": record.get("page"),
            }
        )

    removed = []
    for key in sorted(old_by_key.keys() - new_by_key.keys()):
        record = old_by_key[key]
        removed.append(
            {
                "entity": record["entity"],
                "type": record["type"],
                "old_page": record.get("page"),
            }
        )

    unchanged = []
    for key in sorted(old_by_key.keys() & new_by_key.keys()):
        old_record = old_by_key[key]
        new_record = new_by_key[key]

        old_page = old_record.get("page")
        new_page = new_record.get("page")

        item = {
            "entity": old_record["entity"],
            "type": old_record["type"],
            "old_page": old_page,
            "new_page": new_page,
            "page_changed": old_page != new_page and old_page is not None and new_page is not None,
        }

        if old_page is not None and new_page is not None and old_page != new_page:
            item["page_changed"] = True
            item["page_change"] = f"{old_page} → {new_page}"
        elif old_page is not None and new_page is not None:
            item["page_changed"] = False
            item["page_change"] = None
        else:
            item["page_changed"] = False
            item["page_change"] = None

        unchanged.append(item)

    return {
        "added": added,
        "removed": removed,
        "unchanged": unchanged,
    }