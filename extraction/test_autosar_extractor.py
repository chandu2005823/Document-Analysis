import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.append(str(PROJECT_ROOT / "ingestion"))

from pdf_parser import extract_text_from_pdf
from architecture_extractor import extract_architecture_entities


PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "documents"
    / "AUTOSAR_AP_EXP_SWArchitecture.pdf"
)


print("Loading AUTOSAR document...")

pages = extract_text_from_pdf(PDF_PATH)

print(f"Pages loaded: {len(pages)}")


# Combine the extracted page text
full_text = "\n".join(
    page["text"]
    for page in pages
)


print(f"Characters extracted: {len(full_text)}")


# Run entity extraction
entities = extract_architecture_entities(full_text)


print("\n")
print("AUTOSAR ARCHITECTURE ENTITIES")
print("=============================")


for category, values in entities.items():

    print(f"\n{category.upper()}:")

    if not values:
        print("  None detected")
        continue

    for value in values:
        print(f"  - {value}")