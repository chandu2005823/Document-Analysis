import pymupdf

from analysis.document_comparison import compare_entities
from extraction.architecture_extractor import extract_architecture_entities
from extraction.relationship_extractor import extract_relationships
from ingestion.chunker import create_chunks
from ingestion.pdf_parser import extract_text_from_pdf
from database.traceability_store import save_traceability, load_traceability
from rag.confidence import calculate_confidence
from rag.grounding_guard import check_grounding


def test_compare_entities_detects_adds_removes_and_page_changes():
    old_records = [
        {"entity": "PPort", "type": "ports", "page": 260},
        {"entity": "Legacy Interface", "type": "interfaces", "page": 250},
        {"entity": "Service Instance", "type": "services", "page": 260},
    ]
    new_records = [
        {"entity": "PPort", "type": "ports", "page": 270},
        {"entity": "RPort", "type": "ports", "page": 260},
        {"entity": "Service Instance", "type": "services", "page": 260},
    ]

    result = compare_entities(old_records, new_records)

    assert result["added"]
    assert result["removed"]
    assert any(item["entity"] == "PPort" and item["page_changed"] for item in result["unchanged"])
    assert any(item["entity"] == "RPort" and item["type"] == "ports" for item in result["added"])
    assert any(item["entity"] == "Legacy Interface" and item["type"] == "interfaces" for item in result["removed"])
    assert any(item["entity"] == "Service Instance" for item in result["unchanged"])


def test_extract_text_from_pdf_returns_pages(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Architecture PDF extraction fixture.")
    document.save(pdf_path)
    document.close()

    pages = extract_text_from_pdf(pdf_path)

    assert len(pages) == 1
    assert "Architecture PDF extraction fixture." in pages[0]["text"]


def test_chunker_creates_overlap_chunks():
    pages = [{"page_number": 1, "text": "A" * 2500}]
    chunks = create_chunks(pages, chunk_size=1000, overlap=150)

    assert len(chunks) > 1
    assert chunks[0]["page_number"] == 1
    assert chunks[0]["chunk_id"] == 0


def test_architecture_extractor_extracts_known_terms():
    text = "PPort provides a service instance. RPort consumes a service instance. WatchdogInterface is used."
    entities = extract_architecture_entities(text)

    assert "PPort" in entities["ports"]
    assert "RPort" in entities["ports"]
    assert "WatchdogInterface" in entities["interfaces"]


def test_relationship_extractor_extracts_example_relationships():
    pages = [{"page_number": 260, "text": "PPort provides a service instance. RPort consumes a service instance."}]
    relationships = extract_relationships(pages)

    assert any(r["source"] == "PPort" and r["relationship"] == "provides" for r in relationships)
    assert any(r["source"] == "RPort" and r["relationship"] == "consumes" for r in relationships)


def test_confidence_calculation_returns_valid_output():
    ranked_results = [
        {"final_score": 0.9},
        {"final_score": 0.7},
    ]

    result = calculate_confidence(ranked_results)

    assert 0.0 <= result["score"] <= 1.0
    assert result["level"] in {"Low", "Medium", "High"}


def test_grounding_guard_accepts_supported_answer():
    answer = "PPort provides a service instance."
    context = "PPort provides a service instance in the architecture description."
    result = check_grounding(answer, context)

    assert result["supported"] is True


def test_traceability_store_roundtrip(tmp_path):
    records = [{"entity": "PPort", "type": "ports", "page": 260}]
    output_file = tmp_path / "traceability.json"

    save_traceability(records, output_file)
    loaded = load_traceability(output_file)

    assert loaded == records
