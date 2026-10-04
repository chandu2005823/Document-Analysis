from frontend.relationship_graph import (
    EMPTY_GRAPH_MESSAGE,
    build_relationship_graph,
    filter_relationships,
    resolve_relationship_pages,
)


SAMPLE_RELATIONSHIPS = [
    {
        "source": "PPort",
        "relationship": "provides",
        "target": "Service Instance",
        "page": 260,
    },
    {
        "source": "RPort",
        "relationship": "consumes",
        "target": "Service Instance",
        "page": 260,
    },
]


def test_graph_creates_only_observed_unique_nodes_and_relationship_edges():
    graph = build_relationship_graph(SAMPLE_RELATIONSHIPS)

    assert {node["id"] for node in graph.nodes} == {
        "PPort", "RPort", "Service Instance"
    }
    assert len(graph.nodes) == 3
    assert len(graph.edges) == 2
    assert {(edge["from"], edge["label"], edge["to"]) for edge in graph.edges} == {
        ("PPort", "provides", "Service Instance"),
        ("RPort", "consumes", "Service Instance"),
    }


def test_edges_preserve_page_metadata_and_relationship_labels():
    graph = build_relationship_graph(SAMPLE_RELATIONSHIPS)

    assert all(edge["page"] == 260 for edge in graph.edges)
    assert all("Page: 260" in edge["title"] for edge in graph.edges)
    assert {edge["relationship"] for edge in graph.edges} == {"provides", "consumes"}


def test_search_filters_by_source_target_or_relationship():
    assert filter_relationships(SAMPLE_RELATIONSHIPS, "pport") == [SAMPLE_RELATIONSHIPS[0]]
    assert filter_relationships(SAMPLE_RELATIONSHIPS, "SERVICE INSTANCE") == SAMPLE_RELATIONSHIPS
    assert filter_relationships(SAMPLE_RELATIONSHIPS, "consumes") == [SAMPLE_RELATIONSHIPS[1]]
    assert filter_relationships(SAMPLE_RELATIONSHIPS, "missing") == []


def test_relationship_pages_resolve_from_full_source_evidence():
    relationships = [
        {**SAMPLE_RELATIONSHIPS[0], "page": 26},
        {**SAMPLE_RELATIONSHIPS[1], "page": 26},
    ]
    pages = [
        {"page_number": 26, "text": "PPort provides services as described below."},
        {
            "page_number": 260,
            "text": "PPort provides Service Instance. RPort consumes Service Instance.",
        },
    ]

    resolved = resolve_relationship_pages(relationships, pages)

    assert [item["page"] for item in resolved] == [260, 260]


def test_duplicate_entities_share_a_single_node():
    records = SAMPLE_RELATIONSHIPS + [SAMPLE_RELATIONSHIPS[0].copy()]

    graph = build_relationship_graph(records)

    assert len(graph.nodes) == 3
    assert len(graph.edges) == 3


def test_empty_relationship_data_does_not_create_graph_nodes():
    graph = build_relationship_graph([])

    assert graph.nodes == []
    assert graph.edges == []
    assert EMPTY_GRAPH_MESSAGE == "No architecture relationships are available for this project."