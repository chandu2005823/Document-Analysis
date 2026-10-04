from grounding_guard import check_grounding


context = """
For system development of an automotive embedded computer
the software architecture usually defines the details of
the structural and the behavioral architecture views down
to module level.
"""


answer = (
    "The Adaptive Platform architecture is described "
    "using structural and behavioral architecture views."
)


result = check_grounding(
    answer,
    context
)


print("\n" + "=" * 70)
print("GROUNDING CHECK")
print("=" * 70)

print(
    f"\nOverall Score : "
    f"{result['score']:.4f}"
)

print(
    f"Supported     : "
    f"{result['supported']}"
)

for item in result["sentences"]:

    print("\nSentence:")
    print(item["sentence"])

    print(
        f"Score     : "
        f"{item['score']:.4f}"
    )

    print(
        f"Supported : "
        f"{item['supported']}"
    )