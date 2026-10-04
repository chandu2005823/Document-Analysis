import json
from pathlib import Path

from pdf_parser import extract_text_from_pdf
from chunker import create_chunks
from table_extractor import create_table_chunks, extract_tables_from_pdf


def process_document(pdf_file, output_file):
    # Extract pages
    pages = extract_text_from_pdf(pdf_file)

    # Create chunks
    text_chunks = create_chunks(pages, source_file=Path(pdf_file).name)
    tables = extract_tables_from_pdf(pdf_file)
    table_chunks = create_table_chunks(tables, start_chunk_id=len(text_chunks))
    chunks = text_chunks + table_chunks

    # Prepare output
    data = {
        "source_file": str(pdf_file),
        "total_pages": len(pages),
        "total_chunks": len(chunks),
        "total_text_chunks": len(text_chunks),
        "total_table_chunks": len(table_chunks),
        "total_tables": len(tables),
        "tables": tables,
        "chunks": chunks
    }

    # Create output directory
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print("Document processing completed.")
    print(f"Pages: {len(pages)}")
    print(f"Chunks: {len(chunks)}")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":

   pdf_file = "data/documents/AUTOSAR_AP_EXP_SWArchitecture.pdf"
   output_file = "data/processed/autosar_chunks.json"

   process_document(pdf_file, output_file)