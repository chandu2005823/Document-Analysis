from pathlib import Path
import json

from pdf_parser import extract_text_from_pdf
from chunker import create_chunks
from table_extractor import create_table_chunks, extract_tables_from_pdf


def process_uploaded_pdf(pdf_path, output_path):
    """
    Extract text from an uploaded PDF and create chunks.
    """

    pdf_path = Path(pdf_path)
    output_path = Path(output_path)

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    print("\nProcessing PDF...")
    print(f"File: {pdf_path.name}")

    # Step 1: Extract pages
    pages = extract_text_from_pdf(pdf_path)

    print(f"Pages extracted: {len(pages)}")

    # Step 2: Create chunks
    text_chunks = create_chunks(pages, source_file=pdf_path.name)
    tables = extract_tables_from_pdf(pdf_path)
    table_chunks = create_table_chunks(tables, start_chunk_id=len(text_chunks))
    chunks = text_chunks + table_chunks

    print(f"Chunks created: {len(chunks)}")

    # Step 3: Prepare output
    data = {
        "source_file": pdf_path.name,
        "total_pages": len(pages),
        "total_chunks": len(chunks),
        "total_text_chunks": len(text_chunks),
        "total_table_chunks": len(table_chunks),
        "total_tables": len(tables),
        "tables": tables,
        "chunks": chunks,
    }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Step 4: Save JSON
    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n" + "=" * 60)
    print("PDF PROCESSING COMPLETE")
    print("=" * 60)

    print(f"Pages  : {len(pages)}")
    print(f"Chunks : {len(chunks)}")
    print(f"Output : {output_path}")


if __name__ == "__main__":

    pdf_file = input(
        "\nEnter PDF path: "
    ).strip()

    output_file = (
        "data/processed/uploaded_chunks.json"
    )

    process_uploaded_pdf(
        pdf_file,
        output_file
    )