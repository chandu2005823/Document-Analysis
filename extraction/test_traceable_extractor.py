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


pages = extract_text_from_pdf(PDF_PATH)


print("TRACEABLE ENTITY TEST")
print("=====================")


for page in pages:

    text = page["text"]

    if not text:
        continue

    entities = extract_architecture_entities(text)

    found = False

    for category, values in entities.items():

        if values:

            if not found:
                print(f"\nPAGE {page['page_number']}")
                found = True

            print(f"\n{category.upper()}:")

            for value in values:
                print(f"  - {value}")