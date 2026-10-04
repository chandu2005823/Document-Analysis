import logging
from pathlib import Path


logger = logging.getLogger(__name__)


def _clean_cell(value):
    if value is None:
        return ""
    return " ".join(str(value).split()).replace("|", r"\|")


def table_to_markdown(table):
    """Convert a pdfplumber table to Markdown, or return an empty string if malformed."""
    if not isinstance(table, (list, tuple)):
        return ""

    rows = []
    for row in table:
        if not isinstance(row, (list, tuple)):
            return ""
        cleaned_row = [_clean_cell(cell) for cell in row]
        if any(cleaned_row):
            rows.append(cleaned_row)

    if len(rows) < 2:
        return ""

    column_count = max(len(row) for row in rows)
    if column_count < 2:
        return ""

    normalized_rows = [row + [""] * (column_count - len(row)) for row in rows]
    markdown_rows = [
        "| " + " | ".join(normalized_rows[0]) + " |",
        "| " + " | ".join(["---"] * column_count) + " |",
    ]
    markdown_rows.extend(
        "| " + " | ".join(row) + " |" for row in normalized_rows[1:]
    )
    return "\n".join(markdown_rows)


def extract_tables_from_pdf(pdf_path):
    """Extract detected tables page-by-page while preserving their PDF provenance."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        import pdfplumber
    except ImportError as error:
        logger.warning("Table extraction is unavailable: %s", error)
        return []

    tables = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                try:
                    detected_tables = page.extract_tables() or []
                except Exception as error:
                    logger.warning("Table extraction failed on page %d: %s", page_number, error)
                    continue

                page_table_count = 0
                for detected_table in detected_tables:
                    try:
                        content = table_to_markdown(detected_table)
                    except Exception as error:
                        logger.warning("Malformed table on page %d: %s", page_number, error)
                        continue
                    if not content:
                        continue

                    page_table_count += 1
                    tables.append({
                        "table_id": f"table_{page_number}_{page_table_count}",
                        "page_number": page_number,
                        "source_file": pdf_path.name,
                        "extraction_method": "table",
                        "content": content,
                    })
    except Exception as error:
        logger.warning("Could not extract tables from %s: %s", pdf_path, error)

    return tables


def create_table_chunks(tables, start_chunk_id=0):
    """Create separately typed chunks from extracted table records."""
    chunks = []
    for table in tables:
        content = table.get("content", "")
        if not content:
            continue
        chunks.append({
            "text": content,
            "page_number": table["page_number"],
            "chunk_id": start_chunk_id + len(chunks),
            "chunk_type": "table",
            "table_id": table["table_id"],
            "source_file": table["source_file"],
            "extraction_method": "table",
        })
    return chunks