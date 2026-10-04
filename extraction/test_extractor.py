from architecture_extractor import extract_architecture_entities


text = """
The AUTOSAR Adaptive Platform follows the concept
of a service-oriented architecture.

The architecture contains structural architecture views
and behavioral architecture views.

Applications communicate through services and interfaces.
"""


entities = extract_architecture_entities(text)

print("\nARCHITECTURE ENTITIES")
print("=====================")

for category, values in entities.items():
    print(f"\n{category.upper()}:")

    for value in values:
        print(f"  - {value}")
        