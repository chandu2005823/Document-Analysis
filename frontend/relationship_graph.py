import html


EMPTY_GRAPH_MESSAGE = "No architecture relationships are available for this project."


def _normalize_relationship(record):
    if not isinstance(record, dict):
        return None
    source = str(record.get("source") or "").strip()
    relationship = str(record.get("relationship") or "").strip()
    target = str(record.get("target") or "").strip()
    if not source or not relationship or not target:
        return None
    return {
        **record,
        "source": source,
        "relationship": relationship,
        "target": target,
        "page": record.get("page", record.get("page_number")),
    }


def filter_relationships(relationships, query=""):
    normalized = [
        item for item in (_normalize_relationship(record) for record in relationships)
        if item is not None
    ]
    query = str(query or "").strip().casefold()
    if not query:
        return normalized
    return [
        item
        for item in normalized
        if any(
            query in item[field].casefold()
            for field in ("source", "relationship", "target")
        )
    ]


def resolve_relationship_pages(relationships, pages):
    resolved = []
    for relationship in relationships:
        normalized = _normalize_relationship(relationship)
        if normalized is None:
            continue

        terms = tuple(
            normalized[field].casefold()
            for field in ("source", "relationship", "target")
        )
        evidence_pages = [
            page.get("page_number", page.get("page"))
            for page in pages
            if all(term in str(page.get("text") or "").casefold() for term in terms)
        ]
        stored_page = normalized["page"]
        if evidence_pages and not any(
            str(page) == str(stored_page) for page in evidence_pages
        ):
            normalized["page"] = evidence_pages[0]
        resolved.append(normalized)
    return resolved


def build_relationship_graph(relationships):
    from pyvis.network import Network

    records = filter_relationships(relationships)
    graph = Network(
        height="500px",
        width="100%",
        directed=True,
        notebook=False,
        bgcolor="#ffffff",
        font_color="#17212b",
        cdn_resources="in_line",
    )
    graph.set_options(
        """
        {
          "nodes": {"shape": "dot", "size": 20, "font": {"size": 16}},
          "edges": {"font": {"size": 13, "align": "middle"}, "smooth": {"type": "dynamic"}},
          "interaction": {"hover": true, "navigationButtons": true, "keyboard": true},
          "physics": {"enabled": true, "stabilization": {"iterations": 120}}
        }
        """
    )

    nodes = set()
    for record in records:
        for entity in (record["source"], record["target"]):
            if entity not in nodes:
                nodes.add(entity)
                graph.add_node(
                    entity,
                    label=entity,
                    title=f"Entity: {html.escape(entity)}",
                    color={"background": "#d9eef0", "border": "#0b7285"},
                    borderWidth=2,
                )

    for edge_number, record in enumerate(records):
        page = record["page"]
        page_label = str(page) if page is not None else "Not recorded"
        edge_title = (
            f"{html.escape(record['source'])} → "
            f"{html.escape(record['relationship'])} → "
            f"{html.escape(record['target'])}<br>Page: {html.escape(page_label)}"
        )
        graph.add_edge(
            record["source"],
            record["target"],
            id=edge_number,
            label=record["relationship"],
            title=edge_title,
            arrows="to",
        )
        graph.edges[-1]["relationship"] = record["relationship"]
        graph.edges[-1]["page"] = page
        graph.edges[-1]["document_id"] = record.get("document_id")
        graph.edges[-1]["project_id"] = record.get("project_id")

    return graph


def render_relationship_graph(
    relationships,
    *,
    project_name=None,
    document_name=None,
    key_prefix="relationship_graph",
    query=None,
    show_search=True,
    show_inspector=True,
):
    import streamlit as st
    import streamlit.components.v1 as components

    if not relationships:
        st.info(EMPTY_GRAPH_MESSAGE)
        return False

    st.caption(
        f"Project: {project_name or 'Current project'}"
        + (f" · Document: {document_name}" if document_name else "")
        + f" · Relationships: {len(relationships)}"
    )
    if show_search:
        query = st.text_input(
            "Search graph nodes or relationships",
            placeholder="Example: PPort, Service Instance, provides",
            key=f"{key_prefix}_search",
        )
    filtered = filter_relationships(relationships, query)
    if not filtered:
        st.info("No relationships match this search.")
        return None

    try:
        graph = build_relationship_graph(filtered)
        components.html(graph.generate_html(), height=520, scrolling=False)
    except Exception as error:
        st.warning(
            "Interactive graph rendering is unavailable. Use the text relationship explorer below. "
            f"({error})"
        )
        return None

    selection_key = f"{key_prefix}_selected_edge"
    signature_key = f"{key_prefix}_selection_signature"
    filtered_signature = tuple(
        (
            record["source"],
            record["relationship"],
            record["target"],
            record["page"],
            record.get("document_id"),
            record.get("project_id"),
        )
        for record in filtered
    )
    if st.session_state.get(signature_key) != filtered_signature:
        st.session_state[signature_key] = filtered_signature
        st.session_state[selection_key] = 0
    elif not 0 <= st.session_state.get(selection_key, 0) < len(filtered):
        st.session_state[selection_key] = 0

    selected_index = st.selectbox(
        "Inspect relationship",
        options=list(range(len(filtered))),
        format_func=lambda index: (
            f"{filtered[index]['source']} → {filtered[index]['relationship']} → "
            f"{filtered[index]['target']} · Page {filtered[index]['page'] or 'Unknown'}"
        ),
        key=selection_key,
    )
    selected = filtered[selected_index]
    if show_inspector:
        st.markdown(
            f"**Source:** {selected['source']}  \n"
            f"**Relationship:** {selected['relationship']}  \n"
            f"**Target:** {selected['target']}  \n"
            f"**Page:** {selected['page'] if selected['page'] is not None else 'Not recorded'}"
        )
    return selected