import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.append(str(PROJECT_ROOT / "ingestion"))
sys.path.append(str(PROJECT_ROOT / "extraction"))
sys.path.append(str(PROJECT_ROOT / "database"))

from pdf_parser import extract_text_from_pdf
from traceability import extract_traceable_entities
from traceability_store import save_traceability


PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "documents"
    / "AUTOSAR_AP_EXP_SWArchitecture.pdf"
)


print("Loading document...")

pages = extract_text_from_pdf(PDF_PATH)

print(f"Pages loaded: {len(pages)}")


# ---------------------------------------------------------
# Extract traceability records
# ---------------------------------------------------------

traceability = extract_traceable_entities(pages)


# ---------------------------------------------------------
# Save traceability records
# ---------------------------------------------------------

save_traceability(traceability)

print(
    f"\nSaved {len(traceability)} records to:"
    f"\n{PROJECT_ROOT / 'data' / 'processed' / 'traceability.json'}"
)


# ---------------------------------------------------------
# Display sample records
# ---------------------------------------------------------

print("\nTRACEABILITY RECORDS")
print("====================")

for record in traceability[:30]:

    print(
        f"{record['type']:20} | "
        f"{record['entity']:50} | "
        f"Page {record['page']}"
    )


print(
    f"\nTotal traceability records: "
    f"{len(traceability)}"
)