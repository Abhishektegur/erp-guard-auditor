import os
import tempfile
import pandas as pd
import streamlit as st
import plotly.express as px
import google.generativeai as genai

from engine import ERPAuditEngine
from visualizer import generate_risk_graph
from reporter import generate_pdf_report
from generator import generate_mock_data

# 1. Page Configuration
st.set_page_config(
    page_title="ERP-Guard Dashboard",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Theme Toggle State
if "theme" not in st.session_state:
    st.session_state.theme = "light"

def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"

IS_DARK = st.session_state.theme == "dark"

# 3. CSS Design System Injection
css_variables = f"""
:root {{
    --bg: {"#09090b" if IS_DARK else "#ffffff"};
    --bg-subtle: {"#0c0c0f" if IS_DARK else "#f9fafb"};
    --card: {"#0c0c0f" if IS_DARK else "#ffffff"};
    --card-hover: {"#131316" if IS_DARK else "#f4f4f5"};
    --border: {"#1e1e24" if IS_DARK else "#e4e4e7"};
    --border-subtle: {"#16161a" if IS_DARK else "#f0f0f2"};
    --text: {"#fafafa" if IS_DARK else "#09090b"};
    --text-muted: #71717a;
    --text-dim: {"#52525b" if IS_DARK else "#a1a1aa"};
    --accent: #1A365D;
    --accent-muted: #2B6CB0;
    --green: {"#22c55e" if IS_DARK else "#16a34a"};
    --green-muted: {"rgba(34,197,94,0.12)" if IS_DARK else "rgba(22,163,74,0.08)"};
    --red: {"#ef4444" if IS_DARK else "#dc2626"};
    --red-muted: {"rgba(239,68,68,0.12)" if IS_DARK else "rgba(220,38,38,0.08)"};
    --amber: {"#f59e0b" if IS_DARK else "#d97706"};
    --amber-muted: {"rgba(245,158,11,0.12)" if IS_DARK else "rgba(217,119,6,0.08)"};
    --radius: 10px;
}}
"""

st.markdown(f"<style>{css_variables}</style>", unsafe_allow_html=True)

# Custom Style Rules
st.markdown("""
<style>
header[data-testid="stHeader"], [data-testid="stToolbar"] {
    display: none !important;
}
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .main, .block-container, section[data-testid="stMain"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', -apple-system, sans-serif !important;
}
.block-container {
    padding: 1.5rem 2.5rem 3rem !important;
    max-width: 1360px !important;
}
[data-testid="stHorizontalBlock"] { gap: 1.25rem !important; }

/* Metric Card Layout */
.metric-card { 
    background: var(--card); 
    border: 1px solid var(--border); 
    border-radius: var(--radius); 
    padding: 1.25rem 1.4rem; 
    margin-bottom: 1rem;
}
.metric-label { font-size: 0.8rem; color: var(--text-muted); font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
.metric-value { font-size: 1.85rem; font-weight: 700; color: var(--text); letter-spacing: -0.03em; margin-top: 0.25rem; }
.metric-subtext { font-size: 0.75rem; color: var(--text-dim); margin-top: 0.4rem; }

/* Chart and Containers */
.chart-wrap { 
    background: var(--card); 
    border: 1px solid var(--border); 
    border-radius: var(--radius); 
    padding: 1.2rem; 
    margin-bottom: 1.25rem;
}
.chart-title { font-size: 0.95rem; font-weight: 600; color: var(--text); }
.chart-subtitle { font-size: 0.78rem; color: var(--text-dim); margin-bottom: 0.8rem; }

/* Custom Data Table Styling */
.data-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.8rem; margin-top: 10px; }
.data-table th { text-align: left; padding: 0.75rem 0.8rem; color: var(--text-muted); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid var(--border); background-color: var(--bg-subtle); }
.data-table td { padding: 0.7rem 0.8rem; color: var(--text); border-bottom: 1px solid var(--border-subtle); }
.data-table tr:last-child td { border-bottom: none; }

/* Status Badges */
.badge { display: inline-block; padding: 2px 9px; border-radius: 6px; font-size: 0.72rem; font-weight: 600; }
.badge-critical { color: var(--red); background: var(--red-muted); }
.badge-high { color: var(--amber); background: var(--amber-muted); }
.badge-medium { color: #2B6CB0; background: rgba(43,108,176,0.1); }
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
    font=dict(family="DM Sans, sans-serif", color="#71717a" if not IS_DARK else "#a1a1aa", size=11),
    margin=dict(l=0, r=0, t=10, b=0),
    xaxis=dict(
        gridcolor="rgba(0,0,0,0.04)" if not IS_DARK else "rgba(255,255,255,0.04)",
        zerolinecolor="rgba(0,0,0,0.04)" if not IS_DARK else "rgba(255,255,255,0.04)",
        tickfont=dict(size=10, color="#71717a"),
    ),
    yaxis=dict(
        gridcolor="rgba(0,0,0,0.04)" if not IS_DARK else "rgba(255,255,255,0.04)",
        zerolinecolor="rgba(0,0,0,0.04)" if not IS_DARK else "rgba(255,255,255,0.04)",
        tickfont=dict(size=10, color="#71717a"),
    ),
)

# 5. Header Section
head_left, head_right = st.columns([7, 1])
with head_left:
    st.markdown("""
    <div style='padding-bottom: 10px;'>
        <h1 style='margin: 0; font-size: 2rem; font-weight: 800; color: #1A365D;'>◆ ERP-GUARD</h1>
        <p style='margin: 0; font-size: 0.85rem; color: var(--text-muted); font-weight: 500;'>AUTOMATED SEGREGATION OF DUTIES & COMPLIANCE AUDITING ENGINE</p>
    </div>
    """, unsafe_allow_html=True)
with head_right:
    theme_label = "☀️ Light" if IS_DARK else "🌙 Dark"
    st.button(theme_label, on_click=toggle_theme, use_container_width=True)

# 6. Sidebar Controls & File Uploads
st.sidebar.markdown("### 📥 Ingestion Controls")
use_mock = st.sidebar.checkbox("Use Built-in Mock Audit Data", value=True)

# Temporary directory handling for uploads
data_dir = "./data"
if not use_mock:
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### Upload custom ERP sheets")
    user_file = st.sidebar.file_uploader("users.csv", type="csv")
    perm_file = st.sidebar.file_uploader("permissions.csv", type="csv")
    log_file = st.sidebar.file_uploader("transaction_logs.csv", type="csv")
    hr_file = st.sidebar.file_uploader("hr_database.csv", type="csv")
    
    # Save uploaded files to temp folder
    temp_dir = tempfile.mkdtemp()
    data_dir = temp_dir
    
    # Check if files uploaded, otherwise fallback to copies of mock
    for fn, fobj in [("users.csv", user_file), ("permissions.csv", perm_file), 
                     ("transaction_logs.csv", log_file), ("hr_database.csv", hr_file)]:
        dest = os.path.join(data_dir, fn)
        if fobj is not None:
            with open(dest, "wb") as f:
                f.write(fobj.getbuffer())
        else:
            # Fallback copy
            src_mock = os.path.join("./data", fn)
            if os.path.exists(src_mock):
                pd.read_csv(src_mock).to_csv(dest, index=False)

# Make sure baseline mock exists in default folder
if not os.path.exists("./data/users.csv"):
    generate_mock_data("./data")

# Initialize Engine
@st.cache_data
def run_audits_cached(dir_path):
    engine = ERPAuditEngine("./config/sod_rules.json", dir_path)
    violations = engine.run_all_audits()
    return engine, violations

try:
    engine, violations_df = run_audits_cached(data_dir)
except Exception as e:
    st.error(f"Failed to execute audit engine: {e}")
    st.stop()

# Generate visual network image
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
    render_metric_card("Total Logs Audited", f"{total_txs:,}", "Chronological Transaction rows")
with c2:
    render_metric_card("Compliance Violations", str(total_violations), "Identified exceptions")
with c3:
    render_metric_card("Unique Account Risks", str(unique_violators), "User accounts requiring review")
with c4:
    render_metric_card("Critical Risks (Red)", str(critical_count), "Requires immediate mitigation")

st.markdown("<div style='margin-bottom:15px;'></div>", unsafe_allow_html=True)

# 8. Navigation Tabs
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
                color_discrete_map={"CRITICAL": "#dc2626", "HIGH": "#d97706", "MEDIUM": "#2b6cb0"},
                hole=0.45
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
                color_discrete_sequence=["#2B6CB0"]
            )
            fig_bar.update_layout(**PLOT_LAYOUT)
            st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
        else:
            st.write("No violations detected.")
        st.markdown("</div>", unsafe_allow_html=True)
        
    # Bipartite graph rendering
    st.markdown("""
    <div class="chart-wrap">
        <div class="chart-title">Static Entitlement Conflict Map</div>
        <div class="chart-subtitle">Bipartite relationships between violating users (red) and conflicting permissions (orange)</div>
    """, unsafe_allow_html=True)
    if os.path.exists(graph_path):
        st.image(graph_path, use_container_width=True)
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
