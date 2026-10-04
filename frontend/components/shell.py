import streamlit as st
from pathlib import Path
from html import escape


def apply_dark_theme():
    st.markdown(
        """
        <style>
        :root {
            --bg: #070B14;
            --bg-strong: #0A1220;
            --surface: #101827;
            --surface-elevated: #151E2F;
            --surface-soft: #0F172A;
            --input: #0D1626;
            --panel: rgba(17, 24, 39, 0.9);
            --line: #243148;
            --ink: #F8FAFC;
            --muted: #94A3B8;
            --placeholder: #64748B;
            --primary: #3B82F6;
            --secondary: #8B5CF6;
            --cyan: #22D3EE;
            --success: #22C55E;
            --warning: #F59E0B;
            --danger: #EF4444;
            --shadow-soft: 0 22px 48px rgba(2, 6, 23, 0.42);
            --shadow-card: 0 15px 30px rgba(15, 23, 42, 0.28);
        }

        html, body, [data-testid="stAppViewContainer"], .stApp {
            background: radial-gradient(circle at top left, rgba(59, 130, 246, 0.12), transparent 28%),
                        radial-gradient(circle at top right, rgba(139, 92, 246, 0.10), transparent 24%),
                        var(--bg);
            color: var(--ink);
            color-scheme: dark;
        }

        header[data-testid="stHeader"] {
            display: none !important;
        }

        [data-testid="stToolbar"], [data-testid="stDeployButton"] {
            display: none !important;
        }

        .block-container {
            max-width: 1600px !important;
            padding-top: 0 !important;
            padding-bottom: 3rem !important;
        }

        [data-testid="stSidebar"] {
            background: rgba(9, 14, 24, 0.96) !important;
            border-right: 1px solid var(--line) !important;
            box-shadow: inset -1px 0 0 rgba(148, 163, 184, 0.06) !important;
        }

        [data-testid="stSidebar"] > div {
            padding: 1rem 0.8rem 1.2rem !important;
        }

        [data-testid="stSidebarNav"], [data-testid="stSidebarUserContent"] {
            background: transparent !important;
        }

        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.25rem 0.2rem 0.5rem;
        }

        .brand-mark {
            width: 2.05rem;
            height: 2.05rem;
            border-radius: 0.9rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            font-weight: 900;
            box-shadow: 0 0 28px rgba(59, 130, 246, 0.32);
        }

        .sidebar-brand h3 {
            margin: 0;
            color: var(--ink);
            font-size: 1.15rem;
            font-weight: 800;
            letter-spacing: -0.04em;
        }

        .sidebar-caption {
            margin: 0 0 0.7rem;
            color: var(--muted);
            font-size: 0.72rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }

        .nav-rail {
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
            margin-top: 0.8rem;
        }

        .nav-item {
            display: flex;
            align-items: center;
            gap: 0.7rem;
            padding: 0.78rem 0.9rem;
            border-radius: 0.9rem;
            color: var(--muted);
            background: transparent;
            border: 1px solid transparent;
            font-weight: 700;
            letter-spacing: 0.02em;
            text-decoration: none;
        }

        .nav-item.active {
            background: linear-gradient(90deg, rgba(59, 130, 246, 0.12), rgba(59, 130, 246, 0.04));
            color: var(--ink);
            border-color: rgba(59, 130, 246, 0.22);
            box-shadow: inset 2px 0 0 var(--primary), 0 0 22px rgba(59, 130, 246, 0.08);
        }

        .nav-item .nav-bullet {
            width: 0.55rem;
            height: 0.55rem;
            border-radius: 999px;
            background: rgba(59, 130, 246, 0.7);
            box-shadow: 0 0 10px rgba(59, 130, 246, 0.5);
        }

        .command-shell {
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(10, 16, 29, 0.94));
            border: 1px solid var(--line);
            border-radius: 1.25rem;
            box-shadow: var(--shadow-soft);
            padding: 0.9rem 1rem;
            margin-bottom: 1rem;
        }

        .command-bar {
            display: grid;
            grid-template-columns: 1.2fr 4.2fr 1.1fr;
            gap: 1rem;
            align-items: center;
        }

        .brand-stack {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            min-width: 0;
        }

        .brand-stack .logo {
            width: 2.3rem;
            height: 2.3rem;
            border-radius: 0.8rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            font-weight: 900;
            box-shadow: 0 0 24px rgba(59, 130, 246, 0.25);
        }

        .brand-stack .name {
            font-size: 1.08rem;
            font-weight: 800;
            letter-spacing: -0.04em;
            color: var(--ink);
            white-space: nowrap;
        }

        .brand-stack .tag {
            color: var(--muted);
            font-size: 0.68rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            white-space: nowrap;
        }

        .search-wrap {
            position: relative;
        }

        .search-wrap .stTextInput > div > div > input {
            background: rgba(15, 23, 42, 0.94);
            border: 1px solid var(--line);
            border-radius: 0.9rem;
            color: var(--ink);
            min-height: 3rem;
            padding-left: 2.8rem;
        }

        .search-wrap .stTextInput > div > div > input::placeholder {
            color: var(--muted);
        }

        .search-wrap::before {
            content: "⌕";
            position: absolute;
            left: 1rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--muted);
            font-size: 1.15rem;
            z-index: 2;
        }

        .command-actions {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 0.85rem;
            flex-wrap: wrap;
        }

        .command-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.6rem;
            padding: 0.48rem 0.8rem;
            border-radius: 999px;
            border: 1px solid var(--line);
            background: rgba(15, 23, 42, 0.7);
            color: var(--ink);
            font-size: 0.8rem;
            font-weight: 700;
        }

        .command-bubble {
            width: 1.8rem;
            height: 1.8rem;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            font-weight: 800;
            font-size: 0.75rem;
        }

        .st-key-dashboard_hero {
            position: relative;
            left: 50%;
            width: min(1500px, calc(100vw - 48px));
            max-width: 1500px;
            box-sizing: border-box;
            transform: translateX(-50%);
            min-height: 380px;
            padding: 1.5rem 1.75rem;
            border-radius: 1.1rem;
            background: linear-gradient(145deg, #0B1020, #101827 72%, #0b1423);
            border: 1px solid rgba(59, 130, 246, 0.22);
            box-shadow: 0 18px 42px rgba(2, 6, 23, 0.38);
            margin-bottom: 1rem;
        }

        .st-key-dashboard_hero > div > div[data-testid="stHorizontalBlock"] {
            align-items: center;
            gap: 1.15rem;
        }

        .st-key-hero_analyze_document button,
        .st-key-hero_explore_architecture button {
            box-sizing: border-box;
            min-height: 48px;
            padding: 0.7rem 0.95rem !important;
            border-radius: 0.7rem !important;
            transition: background 160ms ease, border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
        }

        .st-key-hero_analyze_document button {
            border: 0 !important;
            background: linear-gradient(135deg, #3B82F6, #8B5CF6) !important;
            box-shadow: 0 8px 18px rgba(59, 130, 246, 0.22);
        }

        .st-key-hero_analyze_document button:hover,
        .st-key-hero_explore_architecture button:hover {
            transform: translateY(-1px);
        }

        .st-key-hero_analyze_document button:hover {
            box-shadow: 0 10px 22px rgba(59, 130, 246, 0.32);
        }

        .st-key-hero_explore_architecture button {
            border: 1px solid #243148 !important;
            background: rgba(16, 24, 39, 0.84) !important;
        }

        .st-key-hero_explore_architecture button:hover {
            border-color: rgba(59, 130, 246, 0.5) !important;
            background: #151E2F !important;
        }

        .st-key-hero_actions [data-testid="stHorizontalBlock"] {
            display: flex;
            flex-wrap: nowrap;
            align-items: center;
            justify-content: flex-start;
            gap: 0.75rem;
            width: max-content;
        }

        .st-key-hero_actions [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            flex: 0 0 auto !important;
            width: max-content !important;
            padding: 0 !important;
        }

        @media (max-width: 480px) {
            .st-key-hero_actions [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap;
            }
        }

        .hero-title [data-heading-text] {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
        }

        .st-key-dashboard_overview .subsection-head {
            margin-bottom: 0.25rem;
        }

        .st-key-dashboard_overview .status-strip {
            margin-top: 0;
            margin-bottom: 0;
        }

        .st-key-dashboard_hero [data-testid="stImage"] {
            position: relative;
            overflow: hidden;
            border-radius: 0.85rem;
            border: 1px solid rgba(56, 189, 248, 0.24);
            box-shadow: 0 0 34px rgba(59, 130, 246, 0.15), 0 0 26px rgba(34, 211, 238, 0.08);
            line-height: 0;
        }

        .st-key-dashboard_hero [data-testid="stImage"] img {
            display: block;
            width: 100%;
            height: auto;
            object-fit: contain;
            border-radius: 0.85rem;
        }

        .st-key-dashboard_hero [data-testid="stImage"]::after {
            content: "";
            position: absolute;
            inset: 0;
            border-radius: 0.85rem;
            background: linear-gradient(90deg, rgba(7, 11, 20, 0.18), transparent 34%, rgba(7, 11, 20, 0.05));
            pointer-events: none;
        }

        .hero-kicker {
            margin: 0 0 1rem;
            color: var(--cyan);
            font-size: 0.7rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            font-weight: 800;
        }

        .hero-title {
            margin: 0;
            font-size: clamp(2rem, 3vw, 3.1rem);
            line-height: 1.06;
            letter-spacing: -0.06em;
            color: var(--ink);
            max-width: 560px;
        }

        .hero-subtitle {
            margin: 1rem 0 0.75rem;
            color: var(--muted);
            max-width: 560px;
            font-size: 1rem;
            line-height: 1.55;
        }

        .status-strip {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 1rem;
            width: 100%;
            margin: 0.5rem 0 1.5rem;
        }

        .status-card {
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-width: 0;
            height: 128px;
            padding: 1.1rem 1.2rem;
            background: #101827;
            border: 1px solid var(--line);
            border-radius: 16px;
            box-shadow: var(--shadow-card);
            transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
        }

        .status-card:hover {
            border-color: rgba(59, 130, 246, 0.4);
            box-shadow: 0 14px 30px rgba(15, 23, 42, 0.32), 0 0 18px rgba(59, 130, 246, 0.08);
            transform: translateY(-1px);
        }

        .status-card .label {
            color: var(--muted);
            font-size: 0.7rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            display: block;
        }

        .status-card .value {
            color: var(--ink);
            font-size: 1.45rem;
            font-weight: 800;
            line-height: 1.15;
        }

        .status-card .document-value {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .status-card .caption {
            color: var(--muted);
            font-size: 0.76rem;
            line-height: 1.25;
        }

        @media (min-width: 768px) and (max-width: 1199px) {
            .status-strip { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        }

        @media (max-width: 767px) {
            .status-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.75rem; }
            .status-card { height: 120px; padding: 1rem; }
        }

        @media (max-width: 480px) {
            .status-strip { grid-template-columns: minmax(0, 1fr); }
        }

        .subsection-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 0.8rem;
        }

        .subsection-head h3 {
            margin: 0;
            font-size: 1.1rem;
            letter-spacing: -0.04em;
        }

        .subsection-head p {
            margin: 0;
            color: var(--muted);
            font-size: 0.8rem;
        }

        .workspace-grid {
            display: grid;
            grid-template-columns: 1.65fr 0.95fr;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .stack-card {
            background: linear-gradient(180deg, rgba(17, 24, 39, 0.9), rgba(9, 14, 24, 0.75));
            border: 1px solid var(--line);
            border-radius: 1rem;
            padding: 0.9rem;
        }

        .tiny-muted {
            color: var(--muted);
            font-size: 0.74rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }

        @media (max-width: 1180px) {
            .command-bar { grid-template-columns: 1fr; }
            .workspace-grid { grid-template-columns: 1fr; }
        }
        @media (max-width: 900px) {
            .st-key-dashboard_hero .hero-title { font-size: 1.7rem; }
        }

        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] p,
        [data-testid="stFileUploader"] label,
        [data-testid="stFileUploaderDropzone"] p,
        [data-testid="stFileUploaderDropzone"] span {
            color: var(--muted) !important;
        }

        [data-testid="stFileUploaderDropzone"] {
            background: var(--surface) !important;
            border: 1px dashed var(--line) !important;
            color: var(--ink) !important;
        }

        [data-testid="stFileUploaderDropzone"] button,
        [data-testid="stFileUploaderDropzone"] button[kind="secondary"] {
            background: var(--surface-elevated) !important;
            border: 1px solid var(--line) !important;
            color: var(--ink) !important;
        }

        input:not([type="checkbox"]):not([type="radio"]):not([type="file"]),
        textarea,
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stTimeInput"] input,
        [data-testid="stChatInput"] textarea,
        [data-baseweb="base-input"] {
            background-color: var(--input) !important;
            border-color: var(--line) !important;
            color: var(--ink) !important;
            caret-color: var(--ink);
        }

        input:not([type="checkbox"]):not([type="radio"]):not([type="file"])::placeholder,
        textarea::placeholder {
            color: var(--placeholder) !important;
            opacity: 1;
        }

        [data-testid="stTextInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus,
        [data-testid="stNumberInput"] input:focus,
        [data-testid="stDateInput"] input:focus,
        [data-testid="stTimeInput"] input:focus,
        [data-testid="stChatInput"] textarea:focus {
            border-color: var(--primary) !important;
            box-shadow: 0 0 0 1px var(--primary) !important;
        }

        [data-baseweb="select"] > div {
            background: var(--input) !important;
            border-color: var(--line) !important;
            color: var(--ink) !important;
        }

        [data-baseweb="select"] [data-testid="stMarkdownContainer"],
        [data-baseweb="select"] input,
        [data-baseweb="select"] div {
            color: var(--ink);
        }

        [data-baseweb="popover"] > div,
        [data-baseweb="menu"],
        ul[role="listbox"],
        [data-testid="stPopoverBody"],
        [data-testid="stExpander"] details,
        [data-testid="stExpander"] details summary,
        [data-testid="stDialog"] > div,
        div[role="dialog"] {
            background-color: var(--surface) !important;
            border-color: var(--line) !important;
            color: var(--ink) !important;
        }

        li[role="option"],
        [role="option"] {
            background-color: var(--surface) !important;
            color: var(--ink) !important;
        }

        li[role="option"]:hover,
        [role="option"]:hover {
            background-color: #17233A !important;
        }

        li[role="option"][aria-selected="true"],
        [role="option"][aria-selected="true"] {
            background-color: rgba(59, 130, 246, 0.2) !important;
        }

        [data-testid="stBaseButton-primary"],
        button[kind="primary"] {
            background: linear-gradient(90deg, #3B82F6, #8B5CF6) !important;
            border-color: transparent !important;
            color: #FFFFFF !important;
        }

        [data-testid="stBaseButton-secondary"],
        button[kind="secondary"] {
            background: var(--surface) !important;
            border-color: var(--line) !important;
            color: var(--ink) !important;
        }

        [data-testid="stBaseButton-tertiary"],
        button[kind="tertiary"] {
            color: var(--ink) !important;
        }

        [data-testid="stBaseButton-primary"]:hover,
        [data-testid="stBaseButton-secondary"]:hover,
        button[kind="primary"]:hover,
        button[kind="secondary"]:hover {
            box-shadow: 0 0 16px rgba(59, 130, 246, 0.18) !important;
            border-color: rgba(59, 130, 246, 0.55) !important;
        }

        input[type="checkbox"], input[type="radio"] {
            accent-color: var(--primary);
            color-scheme: dark;
        }

        [data-testid="stCheckbox"],
        [data-testid="stRadio"],
        [data-testid="stToggle"],
        [data-testid="stSlider"] {
            color: var(--ink);
        }

        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            background: transparent !important;
            border-bottom-color: var(--line) !important;
        }

        [data-testid="stTabs"] button[role="tab"] {
            background: transparent !important;
            color: var(--muted) !important;
        }

        [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            color: var(--ink) !important;
            border-bottom-color: var(--primary) !important;
        }

        [data-testid="stForm"],
        [data-testid="stMetric"],
        [data-testid="stDataFrame"],
        [data-testid="stDataEditor"],
        [data-testid="stChatMessage"] {
            background-color: var(--surface) !important;
            border-color: var(--line) !important;
            color: var(--ink) !important;
        }

        [data-testid="stMetricLabel"],
        [data-testid="stCaptionContainer"],
        [data-testid="stChatMessage"] p {
            color: var(--muted);
        }

        [data-testid="stDataFrame"] iframe,
        [data-testid="stDataEditor"] iframe {
            color-scheme: dark;
        }

        [data-testid="stAlert"] {
            background-color: var(--surface) !important;
            border-color: var(--line) !important;
            color: var(--ink) !important;
        }

        [data-testid="stStatusWidget"] {
            background-color: var(--surface) !important;
            border-color: var(--line) !important;
            color: var(--ink) !important;
        }

        [data-testid="stTooltipContent"] {
            background-color: var(--surface-elevated) !important;
            color: var(--ink) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_nav_rail(active_label: str = "Overview"):
    nav_items = [
        ("Overview", "◉"),
        ("Documents", "▣"),
        ("Grounded Q&A", "⌁"),
        ("Traceability", "⎇"),
        ("Architecture", "◌"),
        ("Compare Versions", "≣"),
        ("Review & Approvals", "✓"),
        ("Audit Logs", "◫"),
        ("Projects", "▤"),
        ("Settings", "⚙"),
    ]
    st.markdown('<div class="nav-rail">', unsafe_allow_html=True)
    for label, icon in nav_items:
        class_name = "nav-item active" if label == active_label else "nav-item"
        st.markdown(
            f'<div class="{class_name}"><span class="nav-bullet"></span><span>{icon}</span><span>{label}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)


def render_topbar(user_name: str, project_name: str, active_page: str = "Dashboard", project_options=None, on_logout=None):
    initials = (user_name or "A")[0].upper() if user_name else "A"
    visible_project_name = display_project_name(
        project_name, st.session_state.get("current_project_id")
    )
    primary_items = [
        ("Dashboard", "Dashboard"),
        ("Documents", "Documents"),
        ("Q&A", "Grounded Q&A"),
        ("Traceability", "Traceability"),
        ("Architecture", "Architecture"),
        ("Compare", "Compare Versions"),
    ]
    more_items = [
        ("Review & Approvals", "Review & Approvals", ":material/rate_review:"),
        ("Audit Logs", "Audit Logs", ":material/history:"),
        ("Projects", "Projects", ":material/folder_open:"),
        ("Settings", "Settings", ":material/settings:"),
    ]
    secondary_pages = {page for _, page, _ in more_items} | {"Exports"}
    active_primary_page = next(
        (page for _, page in primary_items if page == active_page), None
    )
    active_primary_key = (
        active_primary_page.replace(" ", "_").replace("&", "and")
        if active_primary_page
        else None
    )

    st.markdown(
        f"""
        <style>
        .st-key-autoarch_topbar {{
            position: sticky;
            top: 0;
            z-index: 999;
            box-sizing: border-box;
            width: 100vw;
            max-width: 100vw;
            margin-left: calc(50% - 50vw);
            background: rgba(7, 11, 20, 0.98);
            border-bottom: 1px solid #243148;
            box-shadow: 0 8px 24px rgba(2, 6, 23, 0.28);
            padding: 0.75rem clamp(0.75rem, 1.5vw, 1.5rem);
            margin-bottom: 0;
        }}
        .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] {{
            display: grid !important;
            grid-template-columns: max-content minmax(0, 1fr) max-content;
            flex-wrap: nowrap !important;
            align-items: center;
            column-gap: 36px;
        }}
        .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {{
            flex: none !important;
            width: auto !important;
            min-width: 0;
        }}
        .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) {{
            width: 100% !important;
        }}
        .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) [data-testid="stHorizontalBlock"] {{
            display: flex;
            flex-wrap: nowrap !important;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
            width: 100%;
            max-width: 100%;
        }}
        .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {{
            flex: 0 0 auto !important;
            width: max-content !important;
            min-width: max-content;
            padding: 0 !important;
        }}
        .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(3) [data-testid="stHorizontalBlock"] {{
            display: flex;
            flex-wrap: nowrap !important;
            align-items: center;
            justify-content: flex-end;
            gap: 18px;
            width: max-content;
        }}
        .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(3) [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {{
            flex: 0 0 auto !important;
            width: max-content !important;
            min-width: max-content;
            padding: 0 !important;
        }}
        .st-key-autoarch_topbar div[class*="st-key-primary_"] button,
        .st-key-autoarch_topbar div[class*="st-key-nav_more"] button {{
            width: max-content !important;
            min-width: max-content;
            max-width: none !important;
            min-height: 2.5rem;
            padding: 0.5rem 0.75rem;
            border: 0 !important;
            border-radius: 0.45rem;
            background: transparent !important;
            color: #94A3B8 !important;
            font-size: 0.95rem;
            font-weight: 650;
            white-space: nowrap;
            overflow: visible !important;
            text-overflow: clip !important;
            box-shadow: none;
        }}
        .st-key-autoarch_topbar div[class*="st-key-primary_"] button p,
        .st-key-autoarch_topbar div[class*="st-key-nav_more"] button p,
        .st-key-autoarch_topbar div[class*="st-key-top_logout"] button p,
        .st-key-hero_actions button p {{
            font-size: 0.95rem !important;
            font-weight: 650 !important;
            line-height: 1.2;
            white-space: nowrap;
            overflow: visible !important;
            text-overflow: clip !important;
        }}
        .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) [data-testid="stHorizontalBlock"] button p {{
            font-size: 0.95rem !important;
            font-weight: 650 !important;
            line-height: 1.2;
        }}
        .st-key-autoarch_topbar div[class*="st-key-primary_"] button:hover,
        .st-key-autoarch_topbar div[class*="st-key-nav_more"] button:hover {{
            color: #F8FAFC !important;
            background: rgba(59, 130, 246, 0.10) !important;
        }}
        .st-key-autoarch_topbar .st-key-primary_{active_primary_key or 'none'} button {{
            color: #93C5FD !important;
            background: rgba(59, 130, 246, 0.13) !important;
            box-shadow: inset 0 -2px #3B82F6 !important;
        }}
        .st-key-autoarch_topbar .st-key-nav_more_active button {{
            color: #93C5FD !important;
            background: rgba(59, 130, 246, 0.13) !important;
            box-shadow: inset 0 -2px #3B82F6 !important;
        }}
        .st-key-autoarch_topbar [data-testid="stPopover"] button {{
            white-space: nowrap;
        }}
        [data-testid="stPopoverBody"] {{
            background: #101827 !important;
            border: 1px solid #243148 !important;
            color: #F8FAFC !important;
        }}
        [data-testid="stPopoverBody"] div[class*="st-key-more_"] button {{
            width: 100%;
            justify-content: flex-start;
            min-width: 17rem;
            border: 0 !important;
            background: transparent !important;
            color: #CBD5E1 !important;
            text-align: left;
            font-size: 0.9rem;
            white-space: nowrap;
        }}
        [data-testid="stPopoverBody"] div[class*="st-key-more_"] button p {{
            white-space: nowrap;
            overflow: visible;
            text-overflow: clip;
        }}
        [data-testid="stPopoverBody"] div[class*="st-key-more_"] button:hover {{
            background: rgba(59, 130, 246, 0.12) !important;
            color: #F8FAFC !important;
        }}
        .st-key-autoarch_topbar [data-testid="stSelectbox"] {{
            min-width: 0;
        }}
        .st-key-autoarch_topbar [data-testid="stSelectbox"] > div > div {{
            min-height: 2.2rem;
            background: #101827;
            border-color: #243148;
        }}
        @media (min-width: 1101px) and (max-width: 1350px) {{
            .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] {{
                grid-template-columns: max-content minmax(0, 1fr) max-content;
                column-gap: 32px;
            }}
            .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) [data-testid="stHorizontalBlock"] {{
                gap: 18px;
            }}
            .st-key-autoarch_topbar div[class*="st-key-primary_"] button,
            .st-key-autoarch_topbar div[class*="st-key-nav_more"] button {{
                padding-left: 0.4rem;
                padding-right: 0.4rem;
                font-size: 0.9rem;
            }}
            .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) [data-testid="stHorizontalBlock"] button p {{
                font-size: 0.9rem !important;
            }}
            .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(3) [data-testid="stHorizontalBlock"] {{
                gap: 16px;
            }}
            .st-key-autoarch_topbar .st-key-top_project_selector {{
                width: 145px !important;
            }}
            .st-key-autoarch_topbar .st-key-top_project_selector [data-testid="stSelectbox"] {{
                width: 145px !important;
            }}
        }}
        @media (max-width: 1100px) {{
            .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] {{
                display: grid !important;
                grid-template-columns: minmax(0, 1fr) max-content;
                column-gap: 24px;
                row-gap: 0.3rem;
            }}
            .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(1) {{
                grid-column: 1;
                grid-row: 1;
                width: max-content !important;
            }}
            .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) {{
                grid-column: 1 / -1;
                grid-row: 2;
                width: auto !important;
            }}
            .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(3) {{
                grid-column: 2;
                grid-row: 1;
                width: auto !important;
            }}
            .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) [data-testid="stHorizontalBlock"] {{
                justify-content: center;
                gap: 24px;
            }}
        }}
        @media (max-width: 760px) {{
            .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] {{
                grid-template-columns: minmax(0, 42fr) minmax(0, 56fr);
            }}
            .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) [data-testid="stHorizontalBlock"] {{
                overflow-x: auto;
                flex-wrap: nowrap !important;
                justify-content: flex-start;
            }}
            .st-key-autoarch_topbar > div > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {{
                flex: 0 0 auto !important;
                width: max-content !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="autoarch_topbar"):
        brand_col, nav_col, controls_col = st.columns(
            [1.9, 7.8, 2.4], gap="small", vertical_alignment="center"
        )

        with brand_col:
            st.markdown(
                """
                <div style="display:flex;align-items:center;gap:0.55rem;min-height:2.5rem;white-space:nowrap;">
                    <span style="width:2rem;height:2rem;flex:0 0 2rem;border-radius:0.65rem;display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#3B82F6,#8B5CF6);color:#fff;font-weight:900;box-shadow:0 0 18px rgba(59,130,246,.25);">A</span>
                    <span style="display:flex;flex-direction:column;line-height:1.15;white-space:nowrap;">
                        <strong style="font-size:0.95rem;color:#F8FAFC;">AutoArch-AI</strong>
                        <small style="font-size:0.72rem;color:#94A3B8;">Architecture Intelligence</small>
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with nav_col:
            nav_cols = st.columns(
                [1.1, 1.15, 0.55, 1.35, 1.45, 0.7, 0.9], gap="small"
            )
            for index, (label, page_name) in enumerate(primary_items):
                with nav_cols[index]:
                    if st.button(
                        label,
                        key=f"primary_{page_name.replace(' ', '_').replace('&', 'and')}",
                        help=page_name,
                        width="content",
                        type="tertiary",
                    ):
                        st.session_state.active_page = page_name

            more_container_key = (
                "nav_more_active" if active_page in secondary_pages else "nav_more"
            )
            with nav_cols[6]:
                with st.container(key=more_container_key):
                    with st.popover("More ▾", key="top_more_menu", width="content"):
                        for label, page_name, icon in more_items:
                            if st.button(
                                label,
                                key=f"more_{page_name.replace(' ', '_').replace('&', 'and')}",
                                icon=icon,
                                use_container_width=True,
                                type="tertiary",
                            ):
                                st.session_state.active_page = page_name

        with controls_col:
            project_col, profile_col, logout_col = st.columns(
                [1.35, 0.75, 0.85], gap="small", vertical_alignment="center"
            )
            with project_col:
                if project_options:
                    project_choices = []
                    for option in project_options:
                        if isinstance(option, tuple):
                            project_name_label, project_id = option
                            project_choices.append(
                                (display_project_name(project_name_label, project_id), project_id)
                            )
                        else:
                            project_choices.append((display_project_name(option), option))

                    default_index = 0
                    for index, (label, project_id) in enumerate(project_choices):
                        if label == visible_project_name or project_id == st.session_state.get("current_project_id"):
                            default_index = index
                            break

                    selected = st.selectbox(
                        "Project",
                        options=[label for label, _ in project_choices],
                        index=default_index,
                        key="top_project_selector",
                        label_visibility="collapsed",
                        width=160,
                    )
                    selected_id = next((project_id for label, project_id in project_choices if label == selected), st.session_state.get("current_project_id"))
                    if selected_id != st.session_state.get("current_project_id"):
                        st.session_state.project_selector = selected_id
                        st.session_state.current_project_id = selected_id
                        st.session_state.document_info = None
                        st.session_state.document_ready = False
                        st.session_state.last_answer = None
                        st.session_state.comparison_result = None
                        st.session_state.active_page = st.session_state.get("active_page", "Dashboard")
                        st.rerun()
                else:
                    st.markdown(f"<div style='color:#F8FAFC;font-size:0.75rem;font-weight:700;'>{escape(visible_project_name)}</div>", unsafe_allow_html=True)

            with profile_col:
                with st.popover(
                    "Admin" if (user_name or "").lower() == "admin" else initials,
                    key="top_profile_menu",
                    icon=":material/account_circle:",
                    help=user_name,
                    width="content",
                ):
                    st.caption(user_name)

            with logout_col:
                if on_logout:
                    st.button(
                        "Logout",
                        key="top_logout",
                        help="Sign out",
                        width="content",
                        on_click=on_logout,
                        type="tertiary",
                    )


def render_status_strip(doc_info=None):
    get_value = getattr(doc_info, "get", lambda *_: None)
    filename = str(get_value("filename") or "Waiting")
    pages = get_value("pages")
    values = [
        ("Document", filename, f"{pages} pages" if pages is not None else "Selected project document", True),
        ("Pages", pages if pages is not None else "—", "Total document pages", False),
        ("Knowledge", get_value("chunks") if get_value("chunks") is not None else "—", "Indexed chunks", False),
        ("Entities", get_value("traceability_records") if get_value("traceability_records") is not None else "—", "Architecture entities", False),
        ("Relationships", get_value("relationship_records") if get_value("relationship_records") is not None else "—", "Extracted relationships", False),
    ]
    cards = []
    for label, value, caption, is_document in values:
        safe_value = escape(str(value))
        value_class = "value document-value" if is_document else "value"
        title = f' title="{escape(str(value), quote=True)}"' if is_document else ""
        cards.append(
            f"<article class='status-card'><span class='label'>{label}</span>"
            f"<span class='{value_class}'{title}>{safe_value}</span>"
            f"<span class='caption'>{escape(str(caption))}</span></article>"
        )
    st.markdown(f"<div class='status-strip'>{''.join(cards)}</div>", unsafe_allow_html=True)


def _navigate_to_page(page_name: str):
    st.session_state.active_page = page_name


def render_dashboard_hero():
    image_path = Path(__file__).resolve().parent.parent / "assets" / "image.png"
    with st.container(key="dashboard_hero"):
        copy_col, visual_col = st.columns([1.2, 1.0], gap="large", vertical_alignment="center")
        with copy_col:
            st.markdown(
                """
                <div class="hero-kicker">ACTIVE ARCHITECTURE WORKSPACE</div>
                <h1 class="hero-title"><span>From Documents to</span><span>Architecture Insights</span></h1>
                <p class="hero-subtitle">Analyze, trace and understand complex AUTOSAR architecture documents with grounded AI.</p>
                """,
                unsafe_allow_html=True,
            )
            with st.container(key="hero_actions"):
                action_col, explore_col = st.columns([1.2, 1.0], gap="small")
                with action_col:
                    st.button(
                        "+ Analyze Document",
                        key="hero_analyze_document",
                        type="primary",
                        width="content",
                        on_click=_navigate_to_page,
                        args=("Documents",),
                    )
                with explore_col:
                    st.button(
                        "Explore Architecture",
                        key="hero_explore_architecture",
                        type="secondary",
                        width="content",
                        on_click=_navigate_to_page,
                        args=("Architecture",),
                    )
        with visual_col:
            st.image(str(image_path), width="stretch")


def display_project_name(name, project_id=None):
    if str(name) == "AUTOSAR Demo":
        return f"Project {project_id}" if project_id is not None else "Current project"
    return str(name)
