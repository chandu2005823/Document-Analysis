from document_comparison import compare_entities


old_records = [
    {
        "entity": "PPort",
        "type": "ports"
    }
]

new_records = [
    {
        "entity": "PPort",
        "type": "ports"
    },
    {
        "entity": "RPort",
        "type": "ports"
    }
]


result = compare_entities(old_records, new_records)

print("Added:", result["added"])
print("Removed:", result["removed"])
print("Unchanged:", result["unchanged"])