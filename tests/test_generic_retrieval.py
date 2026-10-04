import pytest
import numpy as np

from rag import confidence, grounding_guard, rag_pipeline, reranker, retriever


def test_metadata_questions_route_to_early_page_search(monkeypatch):
    calls = []

    def metadata_search(query, **kwargs):
        calls.append((query, kwargs))
        return {
            "documents": [["Architectural Styles\nA Visual Guide"]],
            "metadatas": [[{"page_number": 2, "chunk_id": 0}]],
            "distances": [[0.0]],
            "query": query,
        }

    monkeypatch.setattr(rag_pipeline, "search_document_metadata", metadata_search)
    monkeypatch.setattr(rag_pipeline, "rerank_results", lambda results: [{
        "document": results["documents"][0][0],
        "metadata": results["metadatas"][0][0],
        "distance": 0.0,
        "final_score": 0.9,
    }])
    monkeypatch.setattr(rag_pipeline, "load_relationships", lambda **_kwargs: [])

    result = rag_pipeline.retrieve_context(
        "What is the book called?", user_id=1, project_id=1
    )

    assert calls == [("What is the book called?", {"top_k": 8, "user_id": 1, "project_id": 1})]
    assert result["documents"] == [["Architectural Styles\nA Visual Guide"]]
    assert result["metadata_query_type"] == "title"


@pytest.mark.parametrize(
    ("question", "query_type"),
    [
        ("Who is the author?", "author"),
        ("When was it published?", "publication"),
    ],
)
def test_metadata_question_types_are_detected(question, query_type):
    assert rag_pipeline.metadata_query_type(question) == query_type


def test_generic_retrieval_keeps_semantic_results_above_old_cutoff(monkeypatch):
    class FakeEmbeddingModel:
        def encode(self, _texts):
            return np.asarray([[1.0, 0.0]])

    class FakeCollection:
        def query(self, **_kwargs):
            return {
                "documents": [["A pendentive dome transfers a circular base to a square plan."]],
                "metadatas": [[{"page_number": 18, "chunk_id": 4}]],
                "distances": [[1.35]],
            }

        def get(self, **_kwargs):
            return {
                "documents": ["A pendentive dome transfers a circular base to a square plan."],
                "metadatas": [{"page_number": 18, "chunk_id": 4}],
            }

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def get_collection(self, **_kwargs):
            return FakeCollection()

    monkeypatch.setattr(retriever, "EmbeddingModel", FakeEmbeddingModel)
    monkeypatch.setattr(retriever.chromadb, "PersistentClient", FakeClient)
    monkeypatch.setattr(retriever, "project_collection_name", lambda *_args: "autosar_project_1")

    result = retriever.search_documents(
        "What is a pendentive dome?", user_id=1, project_id=1
    )

    assert result["documents"][0]
    assert result["distances"][0] == [1.35]


def test_confidence_is_nonzero_without_autosar_evidence():
    ranked = [{
        "final_score": 0.42,
        "semantic_score": 0.8,
        "evidence_score": 0.0,
    }]

    result = confidence.calculate_confidence(ranked)

    assert result["score"] > 0.0
    assert result["level"] == "Medium"


def test_short_title_answer_is_grounded_by_title_context():
    result = grounding_guard.check_grounding(
        "Architectural Styles: A Visual Guide",
        "Architectural Styles\nA Visual Guide",
    )

    assert result["supported"] is True
    assert result["score"] > 0.0


def test_explicit_architecture_views_are_grounded_when_source_inserts_connectors():
    result = grounding_guard.check_grounding(
        "The main views are the structural architecture view and the behavioral architecture view.",
        "The software architecture defines the details of the structural and the behavioral architecture views.",
    )

    assert result["supported"] is True


def test_unrelated_autosar_answer_is_not_grounded_by_history_context():
    result = grounding_guard.check_grounding(
        "The AUTOSAR Adaptive Platform is a software platform for automotive systems.",
        "Architectural Styles\nA Visual Guide\nAncient Greek architecture uses orders and proportion.",
    )

    assert result["supported"] is False


def test_autosar_reranking_preserves_architecture_evidence():
    result = reranker.rerank_results({
        "query": "What are the main views used to describe the Adaptive Platform architecture?",
        "documents": [[
            "The structural architecture view and behavioral architecture view describe the Adaptive Platform."
        ]],
        "metadatas": [[{"page_number": 10, "chunk_id": 1}]],
        "distances": [[0.2]],
    })

    assert result[0]["evidence_score"] > 0.0
    assert result[0]["final_score"] > 0.0