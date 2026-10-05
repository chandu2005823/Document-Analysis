import streamlit as st
import sys
from pathlib import Path
import json
import re
from html import escape
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

for folder in [PROJECT_ROOT, PROJECT_ROOT / "rag", PROJECT_ROOT / "ingestion", PROJECT_ROOT / "extraction", PROJECT_ROOT / "analysis", PROJECT_ROOT / "database"]:
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from backend.export_utils import export_csv_bytes, export_json_bytes
from frontend.shell import apply_dark_theme, display_project_name, render_nav_rail, render_topbar, render_status_strip, render_dashboard_hero


def load_traceability_from_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_pages_from_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_entity_context(pages, entity, page_number, context_chars=250):
    for page in pages:
        if page["page_number"] != page_number:
            continue

        text = page["text"]
        match = re.search(re.escape(entity), text, re.IGNORECASE)

        if not match:
            return text[:500].strip()

        start = max(0, match.start() - context_chars)
        end = min(len(text), match.end() + context_chars)

        snippet = text[start:end].strip()
        return snippet

    return ""


def traceability_entity_name(record):
    for key in ("entity_name", "name", "entity"):
        value = str(record.get(key) or "").strip()
        if value:
            return value
    return ""


def select_workspace_document(project_documents, project_id, current_document_id=None):
    if not project_documents:
        return None

    documents_by_id = {
        document["document_id"]: document
        for document in project_documents
    }
    widget_key = f"workspace_document_selection_{project_id}"
    if st.session_state.get(widget_key) not in documents_by_id:
        st.session_state[widget_key] = (
            current_document_id
            if current_document_id in documents_by_id
            else project_documents[0]["document_id"]
        )

    selected_document_id = st.selectbox(
        "Document",
        options=list(documents_by_id),
        format_func=lambda document_id: (
            f"{documents_by_id[document_id]['filename']} · "
            f"v{documents_by_id[document_id]['version']}"
        ),
        key=widget_key,
    )
    previous_key = f"workspace_previous_document_{project_id}"
    previous_document_id = st.session_state.get(previous_key, current_document_id)
    if (
        previous_document_id is not None
        and str(previous_document_id) != str(selected_document_id)
    ):
        clear_document_explorer_state(project_id)
    st.session_state[previous_key] = selected_document_id
    return documents_by_id[selected_document_id]


def clear_document_explorer_state(project_id=None):
    project_prefix = f"{project_id}_" if project_id is not None else None
    state_prefixes = (
        "traceability_search_",
        "traceability_filter_",
        "traceability_submitted_query_",
        "architecture_search_",
        "architecture_entity_type_",
        "architecture_relationship_type_",
        "architecture_applied_search_",
        "architecture_applied_entity_type_",
        "architecture_applied_relationship_type_",
        "architecture_graph_",
        "architecture_selected_node_",
    )
    for key in list(st.session_state.keys()):
        is_selection_state = key in {
            "traceability_selected_entity",
            "traceability_selection_scope",
            "architecture_search",
            "architecture_entity_type",
            "architecture_relationship_type",
        }
        matches_project_scope = any(
            key.startswith(prefix + project_prefix)
            for prefix in state_prefixes
        ) if project_prefix is not None else any(
            key.startswith(prefix) for prefix in state_prefixes
        )
        if key.startswith("architecture_selected_node_"):
            matches_project_scope = True
        if is_selection_state or matches_project_scope:
            st.session_state.pop(key, None)


from frontend.document_processor import EMPTY_UPLOAD_MESSAGE, process_uploaded_pdf
from rag.rag_pipeline import retrieve_context
from rag.groq_client import generate_answer
from rag.citation import format_sources
from rag.grounding_guard import check_grounding
from analysis.document_comparison import compare_entities
from database.audit_log import log_event, read_logs
from database.review_store import save_review, list_reviews
from database.versioning import list_document_versions
from database.access_control import (
    AuthorizationError,
    add_project_member,
    authenticate_user,
    can_compare,
    can_export,
    can_review,
    can_upload,
    create_project,
    create_user,
    get_project_document,
    list_users,
    list_project_documents,
    list_user_projects,
    require_login,
    require_project_access,
    update_user,
)
from frontend.relationship_graph import (
    filter_relationships,
    render_relationship_graph,
    resolve_relationship_pages,
)


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="AutoArch-AI",
    page_icon="🏗️",
    layout="wide"
)

apply_dark_theme()


# ---------------------------------------------------------
# Authentication and project scope
# ---------------------------------------------------------

for key, default in {
    "current_user": None,
    "current_user_id": None,
    "current_project_id": None,
    "current_project_name": None,
    "current_role": None,
    "document_ready": False,
    "document_info": None,
    "last_answer": None,
    "comparison_result": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

if st.session_state.current_user_id is not None:
    try:
        st.session_state.current_user = require_login(st.session_state.current_user_id)
    except AuthorizationError:
        for key in (
            "current_user", "current_user_id", "current_project_id",
            "current_project_name", "current_role", "document_info",
            "document_ready", "last_answer", "comparison_result",
        ):
            st.session_state[key] = None if key != "document_ready" else False

if "active_page" not in st.session_state:
    st.session_state.active_page = "Dashboard"
elif st.session_state.active_page in {"Relationships", "Architecture Graph"}:
    st.session_state.active_page = "Architecture"

if st.session_state.current_user_id is None:
    st.markdown(
        """
        <style>
        .st-key-login_page { min-height: calc(100vh - 1rem); display:flex; align-items:center; }
        .st-key-login_page > div { width:100%; }
        .st-key-login_page > div > div[data-testid="stHorizontalBlock"] {
            display:grid !important;
            grid-template-columns:minmax(0, 1.12fr) minmax(360px, 0.88fr);
            align-items:center;
            gap:clamp(2rem, 6vw, 6rem);
            width:min(1240px, 100%);
            margin:0 auto;
        }
        .st-key-login_page > div > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            width:auto !important; min-width:0; padding:0 !important;
        }
        .st-key-login_visual { padding:clamp(0.5rem, 2vw, 1.5rem); }
        .login-brand { display:flex;align-items:center;gap:0.75rem;margin-bottom:2.2rem; }
        .login-brand-mark {
            display:grid;place-items:center;width:2.45rem;height:2.45rem;flex:0 0 2.45rem;
            border-radius:0.7rem;background:linear-gradient(135deg,#3B82F6,#8B5CF6);
            color:#fff;font-weight:900;box-shadow:0 0 24px rgba(59,130,246,.22);
        }
        .login-brand-name { color:#F8FAFC;font-size:1rem;font-weight:800; }
        .login-brand-caption { color:#94A3B8;font-size:0.65rem;letter-spacing:.12em;text-transform:uppercase; }
        .login-eyebrow { color:#22D3EE;font-size:0.68rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase; }
        .login-headline { margin:.55rem 0 .9rem;color:#F8FAFC;font-size:clamp(2rem,4vw,3.3rem);line-height:1.05;font-weight:800; }
        .login-description { max-width:34rem;margin:0 0 1.35rem;color:#94A3B8;font-size:0.95rem;line-height:1.7; }
        .st-key-login_visual [data-testid="stImage"] { overflow:hidden;border:1px solid rgba(56,189,248,.22);border-radius:.8rem;box-shadow:0 18px 50px rgba(2,6,23,.32);line-height:0; }
        .st-key-login_visual [data-testid="stImage"] img { display:block;width:100%;height:auto;object-fit:contain;border-radius:.8rem; }
        .st-key-login_panel {
            padding:clamp(1.35rem, 3vw, 2.25rem);
            background:linear-gradient(155deg,rgba(16,24,39,.98),rgba(11,16,32,.97));
            border:1px solid #243148;border-radius:.9rem;
            box-shadow:0 24px 70px rgba(0,0,0,.28),0 0 35px rgba(59,130,246,.07);
        }
        .login-secure-label { color:#22D3EE;font-size:.63rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase; }
        .login-panel-heading { margin:.55rem 0 .25rem;color:#F8FAFC;font-size:1.45rem;font-weight:800; }
        .login-panel-subtitle { margin:0 0 1.35rem;color:#94A3B8;font-size:.82rem; }
        .st-key-login_panel [data-testid="stWidgetLabel"] p { color:#CBD5E1;font-size:.76rem;font-weight:650; }
        .st-key-login_panel [data-testid="stTextInput"] input { min-height:2.75rem;background:#0B1020;border-color:#243148; }
        .st-key-login_panel [data-testid="stFormSubmitButton"] button { width:100%;min-height:2.8rem;margin-top:.45rem; }
        .login-divider { display:flex;align-items:center;gap:.75rem;margin:1.1rem 0;color:#64748B;font-size:.64rem;letter-spacing:.1em; }
        .login-divider::before,.login-divider::after { content:"";height:1px;flex:1;background:#243148; }
        .login-request-row { display:flex;align-items:center;justify-content:space-between;gap:.75rem;flex-wrap:wrap; }
        .login-request-copy { color:#94A3B8;font-size:.75rem; }
        .st-key-login_request_access button { min-height:2.25rem;padding:.45rem .7rem;border:1px solid #334155;background:#101827;color:#E2E8F0; }
        .st-key-login_request_access button:hover { border-color:#3B82F6;color:#F8FAFC; }
        @media (max-width:850px) {
            .st-key-login_page { min-height:0;padding:1rem 0; }
            .st-key-login_page > div > div[data-testid="stHorizontalBlock"] { grid-template-columns:minmax(0,1fr);gap:1rem; }
            .st-key-login_visual { padding:.25rem; }
            .login-brand { margin-bottom:1.25rem; }
            .login-headline { font-size:2.1rem; }
            .st-key-login_visual [data-testid="stImage"] img { max-height:220px;object-fit:contain; }
            .st-key-login_panel { padding:1.25rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="login_page"):
        visual_col, form_col = st.columns([1.12, 0.88], gap="large")
        with visual_col:
            with st.container(key="login_visual"):
                st.markdown(
                    "<div class='login-brand'><span class='login-brand-mark'>A</span><div><div class='login-brand-name'>AutoArch-AI</div><div class='login-brand-caption'>Architecture Intelligence</div></div></div>"
                    "<div class='login-eyebrow'>Automotive AI Architecture Access</div>"
                    "<h1 class='login-headline'>Engineering<br>Architecture Intelligence</h1>"
                    "<p class='login-description'>Analyze architecture documents.<br>Trace decisions.<br>Explore connected systems.</p>",
                    unsafe_allow_html=True,
                )
                st.image(
                    str(Path(__file__).resolve().parent / "assets" / "image.png"),
                    width="stretch",
                )

        with form_col:
            with st.container(key="login_panel"):
                st.markdown(
                    "<div class='login-secure-label'>Secure workspace</div>"
                    "<h2 class='login-panel-heading'>Welcome back</h2>"
                    "<p class='login-panel-subtitle'>Access your architecture workspace.</p>",
                    unsafe_allow_html=True,
                )
                with st.form("login_form", clear_on_submit=True):
                    login_username = st.text_input("Username", key="login_username")
                    login_password = st.text_input(
                        "Password", type="password", key="login_password"
                    )
                    login_submitted = st.form_submit_button("Sign In", type="primary")
                if login_submitted:
                    with st.spinner("Signing in..."):
                        authenticated_user = authenticate_user(login_username, login_password)
                    if authenticated_user:
                        st.session_state.current_user = authenticated_user
                        st.session_state.current_user_id = authenticated_user["id"]
                        projects = list_user_projects(authenticated_user["id"])
                        if projects:
                            st.session_state.current_project_id = projects[0]["id"]
                        log_event(
                            "LOGIN", username=authenticated_user["username"], status="success",
                            user_id=authenticated_user["id"],
                            project_id=projects[0]["id"] if projects else None,
                        )
                        st.rerun()
                    else:
                        log_event("LOGIN", username=login_username, status="denied", details={"reason": "invalid_credentials"})
                        st.error("Authentication failed. Check your username and password.")
                st.markdown("<div class='login-divider'>OR</div>", unsafe_allow_html=True)
                request_col, button_col = st.columns([1.2, 0.8], vertical_alignment="center")
                with request_col:
                    st.markdown("<div class='login-request-copy'>New to AutoArch-AI?</div>", unsafe_allow_html=True)
                with button_col:
                    if st.button("Request Access", key="login_request_access", type="tertiary", use_container_width=True):
                        st.info("Account creation is managed by an administrator. Please contact your administrator to request access.")
    st.stop()

current_user = st.session_state.current_user
projects = list_user_projects(current_user["id"])
project_by_id = {project["id"]: project for project in projects}

if not projects:
    st.warning("Your account is not a member of any project.")
    if st.button("Log out", key="logout_no_projects"):
        log_event("LOGOUT", user_id=current_user["id"], username=current_user["username"])
        st.session_state.current_user = None
        st.session_state.current_user_id = None
        st.rerun()
    st.stop()

project_ids = [project["id"] for project in projects]
if st.session_state.current_project_id not in project_ids:
    st.session_state.current_project_id = project_ids[0]
if st.session_state.get("project_selector") not in project_ids:
    st.session_state.project_selector = st.session_state.current_project_id


def switch_project():
    selected_id = st.session_state.project_selector
    if selected_id != st.session_state.current_project_id:
        st.session_state.current_project_id = selected_id
        st.session_state.document_info = None
        st.session_state.document_ready = False
        st.session_state.last_answer = None
        st.session_state.comparison_result = None
        st.session_state.current_project_name = None
        clear_document_explorer_state()
        for key in list(st.session_state.keys()):
            if key.startswith(("workspace_document_selection_", "workspace_previous_document_")):
                st.session_state.pop(key, None)
        for widget_key in ("project_question",):
            if widget_key in st.session_state:
                st.session_state[widget_key] = None

selected_project_id = st.session_state.get("project_selector", st.session_state.current_project_id)
project = require_project_access(current_user["id"], selected_project_id)
explorer_project_key = "explorer_active_project_id"
if st.session_state.get(explorer_project_key) != project["id"]:
    clear_document_explorer_state()
    for key in list(st.session_state.keys()):
        if key.startswith(("workspace_document_selection_", "workspace_previous_document_")):
            st.session_state.pop(key, None)
    st.session_state[explorer_project_key] = project["id"]
st.session_state.current_project_id = project["id"]
st.session_state.current_project_name = project["name"]
st.session_state.current_role = project["role"]

project_documents = list_project_documents(current_user["id"], project["id"])
if project_documents:
    latest_document = project_documents[0]
    if (
        not st.session_state.document_info
        or st.session_state.document_info.get("project_id") != project["id"]
        or st.session_state.document_info.get("document_id") != latest_document["document_id"]
    ):
        latest_document = get_project_document(
            current_user["id"], project["id"], latest_document["document_id"]
        )
        artifact_dir = Path(latest_document["artifact_dir"])
        with (artifact_dir / "chunks.json").open("r", encoding="utf-8") as file:
            chunk_data = json.load(file)
        st.session_state.document_info = {
            "filename": latest_document["filename"],
            "document_id": latest_document["document_id"],
            "project_id": project["id"],
            "version": latest_document["version"],
            "pages": latest_document["page_count"],
            "chunks": latest_document["chunk_count"],
            "traceability_records": latest_document["traceability_count"],
            "relationship_records": 0,
            "collection_name": latest_document["collection_name"],
            "artifact_dir": str(artifact_dir),
            "traceability_path": str(artifact_dir / "traceability.json"),
            "pages_path": str(artifact_dir / "pages.json"),
            "relationship_path": str(artifact_dir / "relationships.json"),
            "chunk_data": chunk_data,
        }
        if Path(st.session_state.document_info["relationship_path"]).exists():
            with open(st.session_state.document_info["relationship_path"], "r", encoding="utf-8") as file:
                st.session_state.document_info["relationship_records"] = len(json.load(file))
        st.session_state.document_ready = True
else:
    st.session_state.document_info = None
    st.session_state.document_ready = False

def logout_session():
    log_event(
        "LOGOUT", user_id=current_user["id"], username=current_user["username"],
        project_id=project["id"],
    )
    for key in (
        "current_user", "current_user_id", "current_project_id",
        "current_project_name", "current_role", "document_info",
        "document_ready", "last_answer", "comparison_result",
    ):
        st.session_state[key] = None if key != "document_ready" else False
    st.rerun()

render_topbar(
    current_user["username"],
    project["name"] if project else "Workspace",
    st.session_state.active_page,
    [(project_meta["name"], project_meta["id"]) for project_meta in projects],
    on_logout=logout_session,
)

if st.session_state.active_page == "Dashboard":
    render_dashboard_hero()
    with st.container(key="dashboard_overview"):
        st.markdown('<div class="subsection-head"><h3>Architecture Overview</h3><p>Current project status</p></div>', unsafe_allow_html=True)
        render_status_strip(st.session_state.document_info if st.session_state.document_ready else None)

    st.markdown('<div class="subsection-head"><h3>Recent documents</h3><p>Live project library</p></div>', unsafe_allow_html=True)
    if project_documents:
        docs = project_documents[:4]
        cols = st.columns(min(len(docs), 4))
        for idx, doc in enumerate(docs):
            with cols[idx]:
                st.markdown(f"<div style='background: linear-gradient(180deg, rgba(17,24,39,0.9), rgba(9,14,24,0.7)); border: 1px solid #243148; border-radius: 1rem; padding: 1rem; min-height: 170px;'><div style='display:flex;align-items:center;justify-content:space-between;'><div style='width:2.2rem;height:2.2rem;border-radius:0.8rem;background:linear-gradient(135deg, rgba(59,130,246,0.15), rgba(139,92,246,0.15));color:#3B82F6;display:inline-flex;align-items:center;justify-content:center;font-weight:800;'>DOC</div><span style='background: rgba(59,130,246,0.12); color:#F8FAFC; border:1px solid rgba(59,130,246,0.25); border-radius:999px; padding:0.32rem 0.6rem; font-size:0.7rem; font-weight:700; text-transform:uppercase;'>{doc.get('status', 'processed')}</span></div><div style='margin-top:0.9rem;font-weight:700;color:#F8FAFC;'>{doc.get('filename', 'Document')}</div><div style='margin-top:0.5rem;color:#94A3B8;font-size:0.76rem;line-height:1.6;'>Version {doc.get('version', 'n/a')} · {doc.get('page_count', 0)} pages</div><div style='color:#94A3B8;font-size:0.76rem;'>Updated {doc.get('updated_at', doc.get('upload_timestamp', ''))}</div></div>", unsafe_allow_html=True)
    else:
        st.info("No documents available in the current project.")

    st.markdown('<div class="subsection-head"><h3>Architecture status</h3><p>Recent activity</p></div>', unsafe_allow_html=True)
    st.write("Document cadence, entity extraction, and current project health are shown here using the live backend data.")

    st.markdown('<div class="subsection-head"><h3>Recent Q&A</h3><p>Latest grounded answers</p></div>', unsafe_allow_html=True)
    if st.session_state.last_answer:
        st.info(st.session_state.last_answer["answer"])
        st.caption(f"Question: {st.session_state.last_answer['question']}")
    else:
        st.info("No recent grounded Q&A yet for this project.")
elif st.session_state.active_page == "Documents":
    st.markdown('<div class="subsection-head"><h3>Document Intelligence</h3><p>Upload and review project documents</p></div>', unsafe_allow_html=True)
    processing_success = st.session_state.pop("document_processing_success", None)
    if processing_success:
        success_filename = escape(str(processing_success.get("filename") or "Document"))
        st.markdown(
            f"<div style='margin:0 0 1rem;padding:0.9rem 1rem;background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.3);border-left:3px solid #22C55E;border-radius:.55rem;'>"
            f"<div style='color:#86EFAC;font-size:.95rem;font-weight:750;'>Document processed successfully</div>"
            f"<div style='margin-top:.55rem;color:#F8FAFC;font-size:.8rem;'>Document: {success_filename}</div>"
            f"<div style='margin-top:.25rem;color:#CBD5E1;font-size:.76rem;'>"
            f"Pages processed: {processing_success.get('pages', 0)} &nbsp;·&nbsp; "
            f"Chunks created: {processing_success.get('chunks', 0)} &nbsp;·&nbsp; "
            f"Architecture entities: {processing_success.get('traceability_records', 0)} &nbsp;·&nbsp; "
            f"Relationships: {processing_success.get('relationship_records', 0)}</div>"
            "<div style='margin-top:.45rem;color:#94A3B8;font-size:.74rem;'>"
            "The document is now ready for Q&amp;A, Traceability and Architecture analysis.</div></div>",
            unsafe_allow_html=True,
        )
    if can_upload(current_user["id"], project["id"]):
        uploaded_file = st.file_uploader("Choose an AUTOSAR PDF", type=["pdf"], key=f"project_document_uploader_{project['id']}")
    else:
        uploaded_file = None
        st.info("Your project role allows viewing and querying, but not uploading documents.")
    if uploaded_file is not None:
        if st.button("Process Document", type="primary"):
            with st.spinner("Processing AUTOSAR document..."):
                try:
                    document_info = process_uploaded_pdf(uploaded_file, user_id=current_user["id"], project_id=project["id"])
                    st.session_state.document_ready = True
                    st.session_state.document_info = document_info
                    st.session_state.document_processing_success = {
                        "filename": document_info.get("filename"),
                        "pages": document_info.get("pages", 0),
                        "chunks": document_info.get("chunks", 0),
                        "traceability_records": document_info.get("traceability_records", 0),
                        "relationship_records": document_info.get("relationship_records", 0),
                    }
                    log_event("DOCUMENT_UPLOADED", document_name=uploaded_file.name, status="success", details={"version": document_info.get("version"), "pages": document_info.get("pages")}, user_id=current_user["id"], username=current_user["username"], project_id=project["id"], document_id=document_info.get("document_id"))
                    st.rerun()
                except Exception as e:
                    st.session_state.document_ready = False
                    log_event("DOCUMENT_UPLOAD", document_name=getattr(uploaded_file, "name", "unknown"), status="error", details={"error": str(e)}, user_id=current_user["id"], username=current_user["username"], project_id=project["id"])
                    if str(e) == EMPTY_UPLOAD_MESSAGE:
                        st.error(EMPTY_UPLOAD_MESSAGE)
                    else:
                        st.error(f"Document processing failed: {e}")
    st.markdown('<div class="subsection-head"><h3>Document library</h3><p>All current project documents</p></div>', unsafe_allow_html=True)
    if project_documents:
        cols = st.columns(min(len(project_documents), 4))
        for idx, doc in enumerate(project_documents[:4]):
            with cols[idx % len(cols)]:
                st.markdown(f"<div style='background: linear-gradient(180deg, rgba(17,24,39,0.9), rgba(9,14,24,0.7)); border: 1px solid #243148; border-radius: 1rem; padding: 1rem; min-height: 150px;'><div style='display:flex; align-items:center; justify-content:space-between;'><span style='width:2rem;height:2rem;border-radius:0.7rem;background:linear-gradient(135deg, rgba(59,130,246,0.14), rgba(139,92,246,0.14));display:inline-flex;align-items:center;justify-content:center;color:#3B82F6;font-weight:800;'>PDF</span><span style='padding:0.28rem 0.55rem;border-radius:999px;border:1px solid rgba(59,130,246,0.2); background:rgba(59,130,246,0.08); color:#F8FAFC; font-size:0.68rem; letter-spacing:0.08em; text-transform:uppercase;'>{doc.get('status', 'processed')}</span></div><div style='margin-top:0.9rem;font-weight:700;color:#F8FAFC;'>{doc.get('filename', 'Document')}</div><div style='margin-top:0.4rem;color:#94A3B8;font-size:0.74rem;'>Version {doc.get('version', 'n/a')} · {doc.get('page_count', 0)} pages</div></div>", unsafe_allow_html=True)
    else:
        st.info("No documents yet.")

elif st.session_state.active_page == "Grounded Q&A":
    st.markdown('<div class="subsection-head"><h3>AI Investigation Workspace</h3><p>Grounded engineering questions</p></div>', unsafe_allow_html=True)
    left_col, center_col, right_col = st.columns([1.0, 2.0, 1.2])
    with left_col:
        st.markdown("### Chat history")
        st.button("+ New Investigation", key="new_qna")
        st.write("Previous questions and prior grounded answers remain available in the existing backend session data.")
    with center_col:
        question = st.text_area("Question", placeholder="Ask about the uploaded architecture document...", key="project_question_page", height=120)
        if st.button("Ask AutoArch-AI"):
            if not st.session_state.document_ready:
                st.warning("Please upload and process a PDF first.")
            elif not question.strip():
                st.warning("Please enter a question.")
            else:
                with st.spinner("Searching and generating an answer..."):
                    try:
                        results = retrieve_context(question, top_k=5, user_id=current_user["id"], project_id=project["id"])
                        documents = results["documents"][0]
                        metadatas = results["metadatas"][0]
                        context_parts = []
                        for i, (document, metadata) in enumerate(zip(documents, metadatas), start=1):
                            context_parts.append(f"SOURCE {i}\nPage: {metadata['page_number']}\nChunk ID: {metadata['chunk_id']}\nCONTENT:\n{document}")
                        context = "\n".join(context_parts)
                        relationships = results.get("relationships", [])
                        if relationships:
                            context += "\n\nARCHITECTURE RELATIONSHIPS:\n" + "\n".join(f"{r['source']} {r['relationship']} {r['target']} (Page {r['page']})" for r in relationships)
                        prompt = f"You are an engineering document analysis assistant. Use only the document context.\n\nDOCUMENT CONTEXT:\n{context}\n\nUSER QUESTION:\n{question}"
                        answer = generate_answer(prompt)
                        if not answer or not answer.strip():
                            answer = "I could not find enough information in the document."
                        confidence = results["confidence"]
                        st.session_state.last_answer = {"question": question, "answer": answer, "confidence": confidence, "sources": format_sources(results), "timestamp": None}
                        grounding = check_grounding(answer, context)
                        st.success(answer)
                        st.metric("Confidence", f"{confidence['level']} — {confidence['score']:.4f}")
                        if grounding.get("supported"):
                            st.success(f"Grounding supported — {grounding['score']:.4f}")
                        else:
                            st.warning(f"Grounding weak — {grounding['score']:.4f}")
                    except Exception as e:
                        st.error(f"Question processing failed: {e}")
    with right_col:
        st.markdown("### Source evidence")
        if st.session_state.last_answer:
            sources = st.session_state.last_answer["sources"]
            if sources:
                for source in sources[:3]:
                    st.markdown(f"<div style='background: rgba(17,24,39,0.85); border: 1px solid #243148; border-left: 4px solid #3B82F6; border-radius: 0.8rem; padding: 0.8rem; margin-bottom: 0.7rem;'><div style='color:#94A3B8;font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;'>Page {source.get('page')} · Chunk {source.get('chunk_id')}</div><div style='color:#F8FAFC;font-weight:700;margin-top:0.3rem;'>{source.get('source_number', '')}</div></div>", unsafe_allow_html=True)
            else:
                st.info("No evidence yet.")
        else:
            st.info("Completed answers will show source evidence here.")
elif st.session_state.active_page == "Traceability":
    current_document_info = st.session_state.document_info or {}
    selected_document = select_workspace_document(
        project_documents,
        project["id"],
        current_document_info.get("document_id"),
    )
    document_info = {}
    if selected_document:
        artifact_dir = Path(selected_document["artifact_dir"])
        document_info = {
            "filename": selected_document["filename"],
            "document_id": selected_document["document_id"],
            "project_id": project["id"],
            "user_id": current_user["id"],
            "version": selected_document["version"],
            "traceability_path": str(artifact_dir / "traceability.json"),
            "pages_path": str(artifact_dir / "pages.json"),
            "relationship_path": str(artifact_dir / "relationships.json"),
        }
    document_name = escape(str(document_info.get("filename") or "Current project"))
    st.markdown(
        """
        <style>
        .st-key-traceability_page { padding-top: 0.15rem; }
        .traceability-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin: 0 0 0.7rem;
            padding: 0 0 0.7rem;
            border-bottom: 1px solid #243148;
        }
        .traceability-title { min-width: 0; }
        .traceability-kicker, .traceability-label {
            color: #22D3EE;
            font-size: 0.66rem;
            font-weight: 800;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }
        .traceability-title h1 {
            margin: 0.16rem 0 0.12rem;
            color: #F8FAFC;
            font-size: 1.32rem;
            line-height: 1.2;
        }
        .traceability-title p, .traceability-subtitle {
            margin: 0;
            color: #94A3B8;
            font-size: 0.77rem;
        }
        .traceability-document {
            max-width: 32%;
            min-width: 0;
            text-align: right;
        }
        .traceability-document strong {
            display: block;
            margin-top: 0.25rem;
            color: #F8FAFC;
            font-size: 0.78rem;
            overflow-wrap: anywhere;
        }
        .st-key-traceability_controls { margin-bottom: 0.65rem; }
        .st-key-traceability_controls [data-testid="stWidgetLabel"] { display: none; }
        .st-key-traceability_controls [data-testid="stTextInput"] input,
        .st-key-traceability_controls [data-testid="stSelectbox"] > div > div {
            min-height: 2.35rem;
            background: #101827;
            border-color: #243148;
        }
        .st-key-traceability_panels > div[data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns: minmax(0, 5fr) minmax(0, 7fr) minmax(0, 8fr);
            align-items: start;
            gap: 0.75rem;
        }
        .st-key-traceability_panels > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            width: auto !important;
            min-width: 0;
            padding: 0 !important;
        }
        .st-key-traceability_entities,
        .st-key-traceability_inspector,
        .st-key-traceability_evidence {
            min-width: 0;
            padding: 0.75rem;
            background: rgba(16, 24, 39, 0.58);
            border: 1px solid #243148;
            border-radius: 0.55rem;
        }
        .traceability-panel-title {
            margin: 0;
            color: #F8FAFC;
            font-size: 0.76rem;
            font-weight: 800;
            letter-spacing: 0.09em;
            text-transform: uppercase;
        }
        .traceability-panel-note {
            margin: 0.18rem 0 0.65rem;
            color: #94A3B8;
            font-size: 0.7rem;
            line-height: 1.4;
        }
        .st-key-traceability_entities div[class*="st-key-traceability_entity_card"] {
            margin: 0.25rem 0 0.45rem;
            padding: 0.22rem 0.45rem 0.35rem;
            border: 1px solid transparent;
            border-radius: 0.45rem;
            background: #0B1220;
        }
        .st-key-traceability_entities div[class*="st-key-traceability_entity_card_selected"] {
            border-color: rgba(59, 130, 246, 0.72);
            background: #151E2F;
            box-shadow: 0 0 16px rgba(59, 130, 246, 0.12), inset 2px 0 #3B82F6;
        }
        .st-key-traceability_entities div[class*="st-key-traceability_entity_card"] button {
            min-height: 2rem;
            justify-content: flex-start;
            padding: 0.25rem 0.3rem !important;
            border: 0 !important;
            background: transparent !important;
            color: #F8FAFC !important;
            font-size: 0.82rem !important;
            font-weight: 700 !important;
            box-shadow: none !important;
        }
        .st-key-traceability_entities div[class*="st-key-traceability_entity_card"] button p {
            white-space: normal;
            overflow-wrap: anywhere;
        }
        .traceability-entity-meta {
            margin: 0 0.3rem;
            color: #94A3B8;
            font-size: 0.68rem;
            line-height: 1.4;
            overflow-wrap: anywhere;
        }
        .traceability-entity-heading {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            margin: 0.25rem 0 0.65rem;
            padding: 0.6rem 0;
            border-bottom: 1px solid #243148;
        }
        .traceability-entity-icon {
            display: grid;
            width: 2rem;
            height: 2rem;
            flex: 0 0 2rem;
            place-items: center;
            border: 1px solid rgba(59, 130, 246, 0.4);
            border-radius: 0.45rem;
            background: rgba(59, 130, 246, 0.12);
            color: #93C5FD;
        }
        .traceability-entity-heading strong { color: #F8FAFC; font-size: 0.9rem; }
        .traceability-entity-heading span { display: block; color: #94A3B8; font-size: 0.7rem; }
        .traceability-info-block {
            margin: 0.35rem 0 0.7rem;
            padding: 0.55rem 0;
            border-bottom: 1px solid rgba(36, 49, 72, 0.75);
        }
        .traceability-info-block:last-child { border-bottom: 0; }
        .traceability-info-block b {
            display: block;
            margin-bottom: 0.3rem;
            color: #94A3B8;
            font-size: 0.64rem;
            letter-spacing: 0.08em;
        }
        .traceability-page-chip {
            display: inline-block;
            margin: 0.1rem 0.18rem 0.1rem 0;
            padding: 0.2rem 0.42rem;
            border: 1px solid #243148;
            border-radius: 999px;
            background: #101827;
            color: #BAE6FD;
            font-size: 0.67rem;
        }
        .traceability-related-item { margin: 0.2rem 0; color: #CBD5E1; font-size: 0.75rem; }
        .traceability-flow {
            margin: 0.25rem 0 0.65rem;
            color: #3B82F6;
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.05em;
        }
        .st-key-traceability_evidence_list {
            max-height: 66vh;
            overflow-y: auto;
            padding-right: 0.35rem;
            scrollbar-color: #334155 #101827;
            scrollbar-width: thin;
        }
        .traceability-evidence-card {
            margin: 0 0 0.55rem;
            padding: 0.65rem 0.7rem;
            border: 1px solid #243148;
            border-radius: 0.45rem;
            background: #101827;
        }
        .traceability-evidence-page {
            display: inline-block;
            margin-bottom: 0.45rem;
            padding: 0.19rem 0.42rem;
            border: 1px solid rgba(34, 211, 238, 0.3);
            border-radius: 0.25rem;
            background: rgba(34, 211, 238, 0.08);
            color: #67E8F9;
            font-size: 0.65rem;
            font-weight: 800;
            letter-spacing: 0.07em;
        }
        .traceability-evidence-meta { margin: 0.12rem 0; color: #94A3B8; font-size: 0.68rem; }
        .traceability-evidence-text {
            margin: 0.45rem 0;
            color: #E2E8F0;
            font-size: 0.75rem;
            line-height: 1.5;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
        }
        .traceability-evidence-source {
            padding-top: 0.35rem;
            border-top: 1px solid #243148;
            color: #64748B;
            font-size: 0.62rem;
        }
        .st-key-traceability_controls > div[data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns: minmax(0, 3fr) minmax(8rem, 1fr);
            gap: 0.65rem;
        }
        @media (max-width: 1050px) {
            .st-key-traceability_panels > div[data-testid="stHorizontalBlock"] {
                grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr);
            }
            .st-key-traceability_panels > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(1) {
                grid-column: 1;
                grid-row: 1 / span 2;
            }
            .st-key-traceability_panels > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) {
                grid-column: 2;
                grid-row: 1;
            }
            .st-key-traceability_panels > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(3) {
                grid-column: 2;
                grid-row: 2;
            }
        }
        @media (max-width: 680px) {
            .traceability-header { align-items: flex-start; flex-direction: column; }
            .traceability-document { max-width: 100%; text-align: left; }
            .st-key-traceability_controls > div[data-testid="stHorizontalBlock"] {
                display: grid !important;
                grid-template-columns: minmax(0, 1fr) minmax(7rem, 0.7fr);
            }
            .st-key-traceability_panels > div[data-testid="stHorizontalBlock"] {
                grid-template-columns: minmax(0, 1fr);
            }
            .st-key-traceability_panels > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(n) {
                grid-column: 1;
                grid-row: auto;
            }
            .st-key-traceability_evidence_list { max-height: 60vh; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="traceability_page"):
        st.markdown(
            f"<div class='traceability-header'><div class='traceability-title'>"
            f"<div class='traceability-kicker'>Architecture Evidence Workspace</div>"
            f"<h1>Architecture Traceability</h1>"
            f"<p>Trace every architecture entity back to its source evidence.</p></div>"
            f"<div class='traceability-document'><span class='traceability-label'>Active document / project</span>"
            f"<strong>{document_name}</strong></div></div>",
            unsafe_allow_html=True,
        )

        if not document_info.get("traceability_path") or not Path(document_info["traceability_path"]).exists():
            st.info("Please upload and process a document first.")
        else:
            document_id = document_info.get("document_id")
            project_id = document_info.get("project_id", project["id"])
            traceability_scope_key = f"{project_id}_{document_id}"
            submitted_query_key = f"traceability_submitted_query_{traceability_scope_key}"
            if submitted_query_key not in st.session_state:
                st.session_state[submitted_query_key] = ""

            def belongs_to_active_document(item):
                expected_scope = {
                    "user_id": current_user["id"],
                    "project_id": project_id,
                    "document_id": document_id,
                }
                return all(
                    item.get(key) is None
                    or expected is None
                    or str(item.get(key)) == str(expected)
                    for key, expected in expected_scope.items()
                )

            records = [
                {**record, "entity": traceability_entity_name(record)}
                for record in load_traceability_from_file(document_info["traceability_path"])
                if belongs_to_active_document(record)
            ]

            if not records:
                st.info("No architecture entities found for this document.")
            else:
                entity_types = sorted({record["type"] for record in records})
                with st.container(key="traceability_controls"):
                    search_col, filter_col = st.columns([3, 1], gap="small")
                    with search_col:
                        query = st.text_input(
                            "Search entities",
                            placeholder="Search entities...",
                            key=f"traceability_search_{traceability_scope_key}",
                            label_visibility="collapsed",
                        )
                        submitted = st.button(
                            "Submit",
                            key=f"traceability_submit_{traceability_scope_key}",
                            type="primary",
                        )
                    with filter_col:
                        selected_type = st.selectbox(
                            "Filter by entity type",
                            ["All"] + entity_types,
                            key=f"traceability_filter_{traceability_scope_key}",
                            label_visibility="collapsed",
                        )

                if submitted:
                    if query.strip():
                        st.session_state[submitted_query_key] = query.strip()
                    else:
                        st.session_state[submitted_query_key] = None
                    st.session_state.traceability_selected_entity = None

                submitted_query = st.session_state[submitted_query_key]
                if submitted and not query.strip():
                    st.warning("Please enter an entity name.")

                filtered_records = records
                if selected_type != "All":
                    filtered_records = [record for record in filtered_records if record["type"] == selected_type]
                if submitted_query is None:
                    filtered_records = []
                elif submitted_query:
                    filtered_records = [
                        record
                        for record in filtered_records
                        if submitted_query.lower() in record["entity"].lower()
                    ]

                entity_groups = {}
                for record in filtered_records:
                    entity_key = (record["entity"], record["type"])
                    entity_groups.setdefault(entity_key, []).append(record)

                selection_scope = (str(project_id), str(document_id or ""))
                if st.session_state.get("traceability_selection_scope") != selection_scope:
                    st.session_state.traceability_selection_scope = selection_scope
                    st.session_state.traceability_selected_entity = None

                selected_entity_key = st.session_state.get("traceability_selected_entity")
                if selected_entity_key not in entity_groups:
                    selected_entity_key = None
                if selected_entity_key is None and submitted_query and entity_groups:
                    exact_matches = [
                        key
                        for key in entity_groups
                        if key[0].casefold() == submitted_query.casefold()
                    ]
                    selected_entity_key = (
                        exact_matches[0] if exact_matches else next(iter(entity_groups))
                    )
                st.session_state.traceability_selected_entity = selected_entity_key

                selected_records = [
                    record
                    for record in records
                    if selected_entity_key
                    and (record["entity"], record["type"]) == selected_entity_key
                ]
                source_pages = sorted(
                    {record.get("page") for record in selected_records if record.get("page") is not None},
                    key=lambda page: (0, int(page)) if str(page).isdigit() else (1, str(page)),
                )

                with st.container(key="traceability_panels"):
                    left, center, right = st.columns([5, 7, 8], gap="small")
                    with left:
                        with st.container(key="traceability_entities"):
                            st.markdown("<h2 class='traceability-panel-title'>Entities</h2>", unsafe_allow_html=True)
                            st.markdown(
                                "<p class='traceability-panel-note'>Architecture entities found in the document</p>",
                                unsafe_allow_html=True,
                            )
                            if not entity_groups:
                                st.info("No matching entities found")
                            for index, (entity_key, entity_records) in enumerate(list(entity_groups.items())[:10]):
                                entity_name, entity_type = entity_key
                                entity_pages = sorted(
                                    {record.get("page") for record in entity_records if record.get("page") is not None},
                                    key=lambda page: (0, int(page)) if str(page).isdigit() else (1, str(page)),
                                )
                                card_key = (
                                    f"traceability_entity_card_selected_{index}"
                                    if entity_key == selected_entity_key
                                    else f"traceability_entity_card_{index}"
                                )
                                with st.container(key=card_key):
                                    if st.button(
                                        entity_name,
                                        key=f"traceability_entity_{index}",
                                        type="tertiary",
                                        use_container_width=True,
                                    ):
                                        selected_entity_key = entity_key
                                        st.session_state.traceability_selected_entity = entity_key
                                    display_type = entity_type.replace("_", " ").rstrip("s").title()
                                    page_list = " · ".join(str(page) for page in entity_pages)
                                    st.markdown(
                                        f"<div class='traceability-entity-meta'>{escape(display_type)}"
                                        f"<br>Pages {escape(page_list or 'n/a')}</div>",
                                        unsafe_allow_html=True,
                                    )

                    selected_records = [
                        record
                        for record in records
                        if selected_entity_key
                        and (record["entity"], record["type"]) == selected_entity_key
                    ]
                    source_pages = sorted(
                        {record.get("page") for record in selected_records if record.get("page") is not None},
                        key=lambda page: (0, int(page)) if str(page).isdigit() else (1, str(page)),
                    )

                    with center:
                        with st.container(key="traceability_inspector"):
                            st.markdown("<h2 class='traceability-panel-title'>Entity inspector</h2>", unsafe_allow_html=True)
                            st.markdown("<p class='traceability-flow'>ENTITY &nbsp;›&nbsp; TRACEABILITY &nbsp;›&nbsp; EVIDENCE</p>", unsafe_allow_html=True)
                            if selected_entity_key and selected_records:
                                display_type = selected_entity_key[1].replace("_", " ").rstrip("s").title()
                                st.markdown(
                                    f"<div class='traceability-entity-heading'>"
                                    f"<div class='traceability-entity-icon'>◉</div><div>"
                                    f"<strong>{escape(str(selected_entity_key[0]))}</strong>"
                                    f"<span>{escape(display_type)}</span></div></div>",
                                    unsafe_allow_html=True,
                                )
                                overview_tab, pages_tab, relationships_tab = st.tabs(
                                    ["Overview", "Source pages", "Relationships"]
                                )
                                with overview_tab:
                                    st.markdown(
                                        f"<div class='traceability-info-block'><b>TYPE</b>{escape(display_type)}</div>"
                                        f"<div class='traceability-info-block'><b>SOURCE PAGES</b>{len(source_pages)} linked pages</div>",
                                        unsafe_allow_html=True,
                                    )
                                with pages_tab:
                                    page_chips = "".join(
                                        f"<span class='traceability-page-chip'>PAGE {escape(str(page))}</span>"
                                        for page in source_pages
                                    )
                                    st.markdown(
                                        f"<div class='traceability-info-block'><b>SOURCE PAGES</b>{page_chips}</div>",
                                        unsafe_allow_html=True,
                                    )
                                with relationships_tab:
                                    relationship_path = document_info.get("relationship_path")
                                    entity_relationships = []
                                    if relationship_path and Path(relationship_path).exists():
                                        entity_relationships = [
                                            relation
                                            for relation in load_traceability_from_file(relationship_path)
                                            if belongs_to_active_document(relation)
                                            and selected_entity_key[0]
                                            in (relation.get("source"), relation.get("target"))
                                        ]
                                    if entity_relationships:
                                        for relation in entity_relationships:
                                            st.markdown(
                                                f"<div class='traceability-related-item'>"
                                                f"{escape(str(relation.get('source', '')))} → "
                                                f"{escape(str(relation.get('relationship', '')))} → "
                                                f"{escape(str(relation.get('target', '')))}"
                                                f"<br><span class='traceability-entity-meta'>Page {escape(str(relation.get('page', 'n/a')))}</span></div>",
                                                unsafe_allow_html=True,
                                            )
                                    else:
                                        st.caption("No relationships recorded for this entity.")
                            else:
                                st.markdown("<h3>No entity selected</h3>", unsafe_allow_html=True)
                                st.caption("Select an architecture entity to inspect its details.")

                    with right:
                        with st.container(key="traceability_evidence"):
                            st.markdown("<h2 class='traceability-panel-title'>Source evidence</h2>", unsafe_allow_html=True)
                            st.markdown(
                                "<p class='traceability-panel-note'>Evidence linked to the selected entity</p>",
                                unsafe_allow_html=True,
                            )
                            with st.container(key="traceability_evidence_list"):
                                if not selected_entity_key or not selected_records:
                                    st.markdown("<h3>No source evidence</h3>", unsafe_allow_html=True)
                                    st.caption("Select an entity to view its linked source pages.")
                                else:
                                    pages_path = document_info.get("pages_path")
                                    pages = (
                                        load_pages_from_file(pages_path)
                                        if pages_path and Path(pages_path).exists()
                                        else []
                                    )
                                    pages = [page for page in pages if belongs_to_active_document(page)]
                                    safe_document_name = escape(str(document_info.get("filename") or "Document"))
                                    safe_entity_name = escape(str(selected_entity_key[0]))
                                    for source_page in source_pages:
                                        context = get_entity_context(
                                            pages, selected_entity_key[0], source_page
                                        )
                                        source_text = (
                                            escape(context)
                                            if context
                                            else "No stored source text is available for this page."
                                        )
                                        st.markdown(
                                            f"<article class='traceability-evidence-card'>"
                                            f"<div class='traceability-evidence-page'>PAGE {escape(str(source_page))}</div>"
                                            f"<div class='traceability-evidence-meta'>Document: {safe_document_name}</div>"
                                            f"<div class='traceability-evidence-meta'>Entity: {safe_entity_name}</div>"
                                            f"<div class='traceability-evidence-text'>{source_text}</div>"
                                            f"<div class='traceability-evidence-source'>Source / Traceability</div>"
                                            f"</article>",
                                            unsafe_allow_html=True,
                                        )

elif st.session_state.active_page == "Architecture":
    current_document_info = st.session_state.document_info or {}
    selected_document_row = select_workspace_document(
        project_documents,
        project["id"],
        current_document_info.get("document_id"),
    )
    selected_document = None
    if selected_document_row:
        try:
            selected_document = get_project_document(
                current_user["id"],
                project["id"],
                selected_document_row["document_id"],
            )
        except AuthorizationError as error:
            st.error(str(error))

    st.markdown(
        """
        <style>
        .architecture-explorer-header {
            display:flex;align-items:flex-end;justify-content:space-between;gap:1rem;
            margin:0 0 0.8rem;padding:0 0 0.65rem;border-bottom:1px solid #243148;
        }
        .architecture-explorer-header h1 { margin:0;font-size:1.3rem;color:#F8FAFC; }
        .architecture-explorer-header p { margin:0.2rem 0 0;color:#94A3B8;font-size:0.78rem; }
        .architecture-document { color:#CBD5E1;font-size:0.73rem;text-align:right;overflow-wrap:anywhere; }
        .st-key-architecture_controls { margin-bottom:0.55rem; }
        .st-key-architecture_controls > div[data-testid="stHorizontalBlock"] {
            display:grid !important;grid-template-columns:minmax(0,3fr) minmax(8rem,1fr) minmax(9rem,1fr) max-content;
            align-items:center;gap:0.55rem;
        }
        .st-key-architecture_controls > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            width:auto !important;min-width:0;padding:0 !important;
        }
        .st-key-architecture_controls [data-testid="stWidgetLabel"] {
            display:block;color:#94A3B8;font-size:0.65rem;font-weight:700;
        }
        .st-key-architecture_workspace > div[data-testid="stHorizontalBlock"] {
            display:grid !important;grid-template-columns:minmax(0,1.8fr) minmax(18rem,1fr);
            align-items:start;gap:0.8rem;
        }
        .st-key-architecture_workspace > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            width:auto !important;min-width:0;padding:0 !important;
        }
        .architecture-panel,
        .st-key-architecture_graph_panel,
        .st-key-architecture_inspector_panel {
            min-width:0;padding:0.8rem;background:rgba(16,24,39,0.58);
            border:1px solid #243148;border-radius:0.55rem;
        }
        .st-key-architecture_graph_panel h2,
        .st-key-architecture_inspector_panel h2 { margin:0 0 0.5rem;color:#F8FAFC;font-size:0.76rem;font-weight:800;letter-spacing:0.09em;text-transform:uppercase; }
        .architecture-inspector-value { margin:0.15rem 0 0.65rem;color:#F8FAFC;font-size:0.86rem;font-weight:650;overflow-wrap:anywhere; }
        .architecture-inspector-label { margin-top:0.65rem;color:#94A3B8;font-size:0.64rem;font-weight:800;letter-spacing:0.08em;text-transform:uppercase; }
        .architecture-provenance { margin-top:0.65rem;padding-top:0.55rem;border-top:1px solid #243148;color:#CBD5E1;font-size:0.75rem;line-height:1.5;white-space:pre-wrap;overflow-wrap:anywhere; }
        .st-key-architecture_node button { min-height:2rem; }
        @media (max-width:850px) {
            .st-key-architecture_workspace > div[data-testid="stHorizontalBlock"] { grid-template-columns:minmax(0,1fr); }
            .architecture-explorer-header { align-items:flex-start;flex-direction:column; }
            .architecture-document { text-align:left; }
        }
        @media (max-width:680px) {
            .st-key-architecture_controls > div[data-testid="stHorizontalBlock"] { grid-template-columns:minmax(0,1fr) minmax(0,1fr); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='architecture-explorer-header'><div><h1>Architecture Explorer</h1>"
        f"<p>Explore architecture entities, relationships and their source evidence.</p></div>"
        f"<div class='architecture-document'>{escape(str(selected_document['filename'] if selected_document else display_project_name(project['name'], project['id'])))}</div></div>",
        unsafe_allow_html=True,
    )

    relationships = []
    traceability_records = []
    source_pages = []
    if selected_document:
        try:
            artifact_dir = Path(selected_document["artifact_dir"])
            relationship_path = artifact_dir / "relationships.json"
            traceability_path = artifact_dir / "traceability.json"
            pages_path = artifact_dir / "pages.json"
            if relationship_path.exists():
                with relationship_path.open("r", encoding="utf-8") as file:
                    relationships = json.load(file)
            if traceability_path.exists():
                with traceability_path.open("r", encoding="utf-8") as file:
                    traceability_records = json.load(file)
            if pages_path.exists():
                with pages_path.open("r", encoding="utf-8") as file:
                    source_pages = json.load(file)
            relationships = [
                item for item in relationships
                if item.get("project_id") == project["id"]
                and item.get("document_id") == selected_document["document_id"]
            ]
            traceability_records = [
                item for item in traceability_records
                if item.get("project_id") == project["id"]
                and item.get("document_id") == selected_document["document_id"]
            ]
            source_pages = [
                item for item in source_pages
                if item.get("project_id") == project["id"]
                and item.get("document_id") == selected_document["document_id"]
            ]
            relationships = resolve_relationship_pages(relationships, source_pages)
        except AuthorizationError as error:
            st.error(str(error))

    entity_types_by_name = {}
    for record in traceability_records:
        entity_types_by_name.setdefault(record.get("entity"), set()).add(record.get("type"))
    entity_type_options = sorted(
        {entity_type for values in entity_types_by_name.values() for entity_type in values if entity_type}
    )
    relationship_type_options = sorted(
        {str(item.get("relationship")) for item in relationships if item.get("relationship")}
    )

    architecture_scope_key = (
        f"{project['id']}_{selected_document['document_id'] if selected_document else 'none'}"
    )
    architecture_search_key = f"architecture_search_{architecture_scope_key}"
    architecture_entity_type_key = f"architecture_entity_type_{architecture_scope_key}"
    architecture_relationship_type_key = f"architecture_relationship_type_{architecture_scope_key}"
    applied_search_key = f"architecture_applied_search_{architecture_scope_key}"
    applied_entity_type_key = f"architecture_applied_entity_type_{architecture_scope_key}"
    applied_relationship_type_key = f"architecture_applied_relationship_type_{architecture_scope_key}"
    if applied_search_key not in st.session_state:
        st.session_state[applied_search_key] = ""
        st.session_state[applied_entity_type_key] = "All"
        st.session_state[applied_relationship_type_key] = "All"

    def submit_architecture_controls():
        submitted_query = st.session_state.get(architecture_search_key, "").strip()
        st.session_state[applied_search_key] = submitted_query
        if submitted_query:
            st.session_state[applied_entity_type_key] = st.session_state.get(
                architecture_entity_type_key, "All"
            )
            st.session_state[applied_relationship_type_key] = st.session_state.get(
                architecture_relationship_type_key, "All"
            )
        else:
            st.session_state[architecture_entity_type_key] = "All"
            st.session_state[architecture_relationship_type_key] = "All"
            st.session_state[applied_entity_type_key] = "All"
            st.session_state[applied_relationship_type_key] = "All"

    def reset_architecture_controls():
        st.session_state[architecture_search_key] = ""
        st.session_state[architecture_entity_type_key] = "All"
        st.session_state[architecture_relationship_type_key] = "All"
        st.session_state[applied_search_key] = ""
        st.session_state[applied_entity_type_key] = "All"
        st.session_state[applied_relationship_type_key] = "All"

    with st.container(key="architecture_controls"):
        search_col, entity_col, relationship_col, reset_col = st.columns(
            [3.0, 1.0, 1.15, 0.65], gap="small", vertical_alignment="center"
        )
        with search_col:
            architecture_search = st.text_input(
                "Search",
                placeholder="Search entities or relationships...",
                key=architecture_search_key,
            )
            st.button(
                "Submit",
                key=f"architecture_submit_{architecture_scope_key}",
                type="primary",
                on_click=submit_architecture_controls,
            )
        with entity_col:
            selected_entity_type = st.selectbox(
                "Entity Type",
                ["All"] + entity_type_options,
                key=architecture_entity_type_key,
            )
        with relationship_col:
            selected_relationship_type = st.selectbox(
                "Relationship Type",
                ["All"] + relationship_type_options,
                key=architecture_relationship_type_key,
            )
        with reset_col:
            st.button(
                "Reset",
                key="architecture_reset",
                on_click=reset_architecture_controls,
                use_container_width=True,
            )

    applied_search = st.session_state[applied_search_key]
    applied_entity_type = st.session_state[applied_entity_type_key]
    applied_relationship_type = st.session_state[applied_relationship_type_key]

    filtered_relationships = relationships
    if applied_entity_type != "All":
        selected_entities = {
            name for name, types in entity_types_by_name.items()
            if applied_entity_type in types
        }
        filtered_relationships = [
            item for item in filtered_relationships
            if item.get("source") in selected_entities or item.get("target") in selected_entities
        ]
    if applied_relationship_type != "All":
        filtered_relationships = [
            item for item in filtered_relationships
            if item.get("relationship") == applied_relationship_type
        ]
    filtered_relationships = filter_relationships(
        filtered_relationships, applied_search
    )

    with st.container(key="architecture_workspace"):
        graph_col, inspector_col = st.columns([1.8, 1.0], gap="small")
        with graph_col:
            with st.container(key="architecture_graph_panel"):
                st.markdown("<h2>Architecture Graph</h2>", unsafe_allow_html=True)
                selected_relationship = None
                graph_nodes = sorted({
                    name
                    for item in filtered_relationships
                    for name in (item.get("source"), item.get("target"))
                    if name
                })
                if filtered_relationships:
                    selected_relationship = render_relationship_graph(
                        filtered_relationships,
                        project_name=display_project_name(project["name"], project["id"]),
                        document_name=selected_document["filename"] if selected_document else None,
                        key_prefix=f"architecture_graph_{project['id']}_{selected_document['id'] if selected_document else 'none'}",
                        show_search=False,
                        show_inspector=False,
                    )
                elif not selected_document:
                    st.info("No document selected. Select a document to explore its architecture.")
                elif not relationships:
                    st.info("No architecture relationships are available for this document.")
                else:
                    st.info("No matching architecture relationships found.")

        with inspector_col:
            with st.container(key="architecture_inspector_panel"):
                st.markdown("<h2>Inspector</h2>", unsafe_allow_html=True)
                node_key = f"architecture_selected_node_{selected_document['id'] if selected_document else 'none'}"
                relationship_tab, entity_tab, source_tab = st.tabs(
                    ["Relationship", "Entity / Node", "Source"]
                )
                with relationship_tab:
                    st.markdown("<h3>Relationship details</h3>", unsafe_allow_html=True)
                    if selected_relationship:
                        st.markdown("<div class='architecture-inspector-label'>Source</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='architecture-inspector-value'>{escape(str(selected_relationship.get('source', 'n/a')))}</div>", unsafe_allow_html=True)
                        st.markdown("<div class='architecture-inspector-label'>Relationship</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='architecture-inspector-value'>{escape(str(selected_relationship.get('relationship', 'n/a')))}</div>", unsafe_allow_html=True)
                        st.markdown("<div class='architecture-inspector-label'>Target</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='architecture-inspector-value'>{escape(str(selected_relationship.get('target', 'n/a')))}</div>", unsafe_allow_html=True)
                        st.markdown("<div class='architecture-inspector-label'>Source page</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='architecture-inspector-value'>{escape(str(selected_relationship.get('page', 'Not recorded')))}</div>", unsafe_allow_html=True)
                    else:
                        st.info("Select a relationship")

                with entity_tab:
                    if graph_nodes:
                        if st.session_state.get(node_key) not in graph_nodes:
                            st.session_state[node_key] = graph_nodes[0]
                        selected_node = st.selectbox(
                            "Inspect entity / graph node",
                            graph_nodes,
                            key=node_key,
                        )
                        node_records = [
                            item for item in traceability_records
                            if item.get("entity") == selected_node
                        ]
                        node_types = sorted({item.get("type") for item in node_records if item.get("type")})
                        node_pages = sorted({item.get("page") for item in node_records if item.get("page") is not None}, key=lambda page: (0, int(page)) if str(page).isdigit() else (1, str(page)))
                        st.markdown("<div class='architecture-inspector-label'>Entity</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='architecture-inspector-value'>{escape(selected_node)}</div>", unsafe_allow_html=True)
                        st.markdown("<div class='architecture-inspector-label'>Type</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='architecture-inspector-value'>{escape(', '.join(node_types) or 'Not recorded')}</div>", unsafe_allow_html=True)
                        st.markdown("<div class='architecture-inspector-label'>Source pages</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='architecture-inspector-value'>{escape(', '.join(map(str, node_pages)) or 'Not recorded')}</div>", unsafe_allow_html=True)
                        connected = [item for item in relationships if selected_node in (item.get("source"), item.get("target"))]
                        st.markdown("<div class='architecture-inspector-label'>Connected relationships</div>", unsafe_allow_html=True)
                        if connected:
                            for item in connected:
                                st.caption(f"{item.get('source')} → {item.get('relationship')} → {item.get('target')} · Page {item.get('page', 'n/a')}")
                        else:
                            st.caption("No connected relationships recorded.")
                    else:
                        st.session_state[node_key] = None
                        st.info("No graph entities match the current filters.")

                with source_tab:
                    evidence_relationship = selected_relationship
                    evidence_entity = (
                        evidence_relationship.get("source")
                        if evidence_relationship
                        else st.session_state.get(node_key)
                    )
                    evidence_page = (
                        evidence_relationship.get("page")
                        if evidence_relationship
                        else None
                    )
                    if evidence_page is None and evidence_entity:
                        entity_pages = sorted(
                            {item.get("page") for item in traceability_records if item.get("entity") == evidence_entity and item.get("page") is not None},
                            key=lambda page: (0, int(page)) if str(page).isdigit() else (1, str(page)),
                        )
                        evidence_page = entity_pages[0] if entity_pages else None
                    if selected_document and evidence_entity and evidence_page is not None:
                        evidence_context = get_entity_context(
                            source_pages, evidence_entity, evidence_page
                        )
                        st.markdown(f"**Document:** {selected_document['filename']}")
                        st.markdown(f"**Page:** {evidence_page}")
                        st.markdown(f"**Entity:** {evidence_entity}")
                        st.markdown(
                            f"<div class='architecture-provenance'>{escape(evidence_context or 'No stored source context is available.')}</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.info("No source provenance is available for the current selection.")

elif st.session_state.active_page == "Compare Versions":
    st.markdown('<div class="subsection-head"><h3>Version Control</h3><p>Compare architecture versions</p></div>', unsafe_allow_html=True)
    if can_compare(current_user["id"], project["id"]):
        old_file = st.file_uploader("Upload older / baseline document", type=["pdf"], key=f"comparison_old_{project['id']}")
        new_file = st.file_uploader("Upload newer / current document", type=["pdf"], key=f"comparison_new_{project['id']}")
        if old_file and new_file and st.button("Compare Documents"):
            import tempfile
            from ingestion.pdf_parser import extract_text_from_pdf
            from extraction.traceability import extract_traceable_entities
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_old:
                temp_old.write(old_file.getbuffer())
                old_path = temp_old.name
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_new:
                temp_new.write(new_file.getbuffer())
                new_path = temp_new.name
            old_pages = extract_text_from_pdf(old_path)
            new_pages = extract_text_from_pdf(new_path)
            old_records = extract_traceable_entities(old_pages)
            new_records = extract_traceable_entities(new_pages)
            comparison = compare_entities(old_records, new_records)
            st.session_state.comparison_result = comparison
            st.subheader("Comparison summary")
            col1, col2, col3 = st.columns(3)
            col1.metric("Added", len(comparison["added"]))
            col2.metric("Removed", len(comparison["removed"]))
            col3.metric("Unchanged", len(comparison["unchanged"]))
            st.subheader("Added")
            for item in comparison["added"]:
                st.write(f"**{item['entity']}** — {item['type']}")
    else:
        st.info("Your project role does not allow comparison.")
    if st.session_state.document_info:
        versions = list_document_versions(
            st.session_state.document_info.get("filename"),
            user_id=current_user["id"],
            project_id=project["id"],
        )
        st.markdown("### Document versions")
        if versions:
            version_columns = st.columns(min(len(versions), 3))
            for index, item in enumerate(versions):
                with version_columns[index % len(version_columns)]:
                    st.metric(f"Version {item['version']}", f"{item['page_count']} pages")
                    st.caption(
                        f"{item['upload_timestamp']}  ·  {item['chunk_count']} chunks"
                    )
        else:
            st.info("Version history is not available yet.")

elif st.session_state.active_page == "Review & Approvals":
    st.markdown('<div class="subsection-head"><h3>Review & Approvals</h3><p>Workflow board</p></div>', unsafe_allow_html=True)
    review_items = list_reviews(10, user_id=current_user["id"], project_id=project["id"])
    if review_items:
        for item in review_items:
            st.markdown(f"<div style='background: rgba(17,24,39,0.85); border:1px solid #243148; border-radius:0.8rem; padding:0.9rem; margin-bottom:0.7rem;'><div style='color:#F8FAFC;font-weight:700;'>{item['question']}</div><div style='color:#94A3B8;font-size:0.74rem;margin-top:0.3rem;'>Status: {item['review_status']}</div></div>", unsafe_allow_html=True)
    else:
        st.info("No review entries yet.")

elif st.session_state.active_page == "Audit Logs":
    st.markdown('<div class="subsection-head"><h3>Audit & Activity</h3><p>Security and operations timeline</p></div>', unsafe_allow_html=True)
    for entry in read_logs(20, user_id=current_user["id"], project_id=project["id"]):
        st.markdown(f"<div style='background: rgba(17,24,39,0.85); border:1px solid #243148; border-radius:0.8rem; padding:0.8rem; margin-bottom:0.6rem;'><div style='color:#94A3B8;font-size:0.72rem;letter-spacing:0.12em;text-transform:uppercase;'>{entry['timestamp']} · {entry['event_type']}</div><div style='color:#F8FAFC;font-weight:700;margin-top:0.3rem;'>{entry['document_name'] or 'Workspace event'}</div></div>", unsafe_allow_html=True)

elif st.session_state.active_page == "Projects":
    st.markdown('<div class="subsection-head"><h3>Projects</h3><p>Current workspace overview</p></div>', unsafe_allow_html=True)
    if current_user["role"] == "admin":
        with st.form("create_project_form"):
            new_project_name = st.text_input("New project name")
            create_project_submitted = st.form_submit_button("Create Project")
        if create_project_submitted:
            try:
                new_project = create_project(current_user["id"], new_project_name)
                st.session_state.current_project_id = new_project["id"]
                st.session_state.current_project_name = new_project["name"]
                st.rerun()
            except (ValueError, AuthorizationError) as error:
                st.error(str(error))
    if project["role"] == "admin":
        with st.form("add_project_member_form"):
            member_username = st.text_input("Existing username", key="member_username")
            member_role = st.selectbox("Project role", ["admin", "architect", "viewer"], key="member_role")
            add_member_submitted = st.form_submit_button("Add Project Member")
        if add_member_submitted:
            try:
                add_project_member(current_user["id"], project["id"], member_username, member_role)
                log_event(
                    "PROJECT_MEMBER_ADDED", user_id=current_user["id"],
                    username=current_user["username"], project_id=project["id"],
                    details={"member_username": member_username, "role": member_role},
                )
                st.success("Project membership updated.")
                st.rerun()
            except (ValueError, AuthorizationError) as error:
                st.error(str(error))
    for project_item in projects:
        st.markdown(f"<div style='background: rgba(17,24,39,0.85); border:1px solid #243148; border-radius:1rem; padding:1rem; margin-bottom:0.8rem;'><div style='font-size:1.1rem;font-weight:800;color:#F8FAFC;'>{escape(display_project_name(project_item['name'], project_item['id']))}</div><div style='color:#94A3B8;margin-top:0.4rem;'>Members: {project_item.get('member_count', 0)} · Documents: {project_item.get('document_count', 0)} · Role: {project_item.get('role', 'member')}</div></div>", unsafe_allow_html=True)

elif st.session_state.active_page == "Settings":
    st.markdown('<div class="subsection-head"><h3>Settings</h3><p>Configuration and access controls</p></div>', unsafe_allow_html=True)
    profile, project_col, access, system = st.columns(4)
    with profile:
        st.markdown("### Profile")
        st.write(f"User: {current_user['username']}")
        st.write(f"Role: {current_user['role']}")
    with project_col:
        st.markdown("### Project")
        st.write(f"Project: {display_project_name(project['name'], project['id'])}")
        st.write(f"Role: {project['role']}")
    with access:
        st.markdown("### Access control")
        st.write("Project membership and permissions remain driven by the existing backend RBAC logic.")
        if current_user["role"] == "admin":
            with st.expander("Create User"):
                with st.form("create_project_user_form", clear_on_submit=True):
                    new_username = st.text_input("New username", key="new_project_username")
                    new_password = st.text_input("Temporary password", type="password", key="new_project_password")
                    account_role = st.selectbox("Account role", ["admin", "architect", "viewer"], key="new_account_role")
                    project_role = st.selectbox("Role in this project", ["admin", "architect", "viewer"], key="new_member_role")
                    create_user_submitted = st.form_submit_button("Create User")
                if create_user_submitted:
                    try:
                        created_user = create_user(
                            current_user["id"], new_username, new_password, account_role
                        )
                        add_project_member(
                            current_user["id"], project["id"], created_user["username"], project_role
                        )
                        log_event(
                            "USER_CREATED", user_id=current_user["id"],
                            username=current_user["username"], project_id=project["id"],
                            details={
                                "created_username": created_user["username"],
                                "account_role": account_role,
                                "project_role": project_role,
                            },
                        )
                        st.success("User created and added to this project.")
                    except (ValueError, AuthorizationError) as error:
                        st.error(str(error))

            with st.expander("Manage Users"):
                managed_users = list_users(current_user["id"])
                user_by_id = {user["id"]: user for user in managed_users}
                target_user_id = st.selectbox(
                    "Account",
                    options=list(user_by_id),
                    format_func=lambda user_id: user_by_id[user_id]["username"],
                    key="managed_user_id",
                )
                target_user = user_by_id[target_user_id]
                updated_role = st.selectbox(
                    "Account role",
                    ["admin", "architect", "viewer"],
                    index=["admin", "architect", "viewer"].index(target_user["role"]),
                    key="managed_user_role",
                )
                updated_active = st.checkbox(
                    "Account active", value=target_user["active"], key="managed_user_active"
                )
                if st.button("Save User", key="save_managed_user"):
                    try:
                        update_user(
                            current_user["id"],
                            target_user_id,
                            role=updated_role,
                            active=updated_active,
                        )
                        log_event(
                            "USER_UPDATED", user_id=current_user["id"],
                            username=current_user["username"], project_id=project["id"],
                            details={
                                "target_username": target_user["username"],
                                "role": updated_role,
                                "active": updated_active,
                            },
                        )
                        st.success("User account updated.")
                        st.rerun()
                    except (ValueError, AuthorizationError) as error:
                        st.error(str(error))
    with system:
        st.markdown("### System status")
        st.write("Dark architecture workspace is active.")
    if st.button("Exports", key="settings_exports", icon=":material/download:", type="tertiary"):
        st.session_state.active_page = "Exports"
        st.rerun()

elif st.session_state.active_page == "Exports":
    st.markdown('<div class="subsection-head"><h3>Exports</h3><p>Download artifacts generated by this project</p></div>', unsafe_allow_html=True)
    exp_col1, exp_col2, exp_col3, exp_col4 = st.columns(4)
    with exp_col1:
        if st.session_state.document_info and can_export(current_user["id"], project["id"]):
            traceability_payload = load_traceability_from_file(st.session_state.document_info.get("traceability_path")) if st.session_state.document_info.get("traceability_path") else []
            if st.download_button("Download traceability JSON", data=export_json_bytes(traceability_payload, "traceability_results.json"), file_name="traceability_results.json", mime="application/json"):
                log_event("EXPORT", document_name=st.session_state.document_info.get("filename"), details={"type": "traceability_json"}, user_id=current_user["id"], username=current_user["username"], project_id=project["id"], document_id=st.session_state.document_info.get("document_id"))
    with exp_col2:
        if st.session_state.document_info and st.session_state.document_info.get("relationship_path") and can_export(current_user["id"], project["id"]):
            with open(st.session_state.document_info["relationship_path"], "r", encoding="utf-8") as file:
                relationship_payload = json.load(file)
            if st.download_button("Download relationship JSON", data=export_json_bytes(relationship_payload, "relationship_results.json"), file_name="relationship_results.json", mime="application/json"):
                log_event("EXPORT", document_name=st.session_state.document_info.get("filename"), details={"type": "relationship_json"}, user_id=current_user["id"], username=current_user["username"], project_id=project["id"], document_id=st.session_state.document_info.get("document_id"))
    with exp_col3:
        if st.session_state.last_answer and can_export(current_user["id"], project["id"]):
            if st.download_button("Download Q&A JSON", data=export_json_bytes({"question": st.session_state.last_answer["question"], "answer": st.session_state.last_answer["answer"], "confidence": st.session_state.last_answer["confidence"], "sources": st.session_state.last_answer["sources"]}, "qa_result.json"), file_name="qa_result.json", mime="application/json"):
                log_event("EXPORT", details={"type": "qa_json"}, user_id=current_user["id"], username=current_user["username"], project_id=project["id"], document_id=st.session_state.document_info.get("document_id") if st.session_state.document_info else None)
    with exp_col4:
        if st.session_state.comparison_result and can_export(current_user["id"], project["id"]):
            if st.download_button("Download comparison JSON", data=export_json_bytes(st.session_state.comparison_result, "comparison_result.json"), file_name="comparison_result.json", mime="application/json"):
                log_event("EXPORT", details={"type": "comparison_json"}, user_id=current_user["id"], username=current_user["username"], project_id=project["id"])

else:
    st.info("Select a page from the top navigation.")

st.stop()



# ---------------------------------------------------------
# PDF Upload
# ---------------------------------------------------------

st.markdown('<div id="document-workspace"></div>', unsafe_allow_html=True)
st.header("📄 Document workspace")
st.markdown(
    '<p class="section-note">Load an AUTOSAR PDF to unlock extraction, retrieval, comparison, and traceability views.</p>',
    unsafe_allow_html=True,
)

if can_upload(current_user["id"], project["id"]):
    uploaded_file = st.file_uploader(
        "Choose an AUTOSAR PDF",
        type=["pdf"],
        key=f"project_document_uploader_{project['id']}",
    )
else:
    uploaded_file = None
    st.info("Your project role allows viewing and querying, but not uploading documents.")


if uploaded_file is not None:

    if st.button(
        "⚙️ Process Document",
        type="primary"
    ):

        with st.spinner(
            "Processing AUTOSAR document..."
        ):

            try:

                document_info = process_uploaded_pdf(
                    uploaded_file,
                    user_id=current_user["id"],
                    project_id=project["id"],
                )

                st.session_state.document_ready = True
                st.session_state.document_info = document_info
                log_event(
                    "DOCUMENT_UPLOADED",
                    document_name=uploaded_file.name,
                    status="success",
                    details={"version": document_info.get("version"), "pages": document_info.get("pages")},
                    user_id=current_user["id"],
                    username=current_user["username"],
                    project_id=project["id"],
                    document_id=document_info.get("document_id"),
                )
                st.rerun()

            except Exception as e:
                st.session_state.document_ready = False
                log_event(
                    "DOCUMENT_UPLOAD", document_name=getattr(uploaded_file, "name", "unknown"),
                    status="error", details={"error": str(e)}, user_id=current_user["id"],
                    username=current_user["username"], project_id=project["id"],
                )
                if str(e) == EMPTY_UPLOAD_MESSAGE:
                    st.error(EMPTY_UPLOAD_MESSAGE)
                else:
                    st.error(f"Document processing failed: {e}")


# ---------------------------------------------------------
# Document information
# ---------------------------------------------------------

if st.session_state.document_ready:

    info = st.session_state.document_info

    st.success(f"Document ready · {info['filename']} · Version {info['version']}")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Pages",
            info["pages"]
        )

    with col2:
        st.metric(
            "Chunks",
            info["chunks"]
        )

    with col3:
        st.metric("Vector index", "Ready")


st.divider()


# ---------------------------------------------------------
# Question section
# ---------------------------------------------------------

st.markdown('<div id="grounded-qa"></div>', unsafe_allow_html=True)
st.header("💬 Grounded Q&A")
st.markdown(
    '<p class="section-note">Ask about the uploaded document. Answers are checked against retrieved source context.</p>',
    unsafe_allow_html=True,
)

question = st.text_area(
    "Enter your question",
    placeholder=(
        "Example: What are the main views used "
        "to describe the Adaptive Platform architecture?"
    ),
    height=100,
    key="project_question",
)


if st.button("🔍 Ask AutoArch-AI"):

    if not st.session_state.document_ready:

        st.warning(
            "Please upload and process a PDF first."
        )

    elif not question.strip():

        st.warning(
            "Please enter a question."
        )

    else:

        with st.spinner(
            "Searching the document and generating answer..."
        ):

            try:

                # -----------------------------------------
                # Retrieve from uploaded collection
                # -----------------------------------------

                results = retrieve_context(
                    question,
                    top_k=5,
                    user_id=current_user["id"],
                    project_id=project["id"],
                )

                # -----------------------------------------
                # Build context
                # -----------------------------------------

                documents = results["documents"][0]

                metadatas = results["metadatas"][0]

                context_parts = []

                for i, (
                    document,
                    metadata
                ) in enumerate(
                    zip(
                        documents,
                        metadatas
                    ),
                    start=1
                ):

                    context_parts.append(
                        f"""
SOURCE {i}

Page: {metadata['page_number']}
Chunk ID: {metadata['chunk_id']}

CONTENT:
{document}
"""
                    )

                context = "\n".join(
                    context_parts
                )


                relationships = results.get("relationships", [])

                if relationships:
                    relationship_parts = []

                    for relationship in relationships:
                        relationship_parts.append(
                            f"{relationship['source']} "
                            f"{relationship['relationship']} "
                            f"{relationship['target']} "
                            f"(Page {relationship['page']})"
                        )

                    relationship_context = (
                        "\n\nARCHITECTURE RELATIONSHIPS:\n"
                        + "\n".join(relationship_parts)
                    )

                    context += relationship_context

                # -----------------------------------------
                # Grounded prompt
                # -----------------------------------------

                prompt = f"""

You are an engineering document analysis assistant.

Answer the user's question using ONLY the provided document context.

STRICT RULES:

1. Use only information explicitly present in the document context.

2. Prefer exact wording from the document when answering.
   Only make a summary if the same meaning is explicitly
   stated in the context.

3. When the question asks for names, types, views,
   components, or categories, return only those names
   or categories. Do not explain them unless the document
   explicitly provides the explanation.

4. Do not infer technical details that are not stated.

5. Preserve the terminology used by the document.

6. Give the shortest complete answer supported by the context.

7. If the answer is explicitly present in the context,
   answer it directly.

8. If the context genuinely does not contain the answer,
   say exactly:

"I could not find enough information in the document."

DOCUMENT CONTEXT:

{context}

USER QUESTION:

{question}
"""

                # -----------------------------------------
                # Generate answer
                # -----------------------------------------

                answer = generate_answer(prompt)

                if not answer or not answer.strip():
                    answer = "I could not find enough information in the document."

                confidence = results["confidence"]
                st.session_state.last_answer = {
                    "question": question,
                    "answer": answer,
                    "confidence": confidence,
                    "sources": format_sources(results),
                    "timestamp": None,
                }

                log_event(
                    "DOCUMENT_QUERIED",
                    document_name=st.session_state.document_info.get("filename") if st.session_state.document_info else None,
                    question=question,
                    status="success",
                    user_id=current_user["id"],
                    username=current_user["username"],
                    project_id=project["id"],
                    document_id=st.session_state.document_info.get("document_id") if st.session_state.document_info else None,
                )
                log_event(
                    "ANSWER_GENERATED",
                    document_name=st.session_state.document_info.get("filename") if st.session_state.document_info else None,
                    question=question,
                    status="success",
                    details={"confidence": confidence},
                    user_id=current_user["id"],
                    username=current_user["username"],
                    project_id=project["id"],
                    document_id=st.session_state.document_info.get("document_id") if st.session_state.document_info else None,
                )

                # -----------------------------------------
                # Sources
                # -----------------------------------------

                sources = format_sources(
                    results
                )

                if sources:
                    primary_source = sources[0]

                    st.markdown('<div class="evidence-label">Primary source</div>', unsafe_allow_html=True)
                    st.markdown(
                        f"<div class=\"source-chip\"><strong>Page {primary_source['page']}</strong>"
                        f" &nbsp;·&nbsp; Chunk {primary_source['chunk_id']}</div>",
                        unsafe_allow_html=True,
                    )

                # -----------------------------------------
                # Grounding check
                # -----------------------------------------

                grounding = check_grounding(
                    answer,
                    context
                )

                # -----------------------------------------
                # Answer
                # -----------------------------------------

                with st.container(border=True):
                    st.markdown("### Answer")

                    if grounding["supported"]:
                        st.info(answer)
                    else:
                        st.warning(
                            "The generated answer contains "
                            "information that may not be "
                            "sufficiently supported by the "
                            "retrieved document context."
                        )
                        st.warning(answer)

                # -----------------------------------------
                # Retrieval Confidence
                # -----------------------------------------

                grounding_score = grounding["score"]
                evidence_columns = st.columns(2)
                with evidence_columns[0]:
                    st.markdown("### Retrieval confidence")
                    st.metric(
                        "Confidence",
                        (
                            f"{confidence['level']} — "
                            f"{confidence['score']:.4f}"
                        )
                    )
                with evidence_columns[1]:
                    st.markdown("### Grounding check")
                    if grounding["supported"]:
                        st.success(f"Supported — {grounding_score:.4f}")
                    else:
                        st.warning(f"Weak Support — {grounding_score:.4f}")

                # -----------------------------------------
                # Sources
                # -----------------------------------------

                with st.container(border=True):
                    st.markdown("### Citations")
                    for source in sources:
                        st.caption(
                            f"[{source['source_number']}] "
                            f"Page {source['page']} | "
                            f"Chunk {source['chunk_id']}"
                        )

                if can_review(current_user["id"], project["id"]):
                    review_col1, review_col2 = st.columns(2)
                    with review_col1:
                        if st.button("✅ Approve", key="approve_answer"):
                            save_review(
                                question, answer, confidence, "approved",
                                user_id=current_user["id"], project_id=project["id"],
                            )
                            log_event(
                                "REVIEW", document_name=st.session_state.document_info.get("filename"),
                                user_id=current_user["id"], username=current_user["username"],
                                project_id=project["id"],
                                document_id=st.session_state.document_info.get("document_id"),
                                details={"review_status": "approved"},
                            )
                            st.success("Answer marked as approved.")
                    with review_col2:
                        if st.button("⚠️ Needs Review", key="needs_review_answer"):
                            save_review(
                                question, answer, confidence, "needs_review",
                                user_id=current_user["id"], project_id=project["id"],
                            )
                            log_event(
                                "REVIEW", document_name=st.session_state.document_info.get("filename"),
                                user_id=current_user["id"], username=current_user["username"],
                                project_id=project["id"],
                                document_id=st.session_state.document_info.get("document_id"),
                                details={"review_status": "needs_review"},
                            )
                            st.warning("Answer marked for human review.")

                if st.session_state.last_answer and can_export(current_user["id"], project["id"]):
                    if st.download_button(
                        label="Download Q&A JSON",
                        data=export_json_bytes({
                            "question": st.session_state.last_answer["question"],
                            "answer": st.session_state.last_answer["answer"],
                            "confidence": st.session_state.last_answer["confidence"],
                            "sources": st.session_state.last_answer["sources"],
                        }, "qa_answer.json"),
                        file_name="qa_answer.json",
                        mime="application/json",
                    ):
                        log_event(
                            "EXPORT", document_name=st.session_state.document_info.get("filename"),
                            user_id=current_user["id"], username=current_user["username"],
                            project_id=project["id"],
                            document_id=st.session_state.document_info.get("document_id"),
                            details={"type": "qa_json"},
                        )

            except Exception as e:

                if "GROQ_API_KEY" in str(e):
                    st.error(
                        "Q&A is unavailable because GROQ_API_KEY is not configured. "
                        "Set it in the environment or Streamlit secrets, then try again."
                    )
                else:
                    st.error(
                        f"Question processing failed: {e}"
                    )

st.divider()
st.markdown('<div id="architecture-traceability"></div>', unsafe_allow_html=True)
st.header("🔎 Architecture traceability")
st.markdown(
    '<p class="section-note">Browse extracted entities by type, page, and source context.</p>',
    unsafe_allow_html=True,
)

traceability_path = (
    st.session_state.document_info.get("traceability_path")
    if st.session_state.document_info
    else None
)

relationship_path = (
    st.session_state.document_info.get("relationship_path")
    if st.session_state.document_info
    else None
)

if not traceability_path:
    st.info("Please upload and process a document first.")

else:
    records = load_traceability_from_file(traceability_path)

    # Architecture entity summary
    entity_counts = {}

    for record in records:
        entity_type = record["type"]
        entity_counts[entity_type] = (
            entity_counts.get(entity_type, 0) + 1
        )

    relationship_records = []
    if relationship_path and Path(relationship_path).exists():
        with open(relationship_path, "r", encoding="utf-8") as file:
            relationship_records = json.load(file)

    st.subheader("📊 Architecture Summary")

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric("Components", entity_counts.get("components", 0))
    col2.metric("Interfaces", entity_counts.get("interfaces", 0))
    col3.metric("Ports", entity_counts.get("ports", 0))
    col4.metric("Services", entity_counts.get("services", 0))
    col5.metric("Architecture Views", entity_counts.get("architecture_views", 0))
    col6.metric("Relationships", len(relationship_records))
    st.caption(f"Detected relationships: {len(relationship_records)}")

    st.divider()

    # Get available entity types
    entity_types = sorted(
        set(record["type"] for record in records)
    )

    selected_type = st.selectbox(
        "Filter by entity type",
        ["All"] + entity_types
    )

    search_query = st.text_input(
        "Search for an architecture entity",
        placeholder="Example: WatchdogInterface"
    )

    filtered_records = records

    # Apply type filter
    if selected_type != "All":
        filtered_records = [
            record
            for record in filtered_records
            if record["type"] == selected_type
        ]

    # Apply search filter
    if search_query.strip():
        filtered_records = [
            record
            for record in filtered_records
            if search_query.lower()
            in record["entity"].lower()
        ]

    st.write(
        f"**{len(filtered_records)} matching records**"
    )

    pages_path = (
        st.session_state.document_info.get("pages_path")
        if st.session_state.document_info
        else None
    )

    if pages_path:
        pages = load_pages_from_file(pages_path)
    else:
        pages = []

    if filtered_records:

        for record in filtered_records:
            label = (
                f"{record['entity']}  ·  {record['type']}  ·  "
                f"Page {record.get('page')}"
            )
            with st.expander(label):
                if pages:
                    context = get_entity_context(pages, record["entity"], record.get("page"))
                    if context:
                        st.caption("Document context")
                        st.info(context)

    else:
        st.info("No matching architecture entity found.")

    st.divider()
    st.markdown('<div id="relationship-explorer"></div>', unsafe_allow_html=True)
    st.header("🔗 Relationship explorer")
    st.markdown(
        '<p class="section-note">Inspect how extracted architecture entities connect across the document.</p>',
        unsafe_allow_html=True,
    )

    if not relationship_path:
        st.info("No architecture relationships found.")

    else:
        relationships = relationship_records

        st.write(
            f"**{len(relationships)} relationships detected**"
        )

        relationship_search = st.text_input(
            "Search architecture relationships",
            placeholder="Example: PPort, RPort, provides, consumes"
        )

        filtered_relationships = relationships

        if relationship_search.strip():
            query = relationship_search.lower()

            filtered_relationships = [
                relationship
                for relationship in relationships
                if (
                    query in relationship["source"].lower()
                    or query in relationship["relationship"].lower()
                    or query in relationship["target"].lower()
                )
            ]

        st.write(
            f"**{len(filtered_relationships)} matching relationships**"
        )

        if filtered_relationships:

            for relationship in filtered_relationships:
                with st.container(border=True):
                    st.markdown(
                        f"### {relationship['source']} "
                        f"→ {relationship['relationship']} "
                        f"→ {relationship['target']}"
                    )
                    st.caption(f"Source page {relationship['page']}")

        else:
            st.info("No matching architecture relationship found.")

    st.divider()

st.markdown('<div id="architecture-relationship-graph"></div>', unsafe_allow_html=True)
st.header("🔗 Architecture Relationship Graph")
if not st.session_state.document_info:
    render_relationship_graph([], project_name=display_project_name(project["name"], project["id"]), key_prefix=f"graph_{project['id']}")
else:
    try:
        graph_document = get_project_document(
            current_user["id"],
            project["id"],
            st.session_state.document_info["document_id"],
        )
        graph_relationship_path = Path(graph_document["artifact_dir"]) / "relationships.json"
        if graph_relationship_path.exists():
            with graph_relationship_path.open("r", encoding="utf-8") as file:
                project_relationships = json.load(file)
        else:
            project_relationships = []
        project_relationships = [
            relationship
            for relationship in project_relationships
            if relationship.get("project_id") == project["id"]
            and relationship.get("document_id") == graph_document["document_id"]
        ]
        render_relationship_graph(
            project_relationships,
            project_name=display_project_name(project["name"], project["id"]),
            document_name=graph_document["filename"],
            key_prefix=f"graph_{project['id']}_{graph_document['id']}",
        )
    except AuthorizationError as error:
        st.error(str(error))

st.markdown('<div id="document-comparison"></div>', unsafe_allow_html=True)
st.header("📑 Document comparison")
st.markdown(
    '<p class="section-note">Compare extracted architecture entities between a baseline and current document.</p>',
    unsafe_allow_html=True,
)

if can_compare(current_user["id"], project["id"]):
    old_file = st.file_uploader(
        "Upload older / baseline document",
        type=["pdf"],
        key=f"comparison_old_{project['id']}"
    )

    new_file = st.file_uploader(
        "Upload newer / current document",
        type=["pdf"],
        key=f"comparison_new_{project['id']}"
    )
else:
    old_file = new_file = None
    st.info("Your project role does not allow document comparison.")

if can_compare(current_user["id"], project["id"]) and old_file and new_file:

    if st.button("🔍 Compare Documents"):

        import tempfile
        from ingestion.pdf_parser import extract_text_from_pdf
        from extraction.traceability import extract_traceable_entities

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf"
        ) as temp_old:

            temp_old.write(old_file.getbuffer())
            old_path = temp_old.name

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf"
        ) as temp_new:

            temp_new.write(new_file.getbuffer())
            new_path = temp_new.name

        old_pages = extract_text_from_pdf(old_path)
        new_pages = extract_text_from_pdf(new_path)

        old_records = extract_traceable_entities(old_pages)
        new_records = extract_traceable_entities(new_pages)

        comparison = compare_entities(old_records, new_records)
        st.session_state.comparison_result = comparison
        log_event(
            "COMPARISON_RUN",
            document_name=f"{old_file.name} vs {new_file.name}",
            status="success",
            details={"added": len(comparison["added"]), "removed": len(comparison["removed"]), "unchanged": len(comparison["unchanged"])},
            user_id=current_user["id"],
            username=current_user["username"],
            project_id=project["id"],
            document_id=st.session_state.document_info.get("document_id") if st.session_state.document_info else None,
        )

        st.subheader("Comparison summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Added", len(comparison["added"]))
        col2.metric("Removed", len(comparison["removed"]))
        col3.metric("Unchanged", len(comparison["unchanged"]))

        st.subheader("➕ Added")
        if comparison["added"]:
            for item in comparison["added"]:
                st.write(f"**{item['entity']}** — {item['type']}  \nNew page: {item.get('new_page')}")
        else:
            st.info("No added entities.")

        st.subheader("➖ Removed")
        if comparison["removed"]:
            for item in comparison["removed"]:
                st.write(f"**{item['entity']}** — {item['type']}  \nOld page: {item.get('old_page')}")
        else:
            st.info("No removed entities.")

        st.subheader("✓ Unchanged")
        if comparison["unchanged"]:
            for item in comparison["unchanged"]:
                text = f"**{item['entity']}** — {item['type']}"
                if item.get("page_changed"):
                    text += f"  \nPage changed: {item.get('page_change')}"
                st.write(text)
        else:
            st.info("No unchanged entities.")

        st.subheader("Export comparison")
        comp_json = export_json_bytes(comparison, "comparison_results.json")
        comp_csv = export_csv_bytes([item for group in [comparison["added"], comparison["removed"], comparison["unchanged"]] for item in group], "comparison_results.csv")
        if can_export(current_user["id"], project["id"]):
            colA, colB = st.columns(2)
            with colA:
                if st.download_button("Download comparison JSON", data=comp_json, file_name="comparison_results.json", mime="application/json"):
                    log_event(
                        "EXPORT", document_name=f"{old_file.name} vs {new_file.name}",
                        status="success", details={"type": "comparison_json"},
                        user_id=current_user["id"], username=current_user["username"],
                        project_id=project["id"],
                    )
            with colB:
                if st.download_button("Download comparison CSV", data=comp_csv, file_name="comparison_results.csv", mime="text/csv"):
                    log_event(
                        "EXPORT", document_name=f"{old_file.name} vs {new_file.name}",
                        status="success", details={"type": "comparison_csv"},
                        user_id=current_user["id"], username=current_user["username"],
                        project_id=project["id"],
                    )

st.divider()
st.markdown('<div id="operations"></div>', unsafe_allow_html=True)
st.header("📦 Exports")
st.markdown(
    '<p class="section-note">Download the artifacts generated by the current analysis session.</p>',
    unsafe_allow_html=True,
)
exp_col1, exp_col2, exp_col3, exp_col4 = st.columns(4)
with exp_col1:
    if st.session_state.document_info and can_export(current_user["id"], project["id"]):
        traceability_payload = load_traceability_from_file(st.session_state.document_info.get("traceability_path")) if st.session_state.document_info.get("traceability_path") else []
        if st.download_button("Download traceability JSON", data=export_json_bytes(traceability_payload, "traceability_results.json"), file_name="traceability_results.json", mime="application/json"):
            log_event("EXPORT", document_name=st.session_state.document_info.get("filename"), details={"type": "traceability_json"}, user_id=current_user["id"], username=current_user["username"], project_id=project["id"], document_id=st.session_state.document_info.get("document_id"))
with exp_col2:
    if st.session_state.document_info and st.session_state.document_info.get("relationship_path") and can_export(current_user["id"], project["id"]):
        with open(st.session_state.document_info["relationship_path"], "r", encoding="utf-8") as file:
            relationship_payload = json.load(file)
        if st.download_button("Download relationship JSON", data=export_json_bytes(relationship_payload, "relationship_results.json"), file_name="relationship_results.json", mime="application/json"):
            log_event("EXPORT", document_name=st.session_state.document_info.get("filename"), details={"type": "relationship_json"}, user_id=current_user["id"], username=current_user["username"], project_id=project["id"], document_id=st.session_state.document_info.get("document_id"))
with exp_col3:
    if st.session_state.last_answer and can_export(current_user["id"], project["id"]):
        if st.download_button("Download Q&A JSON", data=export_json_bytes({"question": st.session_state.last_answer["question"], "answer": st.session_state.last_answer["answer"], "confidence": st.session_state.last_answer["confidence"], "sources": st.session_state.last_answer["sources"]}, "qa_result.json"), file_name="qa_result.json", mime="application/json"):
            log_event("EXPORT", details={"type": "qa_json"}, user_id=current_user["id"], username=current_user["username"], project_id=project["id"], document_id=st.session_state.document_info.get("document_id") if st.session_state.document_info else None)
with exp_col4:
    if st.session_state.comparison_result and can_export(current_user["id"], project["id"]):
        if st.download_button("Download comparison JSON", data=export_json_bytes(st.session_state.comparison_result, "comparison_result.json"), file_name="comparison_result.json", mime="application/json"):
            log_event("EXPORT", details={"type": "comparison_json"}, user_id=current_user["id"], username=current_user["username"], project_id=project["id"])

st.divider()
st.header("🧾 Audit log")
for entry in read_logs(10, user_id=current_user["id"], project_id=project["id"]):
    with st.container(border=True):
        st.caption(
            f"{entry['timestamp']}  ·  {entry['event_type']}  ·  "
            f"{entry['status']}"
        )
        st.write(
            f"{entry['document_name'] or 'Workspace event'}"
            f"{('  ·  ' + entry['question']) if entry['question'] else ''}"
        )

st.divider()
st.header("📝 Review queue")
review_items = list_reviews(10, user_id=current_user["id"], project_id=project["id"])
if review_items:
    for item in review_items:
        with st.container(border=True):
            status_class = "ready" if item["review_status"] == "approved" else "waiting"
            st.markdown(
                f'<span class="status-pill {status_class}">{item["review_status"]}</span>',
                unsafe_allow_html=True,
            )
            st.write(item["question"])
            st.info(item["answer"])
else:
    st.info("No review entries yet.")

st.divider()
st.header("📜 Document versions")
if st.session_state.document_info:
    versions = list_document_versions(
        st.session_state.document_info.get("filename"),
        user_id=current_user["id"],
        project_id=project["id"],
    )
    if versions:
        version_columns = st.columns(min(len(versions), 3))
        for index, item in enumerate(versions):
            with version_columns[index % len(version_columns)]:
                st.metric(f"Version {item['version']}", f"{item['page_count']} pages")
                st.caption(
                    f"{item['upload_timestamp']}  ·  {item['chunk_count']} chunks"
                )
    else:
        st.info("Version history is not available yet.")
