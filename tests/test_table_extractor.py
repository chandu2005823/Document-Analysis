import json

import pdfplumber
import pymupdf

from ingestion.chunker import create_chunks
from ingestion.process_uploaded import process_uploaded_pdf
from ingestion.table_extractor import (
    create_table_chunks,
    extract_tables_from_pdf,
    table_to_markdown,
)


def create_controlled_pdf(pdf_path):
    document = pymupdf.open()
    page = document.new_page(width=420, height=180)
    column_lines = [50, 150, 250, 350]
    row_lines = [50, 80, 110]

    for y_position in row_lines:
        page.draw_line((50, y_position), (350, y_position))
    for x_position in column_lines:
        page.draw_line((x_position, 50), (x_position, 110))

    values = [
        ["Name", "Type", "Description"],
        ["PPort", "Provided Port", "Provides service"],
    ]
    for row_index, row in enumerate(values):
        for column_index, value in enumerate(row):
            page.insert_text(
                (column_lines[column_index] + 4, row_lines[row_index] + 19),
                value,
            )

    text_page = document.new_page()
    text_page.insert_text((50, 80), "This page has ordinary text and no table.")
    document.save(pdf_path)
    document.close()
    return pdf_path


def test_extract_tables_from_controlled_pdf_preserves_metadata(tmp_path):
    pdf_path = create_controlled_pdf(tmp_path / "controlled.pdf")

    tables = extract_tables_from_pdf(pdf_path)

    assert len(tables) == 1
    assert tables[0] == {
        "table_id": "table_1_1",
        "page_number": 1,
        "source_file": "controlled.pdf",
        "extraction_method": "table",
        "content": (
            "| Name | Type | Description |\n"
            "| --- | --- | --- |\n"
            "| PPort | Provided Port | Provides service |"
        ),
    }
    assert all(table["page_number"] != 2 for table in tables)


def test_table_to_markdown_cleans_cells_and_rejects_malformed_tables():
    markdown = table_to_markdown([
        [" Name\nValue ", "Type", "Description"],
        ["P|Port", "Provided Port", None],
    ])

    assert markdown == (
        "| Name Value | Type | Description |\n"
        "| --- | --- | --- |\n"
        r"| P\|Port | Provided Port |  |"
    )
    assert table_to_markdown([["Only one column"], ["Still one column"]]) == ""
    assert table_to_markdown([["Header", 1], None]) == ""


def test_page_failure_and_malformed_table_do_not_stop_later_pages(tmp_path, monkeypatch):
    pdf_path = tmp_path / "mocked.pdf"
    pdf_path.touch()

    class FakePage:
        def __init__(self, tables=None, error=None):
            self.tables = tables
            self.error = error

        def extract_tables(self):
            if self.error:
                raise self.error
            return self.tables

    class FakePDF:
        pages = [
            FakePage(error=RuntimeError("page cannot be read")),
            FakePage(tables=[[['One column'], ['Not a table']]]),
            FakePage(tables=[[['Name', 'Type'], ['PPort', 'Provided Port']]]),
        ]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(pdfplumber, "open", lambda _path: FakePDF())

    tables = extract_tables_from_pdf(pdf_path)

    assert len(tables) == 1
    assert tables[0]["page_number"] == 3
    assert tables[0]["table_id"] == "table_3_1"


def test_chunks_preserve_text_ocr_and_table_provenance():
    text_chunks = create_chunks(
        [{"page_number": 4, "text": "OCR extracted words", "extraction_method": "ocr"}],
        source_file="scan.pdf",
    )
    table_chunks = create_table_chunks(
        [{
            "table_id": "table_4_1",
            "page_number": 4,
            "source_file": "scan.pdf",
            "extraction_method": "table",
            "content": "| A | B |\n| --- | --- |\n| x | y |",
        }],
        start_chunk_id=len(text_chunks),
    )

    assert text_chunks[0]["chunk_type"] == "text"
    assert text_chunks[0]["extraction_method"] == "ocr"
    assert text_chunks[0]["source_file"] == "scan.pdf"
    assert table_chunks[0] == {
        "text": "| A | B |\n| --- | --- |\n| x | y |",
        "page_number": 4,
        "chunk_id": 1,
        "chunk_type": "table",
        "table_id": "table_4_1",
        "source_file": "scan.pdf",
        "extraction_method": "table",
    }


def test_uploaded_document_pipeline_keeps_tables_separate_and_chunks_them(tmp_path):
    pdf_path = create_controlled_pdf(tmp_path / "controlled.pdf")
    output_path = tmp_path / "processed" / "chunks.json"

    process_uploaded_pdf(pdf_path, output_path)

    with output_path.open(encoding="utf-8") as file:
        data = json.load(file)

    assert data["total_pages"] == 2
    assert data["total_tables"] == 1
    assert data["total_text_chunks"] == 2
    assert data["total_table_chunks"] == 1
    assert len(data["tables"]) == 1
    assert [chunk["chunk_type"] for chunk in data["chunks"]] == ["text", "text", "table"]
    assert [chunk["chunk_id"] for chunk in data["chunks"]] == [0, 1, 2]
    assert all(chunk["source_file"] == "controlled.pdf" for chunk in data["chunks"])