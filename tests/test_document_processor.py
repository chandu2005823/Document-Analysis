from pathlib import Path

import pytest
import pymupdf

from frontend import document_processor


class UploadedFile:
    def __init__(self, name, payload):
        self.name = name
        self.payload = payload

    def getbuffer(self):
        return memoryview(self.payload)


def configure_processor(monkeypatch, tmp_path):
    monkeypatch.setattr(document_processor, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(document_processor, "can_upload", lambda *_args: True)
    monkeypatch.setattr(
        document_processor,
        "require_project_access",
        lambda *_args: {"id": 7, "name": "Upload Test", "role": "admin"},
    )


def test_zero_byte_upload_has_clear_error_and_skips_pdf_extraction(monkeypatch, tmp_path):
    configure_processor(monkeypatch, tmp_path)
    extraction_called = False

    def extract_text(_pdf_path):
        nonlocal extraction_called
        extraction_called = True
        return []

    monkeypatch.setattr(document_processor, "extract_text_from_pdf", extract_text)

    with pytest.raises(ValueError, match=r"Uploaded file is empty \(0 bytes\)\. Please select a valid PDF\."):
        document_processor.process_uploaded_pdf(
            UploadedFile("empty.pdf", b""), user_id=1, project_id=7
        )

    assert extraction_called is False


def test_valid_pdf_reaches_existing_processing_pipeline(monkeypatch, tmp_path):
    configure_processor(monkeypatch, tmp_path)
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "Architecture")
    valid_pdf = document.tobytes()
    document.close()
    extraction_paths = []
    monkeypatch.setattr(
        document_processor,
        "extract_text_from_pdf",
        lambda path: extraction_paths.append(Path(path)) or [{"page_number": 1, "text": "Architecture"}],
    )
    monkeypatch.setattr(
        document_processor,
        "create_chunks",
        lambda pages, source_file: [{"text": pages[0]["text"], "page_number": 1, "chunk_id": 0}],
    )
    monkeypatch.setattr(document_processor, "extract_tables_from_pdf", lambda _path: [])
    monkeypatch.setattr(document_processor, "create_table_chunks", lambda _tables, start_chunk_id: [])
    monkeypatch.setattr(document_processor, "extract_traceable_entities", lambda _pages: [])
    monkeypatch.setattr(document_processor, "extract_relationships", lambda _pages: [])
    monkeypatch.setattr(document_processor, "get_document_version", lambda *args, **kwargs: {
        "document_id": "p7_valid_v1",
        "version": 1,
        "upload_timestamp": "2026-09-30T00:00:00Z",
    })
    monkeypatch.setattr(document_processor, "project_collection_name", lambda *_args: "autosar_project_7")
    monkeypatch.setattr(document_processor, "build_uploaded_database", lambda *args, **kwargs: None)
    monkeypatch.setattr(document_processor, "create_document_record", lambda *args, **kwargs: None)

    result = document_processor.process_uploaded_pdf(
        UploadedFile("valid.pdf", valid_pdf), user_id=1, project_id=7
    )

    assert result["filename"] == "valid.pdf"
    assert result["version"] == 1
    assert len(extraction_paths) == 1
    assert extraction_paths[0].stat().st_size > 0