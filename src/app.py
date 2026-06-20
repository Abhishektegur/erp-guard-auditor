import os
import tempfile
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
import networkx as nx

from engine import ERPAuditEngine
from visualizer import generate_risk_graph
from reporter import generate_pdf_report
from generator import generate_mock_data

# 1. Page Configuration & Typography Ingestion
st.set_page_config(
    page_title="ERP-Guard Compliance Dashboard",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Theme Toggle State
if "theme" not in st.session_state:
    st.session_state.theme = "dark"  # Default to premium dark mode

def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"

IS_DARK = st.session_state.theme == "dark"

# 3. CSS Premium Design System (Stripe/Vercel Aesthetic)
css_variables = f"""
:root {{
    --bg: {"#09090b" if IS_DARK else "#fafafa"};
    --bg-subtle: {"#121217" if IS_DARK else "#f4f4f5"};
    --card: {"#111115" if IS_DARK else "#ffffff"};
    --card-hover: {"#181822" if IS_DARK else "#f1f5f9"};
    --border: {"#27272a" if IS_DARK else "#e2e8f0"};
    --border-glowing: {"#3b82f6" if IS_DARK else "#1A365D"};
    --text: {"#f4f4f5" if IS_DARK else "#0f172a"};
    --text-muted: {"#a1a1aa" if IS_DARK else "#64748b"};
    --text-dim: {"#71717a" if IS_DARK else "#94a3b8"};
    --accent: #2563eb;
    --accent-glow: {"rgba(37,99,235,0.15)" if IS_DARK else "rgba(37,99,235,0.06)"};
    --green: {"#4ade80" if IS_DARK else "#16a34a"};
    --green-muted: {"rgba(74,222,128,0.12)" if IS_DARK else "rgba(22,163,74,0.08)"};
    --red: {"#f87171" if IS_DARK else "#dc2626"};
    --red-muted: {"rgba(248,113,113,0.12)" if IS_DARK else "rgba(220,38,38,0.08)"};
    --amber: {"#fbbf24" if IS_DARK else "#d97706"};
    --amber-muted: {"rgba(251,191,36,0.12)" if IS_DARK else "rgba(217,119,6,0.08)"};
    --radius: 12px;
}}
"""

st.markdown(f"<style>{css_variables}</style>", unsafe_allow_html=True)

st.markdown("""
<style>
/* Import Premium Font */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

header[data-testid="stHeader"] {
    display: none !important;
}
[data-testid="stSidebarCollapseButton"], [data-testid="collapsedControl"] {
    display: none !important;
}
[data-testid="stToolbar"] {
    display: none !important;
}
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .main, .block-container, section[data-testid="stMain"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.block-container {
    padding: 1.5rem 3rem 3rem !important;
    max-width: 1400px !important;
}
[data-testid="stHorizontalBlock"] { gap: 1.5rem !important; }

/* Premium Glassmorphic Card Styling */
.metric-card { 
    background: var(--card); 
    border: 1px solid var(--border); 
    border-radius: var(--radius); 
    padding: 1.5rem 1.6rem; 
    box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}
.metric-card:hover {
    border-color: var(--border-glowing);
    transform: translateY(-2px);
    box-shadow: 0 8px 30px -4px var(--accent-glow);
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; width: 4px; height: 100%;
    background: var(--border-glowing);
    opacity: 0;
    transition: opacity 0.3s ease;
}
.metric-card:hover::before {
    opacity: 1;
}

.metric-label { font-size: 0.78rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; }
.metric-value { font-size: 2.2rem; font-weight: 800; color: var(--text); letter-spacing: -0.04em; margin-top: 0.4rem; font-family: 'Plus Jakarta Sans', sans-serif; }
.metric-subtext { font-size: 0.76rem; color: var(--text-dim); margin-top: 0.45rem; font-weight: 500; }

/* Chart Container Cards */
.chart-wrap { 
    background: var(--card); 
    border: 1px solid var(--border); 
    border-radius: var(--radius); 
    padding: 1.5rem; 
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
}
.chart-title { font-size: 1rem; font-weight: 700; color: var(--text); letter-spacing: -0.02em; }
.chart-subtitle { font-size: 0.78rem; color: var(--text-dim); margin-bottom: 1.2rem; font-weight: 500; }

/* Custom Data Table Styling */
.data-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.8rem; margin-top: 10px; border-radius: 8px; overflow: hidden; border: 1px solid var(--border); }
.data-table th { text-align: left; padding: 0.8rem 1rem; color: var(--text-muted); font-weight: 700; font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.06em; border-bottom: 1px solid var(--border); background-color: var(--bg-subtle); }
.data-table td { padding: 0.8rem 1rem; color: var(--text); border-bottom: 1px solid var(--border-subtle); font-family: 'Plus Jakarta Sans', sans-serif; }
.data-table tr:hover { background-color: var(--bg-subtle); }
.data-table tr:last-child td { border-bottom: none; }

/* Status Badges */
.badge { display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; }
.badge-critical { color: var(--red); background: var(--red-muted); border: 1px solid rgba(248,113,113,0.2); }
.badge-high { color: var(--amber); background: var(--amber-muted); border: 1px solid rgba(251,191,36,0.2); }
.badge-medium { color: #3b82f6; background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.2); }

/* Premium Tab Navigation */
button[data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-muted) !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    padding: 0.65rem 1.25rem !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
    margin-right: 4px !important;
}
button[data-baseweb="tab"]:hover {
    color: var(--text) !important;
    background: var(--bg-subtle) !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--text) !important;
    background: var(--card) !important;
    border-color: var(--border) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {
    display: none !important;
}
[data-baseweb="tab-list"] {
    gap: 0px !important;
    background: var(--bg-subtle) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 4px !important;
}
</style>
""", unsafe_allow_html=True)

# 4. Helper Elements
def render_metric_card(label, value, subtext):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-subtext">{subtext}</div>
    </div>
    """, unsafe_allow_html=True)

# Plotly Theme Settings
PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Plus Jakarta Sans, sans-serif", color="#a1a1aa" if IS_DARK else "#64748b", size=11),
    margin=dict(l=0, r=0, t=10, b=0),
    xaxis=dict(
        gridcolor="rgba(255,255,255,0.03)" if IS_DARK else "rgba(0,0,0,0.03)",
        zerolinecolor="rgba(255,255,255,0.03)" if IS_DARK else "rgba(0,0,0,0.03)",
        tickfont=dict(size=10, color="#71717a"),
    ),
    yaxis=dict(
        gridcolor="rgba(255,255,255,0.03)" if IS_DARK else "rgba(0,0,0,0.03)",
        zerolinecolor="rgba(255,255,255,0.03)" if IS_DARK else "rgba(0,0,0,0.03)",
        tickfont=dict(size=10, color="#71717a"),
    ),
)

# 5. Header Section
head_left, head_right = st.columns([7, 1])
with head_left:
    st.markdown("""
    <div style='padding-bottom: 15px;'>
        <h1 style='margin: 0; font-size: 2.2rem; font-weight: 900; color: #3b82f6; letter-spacing: -0.04em;'>◆ ERP-GUARD</h1>
        <p style='margin: 5px 0 0 0; font-size: 0.85rem; color: var(--text-muted); font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase;'>AUTOMATED SEGREGATION OF DUTIES & COMPLIANCE AUDITING ENGINE</p>
    </div>
    """, unsafe_allow_html=True)
with head_right:
    theme_label = "☀️ Light" if IS_DARK else "🌙 Dark"
    st.button(theme_label, on_click=toggle_theme, use_container_width=True)

# Helper to auto-detect and read Excel sheets based on keywords
def auto_detect_excel(fobj):
    with pd.ExcelFile(fobj) as xl:
        sheet_names = xl.sheet_names
        
        rules = {
            "users": ["user", "assignment", "profile", "account", "login"],
            "permissions": ["perm", "entitlement", "tcode", "privilege", "authorization"],
            "transaction_logs": ["log", "tx", "trans", "ledger", "journal", "activity"],
            "hr_database": ["hr", "employee", "roster", "active_dir", "personnel", "active directory"]
        }
        
        detected = {}
        logs = []
        
        for std_name, keywords in rules.items():
            matched = None
            for sheet in sheet_names:
                sheet_lower = sheet.lower().strip()
                if any(k in sheet_lower for k in keywords):
                    matched = sheet
                    break
            
            if matched:
                try:
                    df = xl.parse(matched)
                    detected[std_name] = df
                    logs.append(f"✅ Auto-detected **'{std_name}'** in sheet **'{matched}'**")
                except Exception as e:
                    logs.append(f"❌ Failed to parse sheet **'{matched}'**: {e}")
            else:
                logs.append(f"❌ Could not find sheet for **'{std_name}'**")
                
        return detected, logs

# Helper to auto-detect and read files inside a ZIP archive based on keywords
def auto_detect_zip(fobj):
    import zipfile
    detected = {}
    logs = []
    
    rules = {
        "users": ["user", "assignment", "profile", "account", "login"],
        "permissions": ["perm", "entitlement", "tcode", "privilege", "authorization"],
        "transaction_logs": ["log", "tx", "trans", "ledger", "journal", "activity"],
        "hr_database": ["hr", "employee", "roster", "active_dir", "personnel", "active directory"]
    }
    
    try:
        with zipfile.ZipFile(fobj) as z:
            namelist = z.namelist()
            # Filter out hidden files and directory structure descriptors
            clean_names = [n for n in namelist if not n.startswith('__MACOSX') and not os.path.basename(n).startswith('.')]
            
            for std_name, keywords in rules.items():
                matched_file = None
                for name in clean_names:
                    name_lower = name.lower()
                    if any(k in name_lower for k in keywords) and (name_lower.endswith('.csv') or name_lower.endswith('.xlsx') or name_lower.endswith('.xls')):
                        matched_file = name
                        break
                
                if matched_file:
                    try:
                        with z.open(matched_file) as f:
                            if matched_file.lower().endswith('.csv'):
                                df = pd.read_csv(f)
                            else:
                                df = pd.read_excel(f, engine="openpyxl")
                            detected[std_name] = df
                            logs.append(f"✅ Auto-detected **'{std_name}'** in archive file **'{matched_file}'**")
                    except Exception as e:
                        logs.append(f"❌ Failed to parse **'{matched_file}'** inside archive: {e}")
                else:
                    logs.append(f"❌ Could not find file for **'{std_name}'** in archive")
    except Exception as e:
        logs.append(f"❌ Failed to read ZIP archive: {e}")
        
    return detected, logs

# 6. Sidebar Controls & File Uploads
st.sidebar.markdown("### 📥 Ingestion Controls")
use_mock = st.sidebar.checkbox("Use Built-in Mock Audit Data", value=True)

# Temporary directory handling for reports output
temp_dir = tempfile.mkdtemp()
data_dir = temp_dir

# Ingestion state variables
uploaded_file = None
detected_dfs = None
file_logs = []

if not use_mock:
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### Option 1: Upload Excel Workbook or ZIP Archive")
    uploaded_file = st.sidebar.file_uploader("Upload Excel (.xlsx) or ZIP (.zip)", type=["xlsx", "zip"])
    
    if uploaded_file is not None:
        if uploaded_file.name.lower().endswith(".zip"):
            detected_dfs, file_logs = auto_detect_zip(uploaded_file)
            st.sidebar.markdown("##### ZIP Ingestion Status")
        else:
            detected_dfs, file_logs = auto_detect_excel(uploaded_file)
            st.sidebar.markdown("##### Sheet Detection Status")
            
        for log in file_logs:
            st.sidebar.markdown(log)
            
        # Verify required tables are found
        missing = [k for k in ["users", "permissions", "transaction_logs", "hr_database"] if k not in detected_dfs]
        if missing:
            st.sidebar.error(f"Missing required datasets: {missing}")
            st.error("Uploaded archive/workbook is missing required datasets. Please review Ingestion logs in the sidebar.")
            st.stop()
            
    else:
        st.sidebar.markdown("---")
        st.sidebar.markdown("#### Option 2: Upload CSV files")
        user_file = st.sidebar.file_uploader("users.csv", type="csv")
        perm_file = st.sidebar.file_uploader("permissions.csv", type="csv")
        log_file = st.sidebar.file_uploader("transaction_logs.csv", type="csv")
        hr_file = st.sidebar.file_uploader("hr_database.csv", type="csv")
        
        # Build dictionary of uploaded CSV files
        csv_dfs = {}
        for key, fobj in [("users", user_file), ("permissions", perm_file), 
                         ("transaction_logs", log_file), ("hr_database", hr_file)]:
            if fobj is not None:
                csv_dfs[key] = pd.read_csv(fobj)
            else:
                # Copy mock baseline if missing
                src_mock = os.path.join("./data", f"{key}.csv")
                if os.path.exists(src_mock):
                    csv_dfs[key] = pd.read_csv(src_mock)
                else:
                    st.sidebar.error(f"Missing baseline data: {key}.csv")
                    st.stop()
                    
        detected_dfs = csv_dfs

# Make sure baseline mock exists in default folder
if not os.path.exists("./data/users.csv"):
    generate_mock_data("./data")

# Initialize Engine
if use_mock:
    @st.cache_data
    def run_audits_mock():
        engine = ERPAuditEngine("./config/sod_rules.json", "./data")
        violations = engine.run_all_audits()
        return engine, violations
    engine, violations_df = run_audits_mock()
    data_dir = "./data"  # write reports directly to data folder for mock runs
else:
    # Custom run (no cache, runs in-memory dataframes)
    try:
        engine = ERPAuditEngine("./config/sod_rules.json", dataframes=detected_dfs)
        violations_df = engine.run_all_audits()
    except Exception as e:
        st.error(f"Failed to execute audit engine: {e}")
        st.stop()

# Generate static visual network image (needed for PDF generation)
graph_path = os.path.join(data_dir, "risk_network.png")
generate_risk_graph(engine, graph_path)

# Report Generation Trigger
st.sidebar.markdown("---")
st.sidebar.markdown("### 📄 Export PDF Deliverable")
if st.sidebar.button("Build Formal Audit Report", use_container_width=True):
    pdf_path = os.path.join(data_dir, "audit_report.pdf")
    generate_pdf_report(engine, violations_df, graph_path, pdf_path)
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            st.sidebar.download_button(
                label="⬇️ Download PDF Report",
                data=f.read(),
                file_name="ERP_Guard_Compliance_Report.pdf",
                mime="application/pdf",
                use_container_width=True
            )

# 7. KPI Scorecards Dashboard
total_txs = len(engine.logs_df)
total_violations = len(violations_df)
unique_violators = violations_df["user_id"].nunique() if total_violations > 0 else 0
critical_count = len(violations_df[violations_df["risk_level"] == "CRITICAL"]) if total_violations > 0 else 0
high_count = len(violations_df[violations_df["risk_level"] == "HIGH"]) if total_violations > 0 else 0

c1, c2, c3, c4 = st.columns(4)
with c1:
    render_metric_card("Total Logs Audited", f"{total_txs:,}", "Chronological ERP transaction rows")
with c2:
    render_metric_card("Compliance Violations", str(total_violations), "Active alerts requiring mitigation")
with c3:
    render_metric_card("Unique Account Risks", str(unique_violators), "Individual user profiles flagged")
with c4:
    render_metric_card("Critical Risks", str(critical_count), "High-severity exceptions identified")

st.markdown("<div style='margin-bottom:15px;'></div>", unsafe_allow_html=True)

# 8. Interactive Plotly Graph Generator (Modern & Interactive replacement for matplotlib)
def get_interactive_risk_graph(engine):
    user_perms = engine.get_user_permissions()
    static_violations = engine.audit_static_entitlements()
    
    violating_users = set()
    conflicting_perms = set()
    
    if not static_violations.empty:
        violating_users = set(static_violations["user_id"].tolist())
        conflicts = engine.rules.get("conflicting_permission_pairs", [])
        for c in conflicts:
            conflicting_perms.add(c["permission_a"])
            conflicting_perms.add(c["permission_b"])
            
    # Build Bipartite Graph
    G = nx.Graph()
    user_nodes = []
    perm_nodes = []
    
    for _, row in user_perms.iterrows():
        user_id = row["user_id"]
        if user_id not in violating_users:
            continue
        user_nodes.append(user_id)
        G.add_node(user_id, type="user", department=row["department"], name=row["name"])
        for perm in row["permission"]:
            if perm in conflicting_perms:
                if perm not in perm_nodes:
                    perm_nodes.append(perm)
                    G.add_node(perm, type="permission")
                G.add_edge(user_id, perm)

    if len(G.nodes) == 0:
        return None

    # Compute bipartite positions
    pos = {}
    user_nodes.sort()
    perm_nodes.sort()
    
    # Scale Y spacing based on node count to keep clean spacing
    user_gap = 1.0 if len(user_nodes) <= 1 else 4.0 / (len(user_nodes) - 1)
    perm_gap = 1.0 if len(perm_nodes) <= 1 else 4.0 / (len(perm_nodes) - 1)
    
    for i, u in enumerate(user_nodes):
        pos[u] = (-1.0, 2.0 - i * user_gap)
    for i, p in enumerate(perm_nodes):
        pos[p] = (1.0, 2.0 - i * perm_gap)

    # Create Edges trace
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1.5, color='rgba(156, 163, 175, 0.4)'),
        hoverinfo='none',
        mode='lines'
    )

    # Create Nodes trace
    node_x = []
    node_y = []
    node_color = []
    node_text = []
    node_size = []
    text_position = []
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        
        # Color & Info styling
        if G.nodes[node]["type"] == "user":
            node_color.append("#ef4444")  # Premium Red
            node_size.append(24)
            text_position.append("middle left")
            node_text.append(f"👤 User Profile: {node}<br>Name: {G.nodes[node]['name']}<br>Dept: {G.nodes[node]['department']}")
        else:
            node_color.append("#f59e0b")  # Premium Gold/Amber
            node_size.append(28)
            text_position.append("middle right")
            node_text.append(f"🔑 Core Permission: {node}<br>Status: Critical SoD Component")

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=[n for n in G.nodes()],
        textposition=text_position,
        hovertext=node_text,
        marker=dict(
            showscale=False,
            color=node_color,
            size=node_size,
            line=dict(width=1.5, color='#ffffff' if not IS_DARK else '#09090b')
        ),
        textfont=dict(
            family="Plus Jakarta Sans, sans-serif",
            size=10,
            color="#0f172a" if not IS_DARK else "#f4f4f5",
        )
    )

    fig = go.Figure(data=[edge_trace, node_trace],
                 layout=go.Layout(
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=0,l=20,r=20,t=0),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-1.8, 1.8]),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-2.5, 2.5]),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                 ))
    return fig

# 9. Navigation Tabs
tab_dash, tab_findings, tab_ai = st.tabs(["📊 Analytics Dashboard", "📋 Detailed Audit Findings", "🤖 Gemini AI Auditor"])

# --- TAB 1: DASHBOARD ---
with tab_dash:
    col_l, col_r = st.columns([1, 1])
    
    with col_l:
        st.markdown("""
        <div class="chart-wrap">
            <div class="chart-title">Violations by Risk Level</div>
            <div class="chart-subtitle">Breakdown of compliance exceptions by risk severity</div>
        """, unsafe_allow_html=True)
        if total_violations > 0:
            fig_pie = px.pie(
                violations_df, 
                names="risk_level",
                color="risk_level",
                color_discrete_map={"CRITICAL": "#ef4444", "HIGH": "#f59e0b", "MEDIUM": "#3b82f6"},
                hole=0.55
            )
            fig_pie.update_layout(**PLOT_LAYOUT, showlegend=True)
            st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})
        else:
            st.write("No violations detected.")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_r:
        st.markdown("""
        <div class="chart-wrap">
            <div class="chart-title">Exceptions by Violation Category</div>
            <div class="chart-subtitle">Frequency of exceptions identified across control points</div>
        """, unsafe_allow_html=True)
        if total_violations > 0:
            type_counts = violations_df["violation_type"].value_counts().reset_index()
            type_counts.columns = ["violation_type", "count"]
            type_counts["violation_type"] = type_counts["violation_type"].str.replace("_", " ")
            
            fig_bar = px.bar(
                type_counts, 
                x="count", 
                y="violation_type", 
                orientation="h",
                color_discrete_sequence=["#3b82f6"]
            )
            fig_bar.update_layout(**PLOT_LAYOUT)
            st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
        else:
            st.write("No violations detected.")
        st.markdown("</div>", unsafe_allow_html=True)
        
    # Interactive Bipartite graph rendering
    st.markdown("""
    <div class="chart-wrap">
        <div class="chart-title">Access Conflict Matrix (Interactive Graph)</div>
        <div class="chart-subtitle">Hover over nodes to inspect users (red) and their conflicting system permissions (gold). Drag or scroll to zoom.</div>
    """, unsafe_allow_html=True)
    plotly_graph = get_interactive_risk_graph(engine)
    if plotly_graph is not None:
        st.plotly_chart(plotly_graph, use_container_width=True, config={"displayModeBar": False})
    else:
        st.write("No static violations graph generated.")
    st.markdown("</div>", unsafe_allow_html=True)

# --- TAB 2: DETAILED FINDINGS ---
with tab_findings:
    sub_tabs = ["Static SoD", "Transactional Crossovers", "Account Integrity", "Split PO Limit Bypasses", "Dept Whitelist"]
    sub_sel = st.selectbox("Select Audit Module:", sub_tabs)
    
    if sub_sel == "Static SoD":
        df = violations_df[violations_df["violation_type"] == "STATIC_SOD"]
        st.markdown("### Static Entitlement Violations")
        st.markdown("Checks user authorization assignments. These users possess roles that combine conflicting permissions.")
        
        if df.empty:
            st.info("No static SoD conflicts detected.")
        else:
            rows = ""
            for _, r in df.iterrows():
                badge_cls = "badge-critical" if r["risk_level"] == "CRITICAL" else "badge-high"
                rows += f"""
                <tr>
                    <td><b>{r['user_id']}</b></td>
                    <td>{r['user_name']}</td>
                    <td>{r['department']}</td>
                    <td>{r['conflict_name']}</td>
                    <td><span class="badge {badge_cls}">{r['risk_level']}</span></td>
                    <td>{r['details']}</td>
                </tr>
                """
            st.markdown(f"""
            <table class="data-table">
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th>Name</th>
                        <th>Department</th>
                        <th>Conflict Name</th>
                        <th>Risk Level</th>
                        <th>Audit Details</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            """, unsafe_allow_html=True)
            
    elif sub_sel == "Transactional Crossovers":
        df = violations_df[violations_df["violation_type"].isin(["TRANSACTION_CYCLE_VIOLATION", "TRANSACTION_SOD_CROSSOVER"])]
        st.markdown("### Transactional Exception Crossovers")
        st.markdown("Audits transaction logs for users executing conflicting operations (e.g. creating and paying a vendor).")
        
        if df.empty:
            st.info("No transactional exception crossovers detected.")
        else:
            rows = ""
            for _, r in df.iterrows():
                badge_cls = "badge-critical" if r["risk_level"] == "CRITICAL" else "badge-high"
                rows += f"""
                <tr>
                    <td><b>{r['user_id']}</b></td>
                    <td>{r['user_name']}</td>
                    <td>{r['violation_type'].replace('_', ' ')}</td>
                    <td><span class="badge {badge_cls}">{r['risk_level']}</span></td>
                    <td>{r['details']}</td>
                </tr>
                """
            st.markdown(f"""
            <table class="data-table">
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th>Name</th>
                        <th>Incident Type</th>
                        <th>Risk Level</th>
                        <th>Audit Details</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            """, unsafe_allow_html=True)
            
    elif sub_sel == "Account Integrity":
        df = violations_df[violations_df["violation_type"].isin(["GHOST_ACCOUNT_ACTIVITY", "TERMINATED_USER_ACTIVITY"])]
        st.markdown("### Account Integrity & Ghost User Audit")
        st.markdown("Traces actions logged under unregistered accounts or employees who have left the company.")
        
        if df.empty:
            st.info("No account integrity violations detected.")
        else:
            rows = ""
            for _, r in df.iterrows():
                rows += f"""
                <tr>
                    <td><b>{r['user_id']}</b></td>
                    <td>{r['user_name']}</td>
                    <td>{r['department']}</td>
                    <td><span class="badge badge-critical">CRITICAL</span></td>
                    <td>{r['details']}</td>
                </tr>
                """
            st.markdown(f"""
            <table class="data-table">
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th>Name</th>
                        <th>Department</th>
                        <th>Risk Level</th>
                        <th>Audit Details</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            """, unsafe_allow_html=True)
            
    elif sub_sel == "Split PO Limit Bypasses":
        df = violations_df[violations_df["violation_type"] == "SPLIT_TRANSACTION_LIMIT_AVOIDANCE"]
        st.markdown("### Purchase Order Splitting Detections")
        st.markdown("Detects user patterns splitting purchase order amounts below threshold limits to avoid approvals.")
        
        if df.empty:
            st.info("No split transaction bypasses detected.")
        else:
            rows = ""
            for _, r in df.iterrows():
                rows += f"""
                <tr>
                    <td><b>{r['user_id']}</b></td>
                    <td>{r['user_name']}</td>
                    <td>{r['department']}</td>
                    <td><span class="badge badge-high">HIGH</span></td>
                    <td>{r['details']}</td>
                </tr>
                """
            st.markdown(f"""
            <table class="data-table">
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th>Name</th>
                        <th>Department</th>
                        <th>Risk Level</th>
                        <th>Audit Details</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            """, unsafe_allow_html=True)
            
    elif sub_sel == "Dept Whitelist":
        df = violations_df[violations_df["violation_type"] == "DEPARTMENT_RESTRICTION_VIOLATION"]
        st.markdown("### Department Restriction Exceptions")
        st.markdown("Checks if users hold technical privileges assigned outside their active department whitelists.")
        
        if df.empty:
            st.info("No department restriction exceptions detected.")
        else:
            rows = ""
            for _, r in df.iterrows():
                rows += f"""
                <tr>
                    <td><b>{r['user_id']}</b></td>
                    <td>{r['user_name']}</td>
                    <td>{r['department']}</td>
                    <td><span class="badge badge-high">HIGH</span></td>
                    <td>{r['details']}</td>
                </tr>
                """
            st.markdown(f"""
            <table class="data-table">
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th>Name</th>
                        <th>Department</th>
                        <th>Risk Level</th>
                        <th>Audit Details</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            """, unsafe_allow_html=True)

# --- TAB 3: GEMINI AI CHAT ASSISTANT ---
with tab_ai:
    st.markdown("### 🤖 Gemini AI Audit Assistant")
    st.markdown("Interact with the Gemini model to analyze, summarize, and resolve findings in natural language.")
    
    # API Key Configuration
    api_key_source = st.sidebar.text_input("Gemini API Key:", type="password", help="Enter your Google AI Studio API key to enable chat capabilities.")
    
    # Initialize Chat History
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Handle Input Question
    user_prompt = st.chat_input("Ask a question about the audit findings (e.g. 'Summarize critical risks')")
    
    if user_prompt:
        # Check API Key
        api_key = api_key_source or os.environ.get("GEMINI_API_KEY")
        
        with st.chat_message("user"):
            st.markdown(user_prompt)
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        
        if not api_key:
            with st.chat_message("assistant"):
                st.warning("⚠️ Chat interface requires a Gemini API Key. Please enter your key in the sidebar text input.")
        else:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.markdown("*Auditing dataset...*")
                
                try:
                    # Configure API
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    # Prepare Context Data
                    findings_summary = ""
                    if not violations_df.empty:
                        findings_summary = violations_df[["violation_type", "user_id", "user_name", "risk_level", "details"]].to_string()
                    else:
                        findings_summary = "No violations detected."
                        
                    context_prompt = f"""
                    You are ERP-Guard AI Auditor, a professional compliance audit assistant.
                    Your goal is to answer user queries accurately based on the audit findings provided below.
                    
                    AUDIT REPORT SUMMARY STATISTICS:
                    - Total Logs Audited: {total_txs}
                    - Unique Account Risks: {unique_violators}
                    - Total Exception Violations: {total_violations}
                    - Critical Severity Exceptions: {critical_count}
                    - High Severity Exceptions: {high_count}
                    
                    DETAILED FINDINGS (CSV FORMAT):
                    {findings_summary}
                    
                    CONVERSATION HISTORY:
                    {str(st.session_state.messages[:-1])}
                    
                    USER QUERY:
                    {user_prompt}
                    
                    Answer clearly, using professional internal-audit formatting. Bold key terms. Map out explanations logically.
                    """
                    
                    # Call Gemini with streaming
                    response = model.generate_content(context_prompt, stream=True)
                    full_response = ""
                    for chunk in response:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")
                    message_placeholder.markdown(full_response)
                    
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    
                except Exception as ex:
                    message_placeholder.markdown(f"❌ Gemini API Error: {ex}")
