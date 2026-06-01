# app.py — Instagram Influencer Audit Agent UI
# Supports two modes: Screenshot Audit (Gemini multimodal) and Auto Scraper (legacy)

import streamlit as st
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()  # load .env (GOOGLE_API_KEY, etc.) into environment

from datetime import datetime
from services.report_generator import ReportGeneratorService, BENCHMARK_MODELS
from services.storage_manager import StorageManager
from database.models import Session, Influencer, AuditRun, NormalizedMetrics
from services.normalizer import MetricsNormalizer

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Influencer Audit Agent",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS — dark premium theme ───────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Global reset ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Dark background ── */
.stApp {
    background: linear-gradient(135deg, #0d0d1a 0%, #111827 60%, #0d1f2d 100%);
    min-height: 100vh;
}

/* ── Hide default Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── Hero header ── */
.hero {
    text-align: center;
    padding: 2.5rem 0 1.5rem;
}
.hero-badge {
    display: inline-block;
    background: linear-gradient(90deg, #7c3aed22, #2563eb22);
    border: 1px solid #7c3aed55;
    color: #a78bfa;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    padding: 0.35rem 1rem;
    border-radius: 999px;
    margin-bottom: 1rem;
}
.hero-title {
    font-size: 2.6rem;
    font-weight: 700;
    background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.2;
    margin-bottom: 0.6rem;
}
.hero-sub {
    color: #94a3b8;
    font-size: 1.05rem;
    font-weight: 400;
}

/* ── Input area card ── */
.input-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 16px;
    padding: 2rem;
    margin: 1.5rem 0;
    backdrop-filter: blur(10px);
}

/* ── Streamlit input override ── */
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.14) !important;
    border-radius: 12px !important;
    color: #f1f5f9 !important;
    font-size: 1.05rem !important;
    padding: 0.75rem 1.1rem !important;
    font-family: 'Inter', sans-serif !important;
    transition: border-color 0.2s;
}
.stTextInput > div > div > input:focus {
    border-color: #7c3aed !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,0.2) !important;
}
.stTextInput > label {
    color: #94a3b8 !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.04em !important;
}

/* ── Primary button override ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7c3aed, #2563eb) !important;
    border: none !important;
    border-radius: 12px !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    padding: 0.75rem 2rem !important;
    width: 100% !important;
    transition: opacity 0.2s, transform 0.15s !important;
    letter-spacing: 0.02em;
}
.stButton > button[kind="primary"]:hover {
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
}

/* ── Step status row ── */
.step-row {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    padding: 0.7rem 1rem;
    border-radius: 10px;
    margin-bottom: 0.5rem;
    font-size: 0.95rem;
    font-weight: 500;
    transition: background 0.3s;
}
.step-row.done   { background: rgba(52,211,153,0.08); color: #34d399; }
.step-row.active { background: rgba(96,165,250,0.10); color: #93c5fd; }
.step-row.fail   { background: rgba(248,113,113,0.10); color: #f87171; }
.step-row.idle   { background: rgba(255,255,255,0.03); color: #64748b; }
.step-icon { font-size: 1.1rem; min-width: 1.4rem; text-align:center; }

/* ── Metric grid ── */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 1rem;
    margin: 1.5rem 0;
}
.metric-card {
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 14px;
    padding: 1.2rem 1rem;
    text-align: center;
}
.metric-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #64748b;
    margin-bottom: 0.4rem;
}
.metric-value {
    font-size: 1.55rem;
    font-weight: 700;
    color: #f1f5f9;
    line-height: 1.1;
}
.metric-sub {
    font-size: 0.75rem;
    color: #64748b;
    margin-top: 0.25rem;
}

/* ── Report card ── */
.report-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 16px;
    padding: 2rem 2.2rem;
    margin-top: 1.5rem;
    color: #cbd5e1;
    line-height: 1.75;
}
.report-card h1, .report-card h2, .report-card h3 {
    color: #f1f5f9;
}
.report-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #a78bfa;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* ── Screenshot preview grid ── */
.screenshot-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0.75rem;
    margin: 1rem 0;
}
.screenshot-grid img {
    width: 100%;
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.1);
}

/* ── Section header ── */
.section-header {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #a78bfa;
    margin: 1.5rem 0 0.75rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid rgba(167,139,250,0.2);
}

/* ── Data table styling ── */
.data-row {
    display: flex;
    justify-content: space-between;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    font-size: 0.9rem;
}
.data-row:last-child { border-bottom: none; }
.data-key { color: #94a3b8; font-weight: 500; }
.data-val { color: #f1f5f9; font-weight: 600; }

/* ── Divider ── */
.custom-divider {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.07);
    margin: 1.5rem 0;
}

/* ── Error / warning box ── */
.stAlert {
    border-radius: 12px !important;
}

/* ── Spinner ── */
.stSpinner > div {
    border-top-color: #7c3aed !important;
}
</style>
""", unsafe_allow_html=True)

# ── Helper: format large numbers ──────────────────────────────────────────────
def fmt_num(n):
    if n is None:
        return "—"
    n = float(n)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{int(n):,}"


# ── Helper: render metric cards (legacy scraper format) ───────────────────────
def render_metrics(data: dict):
    def get_val(section: str, field: str):
        sec = data.get(section, {})
        obj = sec.get(field, {})
        if obj.get("status") != "ok":
            return None
        return obj.get("value")

    html = '<div class="metric-grid">'
    metrics = [
        ("👥", "Followers",      fmt_num(get_val("profile_metrics", "followers")),       ""),
        ("➡️", "Following",      fmt_num(get_val("profile_metrics", "following")),       ""),
        ("🖼️", "Posts",          fmt_num(get_val("profile_metrics", "posts_count")),     ""),
        ("❤️", "Avg Likes",      fmt_num(get_val("engagement_metrics", "avg_likes")),       "per post"),
        ("💬", "Avg Comments",   fmt_num(get_val("engagement_metrics", "avg_comments")),    "per post"),
    ]
    
    er = get_val("engagement_metrics", "engagement_rate")
    er_str = f"{er:.2f}%" if er is not None else "—"
    metrics.append(("📈", "Engagement", er_str, "rate"))
    
    gr = get_val("growth_metrics", "growth_rate")
    gr_str = f"{gr:+.1f}%" if gr is not None else "—"
    metrics.append(("🚀", "Growth", gr_str, "monthly"))
    
    auth = get_val("authenticity_metrics", "authenticity_score")
    auth_str = f"{auth:.0f}%" if auth is not None else "—"
    metrics.append(("🛡️", "Authenticity", auth_str, "score"))

    for icon, label, value, sub in metrics:
        html += f"""
        <div class="metric-card">
            <div class="metric-label">{icon} {label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{sub}</div>
        </div>"""
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ── Helper: render extracted metrics (Gemini flat JSON format) ────────────────
def render_extracted_metrics(data: dict):
    """Render metric cards from Gemini's flat extraction JSON."""
    profile = data.get("profile_metrics", {})
    engagement = data.get("engagement_metrics", {})
    growth = data.get("growth_metrics", {})

    html = '<div class="metric-grid">'
    metrics = [
        ("👥", "Followers",    fmt_num(profile.get("followers")),     ""),
        ("➡️", "Following",    fmt_num(profile.get("following")),     ""),
        ("🖼️", "Posts",        fmt_num(profile.get("posts")),        ""),
        ("❤️", "Avg Likes",    fmt_num(engagement.get("avg_likes")), "per post"),
        ("💬", "Avg Comments", fmt_num(engagement.get("avg_comments")), "per post"),
    ]

    er = engagement.get("engagement_rate")
    er_str = f"{er:.2f}%" if er is not None else "—"
    metrics.append(("📈", "Engagement", er_str, "rate"))

    mg = growth.get("monthly_growth_rate")
    if mg is not None:
        mg_str = str(mg) if isinstance(mg, str) else f"{mg:+.1f}%"
    else:
        mg_str = "—"
    metrics.append(("🚀", "Growth", mg_str, "monthly"))

    views = engagement.get("avg_views")
    metrics.append(("👁️", "Avg Views", fmt_num(views), "per post"))

    for icon, label, value, sub in metrics:
        html += f"""
        <div class="metric-card">
            <div class="metric-label">{icon} {label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{sub}</div>
        </div>"""
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ── Helper: render a section of key-value pairs ──────────────────────────────
def render_section(title: str, data: dict):
    """Render a section of extracted data as styled key-value rows."""
    if not data or not any(v is not None for v in data.values()):
        return  # Skip empty sections

    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)
    html = ""
    for key, value in data.items():
        if value is None:
            display = '<span style="color:#475569">not visible</span>'
        elif isinstance(value, list):
            display = ", ".join(str(v) for v in value)
        else:
            display = str(value)
        label = key.replace("_", " ").title()
        html += f'<div class="data-row"><span class="data-key">{label}</span><span class="data-val">{display}</span></div>'
    st.markdown(html, unsafe_allow_html=True)


# ── Helper: render a step row ─────────────────────────────────────────────────
def step_html(icon, text, state="idle"):
    return f'<div class="step-row {state}"><span class="step-icon">{icon}</span>{text}</div>'


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN UI
# ══════════════════════════════════════════════════════════════════════════════

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-badge">🤖 AI-Powered Agent</div>
    <div class="hero-title">Influencer Audit Agent</div>
    <div class="hero-sub">Upload screenshots or enter a username to generate<br>a full professional audit report.</div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_screenshot, tab_scraper, tab_benchmark = st.tabs(["📸 Screenshot Audit", "🤖 Auto Scraper", "🔬 Multi-Model Benchmarking"])


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1: SCREENSHOT AUDIT
# ══════════════════════════════════════════════════════════════════════════════
with tab_screenshot:
    st.markdown('<div class="input-card">', unsafe_allow_html=True)

    creator_name = st.text_input(
        "Creator Username (optional)",
        placeholder="e.g.  life_with_janvi",
        key="screenshot_creator_name",
    )

    uploaded_files = st.file_uploader(
        "Upload Analytics Screenshots",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        key="screenshot_uploader",
        help="Upload screenshots from NotJustAnalytics, Toolzu, Socialinsider, or similar platforms.",
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Preview uploaded screenshots ──────────────────────────────────────
    if uploaded_files:
        preview_limit = 9  # Show at most 9 thumbnails to keep UI clean
        shown = uploaded_files[:preview_limit]
        st.markdown(f'<div class="section-header">📎 Uploaded Screenshots ({len(uploaded_files)})</div>', unsafe_allow_html=True)
        cols = st.columns(min(len(shown), 3))
        for i, f in enumerate(shown):
            f.seek(0)  # Reset file pointer before reading
            with cols[i % 3]:
                st.image(f.getvalue(), caption=f.name, use_container_width=True)
        if len(uploaded_files) > preview_limit:
            st.caption(f"… and {len(uploaded_files) - preview_limit} more screenshot(s) not shown in preview.")

    # ── Extract button ────────────────────────────────────────────────────
    extract_btn = st.button("🔍  Extract Analytics", type="primary", key="extract_btn")

    if extract_btn:
        if not uploaded_files:
            st.warning("⚠️  Please upload at least one screenshot before extracting.")
            st.stop()

        # Clear out any previous sessions to avoid state contamination
        if "extracted_metrics" in st.session_state:
            del st.session_state.extracted_metrics
        if "strategist_report" in st.session_state:
            del st.session_state.strategist_report

        # ── Step tracker ──────────────────────────────────────────────────
        status_box = st.empty()

        def render_steps(steps):
            html = "".join(step_html(i, l, s) for i, l, s in steps)
            status_box.markdown(html, unsafe_allow_html=True)

        steps = [
            ("📤", f"Processing {len(uploaded_files)} screenshot(s)", "active"),
            ("🤖", "Sending to Gemini for extraction", "idle"),
            ("✅", "Extraction complete", "idle"),
        ]
        render_steps(steps)

        # ── Read image bytes ──────────────────────────────────────────────
        image_bytes_list = []
        image_filenames = []
        for f in uploaded_files:
            image_bytes_list.append(f.getvalue())
            image_filenames.append(f.name)

        steps[0] = ("✅", f"Loaded {len(uploaded_files)} screenshot(s)", "done")
        steps[1] = ("🤖", "Sending to Gemini for extraction…", "active")
        render_steps(steps)

        # ── Call Gemini extractor ─────────────────────────────────────────
        from services.gemini_extractor import GeminiExtractor

        extractor = GeminiExtractor()
        name = creator_name.strip().lstrip("@") if creator_name and creator_name.strip() else None

        # Progress callback to update UI during batch processing
        def on_batch_progress(batch_num, total_batches, status):
            steps[1] = ("🤖", f"Extracting batch {batch_num}/{total_batches}…", "active")
            render_steps(steps)

        result = extractor.extract(
            image_bytes_list,
            creator_name=name,
            filenames=image_filenames,
            progress_callback=on_batch_progress,
        )

        # ── Handle result ─────────────────────────────────────────────────
        if "error" in result:
            steps[1] = ("❌", f"Extraction failed: {result['error'][:100]}", "fail")
            steps[2] = ("❌", "Extraction failed", "fail")
            render_steps(steps)

            st.error(f"**Extraction failed:** {result['error']}")
            if result.get("raw_response"):
                with st.expander("🔍 Gemini Raw Response (debug)"):
                    st.code(result["raw_response"], language="text")
            st.stop()

        batches_ok = result.pop("_batches_processed", "?")
        batches_total = result.pop("_batches_total", "?")
        batch_errors = result.pop("_batch_errors", [])
        skipped_imgs = result.pop("_skipped_images", [])

        steps[1] = ("✅", f"Gemini extraction complete ({batches_ok}/{batches_total} batches)", "done")
        steps[2] = ("✅", "Analytics extracted successfully", "done")
        render_steps(steps)

        if batch_errors:
            for err in batch_errors:
                st.warning(f"⚠️ {err}")
        if skipped_imgs:
            st.info(f"ℹ️ Skipped {len(skipped_imgs)} unrecognized file(s): {', '.join(skipped_imgs)}")

        # Store in session state for persistence across click/rerun actions
        st.session_state.extracted_metrics = result
        st.session_state.creator_name_display = result.get("creator_username") or name or "Unknown"
        st.session_state.source_display = result.get("source_platform") or "Analytics Screenshot"
        st.rerun()

    # ── Persistent view block ─────────────────────────────────────────────────
    if "extracted_metrics" in st.session_state:
        result = st.session_state.extracted_metrics
        name_display = st.session_state.creator_name_display
        src_display = st.session_state.source_display

        # ── Display extracted results ──
        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
        st.markdown(f"### 📊 Extracted Metrics — @{name_display}")
        st.caption(f"Source: {src_display}")

        render_extracted_metrics(result)

        # ── Action Buttons for Strategy Report and PDF Generation ──
        st.markdown('<div class="input-card" style="margin-top: 1.5rem; padding: 1.5rem;">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            gen_report_btn = st.button("🧠 Generate Growth Strategy Report", type="primary", use_container_width=True)
        with col2:
            pdf_ready = "strategist_report" in st.session_state
            if pdf_ready:
                from services.pdf_generator import generate_pdf_report
                
                with st.spinner("Compiling beautiful PDF report…"):
                    try:
                        pdf_bytes = generate_pdf_report(
                            st.session_state.creator_name_display,
                            st.session_state.strategist_report,
                            st.session_state.extracted_metrics
                        )
                        st.download_button(
                            label="📥 Download Strategy PDF",
                            data=pdf_bytes,
                            file_name=f"{st.session_state.creator_name_display}_instagram_audit.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Failed to generate PDF: {e}")
            else:
                st.button("📥 Download Strategy PDF (Generate Report First)", disabled=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Generate Strategy Report via Gemini Content Strategist
        if gen_report_btn:
            with st.spinner("🔮 Analyzing metrics & formulating custom strategist recommendations..."):
                try:
                    from services.strategist_service import StrategistService
                    strategist = StrategistService()
                    report_text = strategist.generate_growth_audit(result, name_display)
                    st.session_state.strategist_report = report_text
                    st.rerun()
                except Exception as e:
                    st.error(f"Strategist Service Error: {e}")

        # Display the strategist report if it exists
        if "strategist_report" in st.session_state:
            st.markdown('<div class="report-card">', unsafe_allow_html=True)
            st.markdown('<div class="report-title">📋 Arohanum Elevate X Content Strategist Audit</div>', unsafe_allow_html=True)
            st.markdown(st.session_state.strategist_report)
            st.markdown('</div>', unsafe_allow_html=True)

        # Detailed sections
        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
        render_section("👤 Profile Metrics", result.get("profile_metrics", {}))
        render_section("❤️ Engagement Metrics", result.get("engagement_metrics", {}))
        render_section("🚀 Growth Metrics", result.get("growth_metrics", {}))
        render_section("#️⃣ Hashtag Metrics", result.get("hashtag_metrics", {}))
        render_section("🎬 Content Metrics", result.get("content_metrics", {}))
        render_section("👥 Audience Metrics", result.get("audience_metrics", {}))

        # Additional metrics (catch-all)
        additional = result.get("additional_metrics", {})
        if additional:
            render_section("📋 Additional Metrics", additional)

        # Raw JSON debug
        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
        with st.expander("🔍 View raw extracted JSON"):
            st.json(result)


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2: AUTO SCRAPER (existing flow — preserved as-is)
# ══════════════════════════════════════════════════════════════════════════════
with tab_scraper:
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    username = st.text_input(
        "Instagram Username",
        placeholder="e.g.  natgeo  or  cristiano",
        label_visibility="visible",
        key="scraper_username",
    )
    run = st.button("🚀  Run Audit Agent", type="primary", key="scraper_run_btn")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Agent execution ───────────────────────────────────────────────────
    if run:
        if not username.strip():
            st.warning("⚠️  Please enter an Instagram username before running.")
            st.stop()

        username = username.strip().lstrip("@")

        # ── Step tracker placeholder ──────────────────────────────────────
        status_box = st.empty()

        def render_steps(steps):
            """steps = list of (icon, label, state)"""
            html = "".join(step_html(i, l, s) for i, l, s in steps)
            status_box.markdown(html, unsafe_allow_html=True)

        steps = [
            ("🌐", f"Launching Chrome → notjustanalytics.com/@{username}", "active"),
            ("📡", "Extracting metrics from page",                         "idle"),
            ("🤖", "Generating AI audit report via Gemini",                "idle"),
        ]
        render_steps(steps)

        # ── Step 1 : scrape ───────────────────────────────────────────────
        data = None
        try:
            from scraper import get_profile_data, save_to_json
            from database.models import Session, Influencer, AuditRun, RawScraperData, NormalizedMetrics
            from services.normalizer import MetricsNormalizer
            
            data = get_profile_data(username)
            save_to_json(data)
            
            # --- PostgreSQL Integration ---
            with Session() as session:
                # 1. Get or create influencer
                influencer = session.query(Influencer).filter_by(username=username).first()
                if not influencer:
                    influencer = Influencer(username=username)
                    session.add(influencer)
                    session.commit()
                
                # 2. Create AuditRun
                audit_run = AuditRun(influencer_id=influencer.id, status="scraping_done")
                session.add(audit_run)
                session.commit()
                
                # 3. Save Raw Data
                raw_data = RawScraperData(
                    audit_run_id=audit_run.id,
                    source="nja",
                    raw_json=data
                )
                session.add(raw_data)
                
                # 4. Normalize and Save Metrics
                normalizer = MetricsNormalizer()
                norm_metrics = normalizer.normalize("nja", data)
                db_metrics = NormalizedMetrics(
                    audit_run_id=audit_run.id,
                    **norm_metrics
                )
                session.add(db_metrics)
                session.commit()
                
                # Save audit_run.id to session state for later report attachment
                st.session_state.current_audit_run_id = audit_run.id

            steps[0] = ("✅", f"Scraped @{username} successfully", "done")
            steps[1] = ("📡", "Extracting metrics from page",      "done")
            render_steps(steps)

        except Exception as e:
            err_msg = str(e)
            steps[0] = ("❌", f"Scraping failed: {err_msg[:120]}", "fail")
            render_steps(steps)
            st.error(f"**Scraping failed:** {err_msg}")
            st.stop()

        # ── Metric cards ─────────────────────────────────────────────────
        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
        st.markdown(f"### 📊 Metrics for **@{username}**")
        render_metrics(data)
        
        # --- Validation Warnings ---
        from services.validator import AuditValidator
        validator = AuditValidator()
        warnings = validator.validate(data)
        for w in warnings:
            st.warning(f"⚠️ {w}")

        # ── Step 3 : LLM report ──────────────────────────────────────────
        steps[2] = ("🤖", "Generating AI audit report via Gemini…", "active")
        render_steps(steps)

        report = None
        try:
            from llm.client import generate_audit
            from database.models import Session, Report, AuditRun
            
            report = generate_audit(data)
            
            # --- Save Report to PostgreSQL ---
            if 'current_audit_run_id' in st.session_state:
                with Session() as session:
                    db_report = Report(
                        audit_run_id=st.session_state.current_audit_run_id,
                        ai_report=report
                    )
                    session.add(db_report)
                    
                    # Update audit run status
                    audit_run = session.query(AuditRun).get(st.session_state.current_audit_run_id)
                    if audit_run:
                        audit_run.status = "success"
                    
                    session.commit()

            steps[2] = ("✅", "Audit report generated", "done")
            render_steps(steps)

        except Exception as e:
            steps[2] = ("❌", f"Report generation failed: {e}", "fail")
            render_steps(steps)
            st.error(f"LLM error: {e}")
            st.stop()

        # ── Report display ───────────────────────────────────────────────
        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        st.markdown('<div class="report-title">📋 Audit Report</div>', unsafe_allow_html=True)
        st.markdown(report)
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Raw JSON expander ────────────────────────────────────────────
        with st.expander("🔍 View raw scraped data"):
            st.json(data)


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 3: MULTI-MODEL BENCHMARKING
# ══════════════════════════════════════════════════════════════════════════════
with tab_benchmark:
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    
    col_operator, col_creator = st.columns(2)
    with col_operator:
        employee_username = st.text_input(
            "Employee Username",
            value="operator_demo",
            placeholder="e.g.  sanchita_a",
            key="benchmark_employee_username",
            help="Your identifier to link reports to you in the database."
        )
    with col_creator:
        benchmark_creator_name = st.text_input(
            "Creator Username (optional)",
            placeholder="e.g.  life_with_janvi",
            key="benchmark_creator_name",
        )
        
    uploaded_files_bench = st.file_uploader(
        "Upload Analytics Screenshots",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        key="benchmark_uploader",
        help="Upload screenshots from NotJustAnalytics, Toolzu, Socialinsider, etc.",
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Preview uploaded screenshots
    if uploaded_files_bench:
        preview_limit = 6
        shown = uploaded_files_bench[:preview_limit]
        st.markdown(f'<div class="section-header">📎 Uploaded Screenshots ({len(uploaded_files_bench)})</div>', unsafe_allow_html=True)
        cols = st.columns(min(len(shown), 3))
        for i, f in enumerate(shown):
            f.seek(0)
            with cols[i % 3]:
                st.image(f.getvalue(), caption=f.name, use_container_width=True)
        if len(uploaded_files_bench) > preview_limit:
            st.caption(f"… and {len(uploaded_files_bench) - preview_limit} more screenshot(s) not shown in preview.")
            
    # Benchmark Run Button
    benchmark_btn = st.button("🔬  Run Multi-Model Benchmark", type="primary", key="benchmark_btn")
    
    if benchmark_btn:
        if not uploaded_files_bench:
            st.warning("⚠️  Please upload at least one screenshot before running the benchmark.")
            st.stop()
            
        # Clean previous state
        if "benchmark_results" in st.session_state:
            del st.session_state.benchmark_results
        if "benchmark_extracted_metrics" in st.session_state:
            del st.session_state.benchmark_extracted_metrics
        if "benchmark_creator" in st.session_state:
            del st.session_state.benchmark_creator
            
        # Step tracker
        status_box = st.empty()
        
        def render_benchmark_steps(steps):
            html = "".join(step_html(i, l, s) for i, l, s in steps)
            status_box.markdown(html, unsafe_allow_html=True)
            
        steps = [
            ("📤", f"Loaded {len(uploaded_files_bench)} screenshots", "active"),
            ("🤖", "Extracting flat analytics JSON via Gemini (Perception)", "idle"),
            ("💾", "Registering Audit Run in PostgreSQL", "idle"),
            ("🔮", "Generating creator audits across 4 OpenRouter models (Reasoning)", "idle"),
        ]
        render_benchmark_steps(steps)
        
        # 1. Processing files
        image_bytes_list = []
        image_filenames = []
        for f in uploaded_files_bench:
            image_bytes_list.append(f.getvalue())
            image_filenames.append(f.name)
            
        steps[0] = ("✅", f"Loaded {len(uploaded_files_bench)} screenshot(s)", "done")
        steps[1] = ("🤖", "Extracting flat analytics JSON via Gemini (Perception)…", "active")
        render_benchmark_steps(steps)
        
        # 2. Extract metrics via Gemini
        from services.gemini_extractor import GeminiExtractor
        extractor = GeminiExtractor()
        name = benchmark_creator_name.strip().lstrip("@") if benchmark_creator_name and benchmark_creator_name.strip() else None
        
        def on_batch_progress(batch_num, total_batches, status):
            steps[1] = ("🤖", f"Extracting batch {batch_num}/{total_batches} via Gemini…", "active")
            render_benchmark_steps(steps)
            
        result = extractor.extract(
            image_bytes_list,
            creator_name=name,
            filenames=image_filenames,
            progress_callback=on_batch_progress,
        )
        
        if "error" in result:
            steps[1] = ("❌", f"Extraction failed: {result['error'][:100]}", "fail")
            render_benchmark_steps(steps)
            st.error(f"**Gemini Extraction failed:** {result['error']}")
            st.stop()
            
        result.pop("_batches_processed", None)
        result.pop("_batches_total", None)
        result.pop("_batch_errors", None)
        result.pop("_skipped_images", None)
        
        steps[1] = ("✅", "Flat analytics JSON extracted (Perception complete)", "done")
        steps[2] = ("💾", "Registering Audit Run in PostgreSQL…", "active")
        render_benchmark_steps(steps)
        
        # 3. Save to database to get audit_run_id (Avoids duplicate JSON long-term)
        audit_run_id = None
        creator_name_resolved = result.get("creator_username") or name or "unknown_creator"
        
        try:
            with Session() as session:
                # Get or create influencer
                influencer = session.query(Influencer).filter_by(username=creator_name_resolved).first()
                if not influencer:
                    influencer = Influencer(username=creator_name_resolved)
                    session.add(influencer)
                    session.commit()
                    
                # Create AuditRun
                audit_run = AuditRun(influencer_id=influencer.id, status="benchmarking")
                session.add(audit_run)
                session.commit()
                audit_run_id = audit_run.id
                
                # Save NormalizedMetrics
                profile = result.get("profile_metrics", {})
                engagement = result.get("engagement_metrics", {})
                growth = result.get("growth_metrics", {})
                
                def to_float(val):
                    if val is None:
                        return None
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return None
                        
                db_metrics = NormalizedMetrics(
                    audit_run_id=audit_run_id,
                    followers=to_float(profile.get("followers")),
                    following=to_float(profile.get("following")),
                    posts_count=to_float(profile.get("posts")),
                    avg_likes=to_float(engagement.get("avg_likes")),
                    avg_comments=to_float(engagement.get("avg_comments")),
                    engagement_rate=to_float(engagement.get("engagement_rate")),
                    growth_rate=to_float(growth.get("monthly_growth_rate")),
                    authenticity_score=None
                )
                session.add(db_metrics)
                session.commit()
                
            steps[2] = ("✅", f"Audit Run registered in DB (ID: {audit_run_id})", "done")
            render_benchmark_steps(steps)
            
        except Exception as e:
            steps[2] = ("❌", f"Database registration failed: {str(e)[:100]}", "fail")
            render_benchmark_steps(steps)
            st.error(f"**PostgreSQL registration failed:** {str(e)}")
            st.stop()
            
        # 4. OpenRouter Multi-Model Generation
        steps[3] = ("🔮", "Generating creator audits across 4 OpenRouter models…", "active")
        render_benchmark_steps(steps)
        
        benchmark_results = {}
        
        generator = ReportGeneratorService()
        storage = StorageManager()
        
        progress_bar = st.progress(0.0)
        model_keys = list(BENCHMARK_MODELS.keys())
        total_models = len(model_keys)
        
        for idx, model_key in enumerate(model_keys, 1):
            steps[3] = ("🔮", f"Generating report using {model_key} ({idx}/{total_models})…", "active")
            render_benchmark_steps(steps)
            
            # Isolated run per model
            model_res = generator.generate_report(model_key, result, creator_name_resolved)
            
            # If no errors, immediately double-persist
            if not model_res.get("error") and model_res.get("report_text"):
                local_path = storage.save_report_locally(
                    creator_name_resolved,
                    model_key,
                    model_res["report_text"]
                )
                model_res["local_filepath"] = local_path
                
                db_success = storage.save_report_to_db(
                    audit_run_id=audit_run_id,
                    employee_username=employee_username,
                    model_used=model_key,
                    report_text=model_res["report_text"],
                    raw_model_response=model_res["raw_response"],
                    latency=model_res["latency"],
                    prompt_tokens=model_res["prompt_tokens"],
                    completion_tokens=model_res["completion_tokens"]
                )
                model_res["db_saved"] = db_success
            else:
                model_res["local_filepath"] = None
                model_res["db_saved"] = False
                
            benchmark_results[model_key] = model_res
            progress_bar.progress(idx / total_models)
            
        # Update AuditRun status to benchmark_done
        try:
            with Session() as session:
                audit_run = session.query(AuditRun).get(audit_run_id)
                if audit_run:
                    audit_run.status = "benchmark_done"
                session.commit()
        except Exception:
            pass
            
        steps[3] = ("✅", "Multi-model benchmarking complete!", "done")
        render_benchmark_steps(steps)
        
        st.session_state.benchmark_results = benchmark_results
        st.session_state.benchmark_extracted_metrics = result
        st.session_state.benchmark_creator = creator_name_resolved
        st.session_state.benchmark_audit_run_id = audit_run_id
        st.session_state.benchmark_employee = employee_username
        st.session_state.benchmark_timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        st.rerun()

    # ── Persistent view block ──
    if "benchmark_results" in st.session_state:
        results = st.session_state.benchmark_results
        extracted = st.session_state.benchmark_extracted_metrics
        creator = st.session_state.benchmark_creator
        run_id = st.session_state.benchmark_audit_run_id
        employee = st.session_state.benchmark_employee
        timestamp = st.session_state.benchmark_timestamp
        
        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
        st.markdown(f"### 🔬 Benchmark Results — @{creator}")
        st.caption(f"Audit Run ID: **{run_id}** | Run by: **{employee}** | Generated: **{timestamp}**")
        
        render_extracted_metrics(extracted)
        
        # Display settings
        st.markdown("##### ⚙️ Comparison View Settings")
        display_mode = st.radio(
            "Select display layout:",
            ["Grid View (Side-by-Side)", "Detailed Tab View"],
            horizontal=True,
            key="benchmark_display_mode"
        )
        
        st.markdown('<div style="margin-top: 1.5rem;"></div>', unsafe_allow_html=True)
        
        # 1. Grid View
        if display_mode == "Grid View (Side-by-Side)":
            cols = st.columns(4)
            for idx, (model_key, data_res) in enumerate(results.items()):
                with cols[idx]:
                    st.markdown(f"#### 🤖 {model_key}")
                    
                    # Performance Telemetry
                    st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 0.6rem 0.8rem; font-size: 0.78rem; color: #94a3b8; margin-bottom: 1rem; line-height: 1.4;">
                        ⏳ Latency: <b>{data_res['latency']}s</b><br>
                        📥 Prompt Tokens: <b>{data_res['prompt_tokens']}</b><br>
                        📤 Completion Tokens: <b>{data_res['completion_tokens']}</b><br>
                        🗄️ Database: {'<span style="color:#34d399">✅ Saved</span>' if data_res['db_saved'] else '<span style="color:#f87171">❌ Failed</span>'}<br>
                        💾 Disk: {'<span style="color:#34d399">✅ Stored</span>' if data_res['local_filepath'] else '<span style="color:#f87171">❌ Failed</span>'}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if data_res.get("error"):
                        st.error(f"❌ Generation Failed\n\n{data_res['error']}")
                    else:
                        st.markdown(f'<div class="report-card" style="padding: 1.2rem; font-size: 0.82rem; height: 500px; overflow-y: scroll; border: 1px solid rgba(255,255,255,0.08);">', unsafe_allow_html=True)
                        st.markdown(data_res["report_text"])
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Download Button
                        st.download_button(
                            label=f"📥 Download Report",
                            data=data_res["report_text"],
                            file_name=f"{creator}_{model_key.lower().replace(' ', '_')}_audit.md",
                            mime="text/markdown",
                            key=f"grid_dl_{model_key}"
                        )
                        
        # 2. Detailed Tab View
        else:
            tabs = st.tabs(list(results.keys()))
            for idx, (model_key, data_res) in enumerate(results.items()):
                with tabs[idx]:
                    # Telemetry metrics row
                    stat_col1, stat_col2, stat_col3, stat_col4, stat_col5 = st.columns(5)
                    with stat_col1:
                        st.metric("⏳ Latency", f"{data_res['latency']}s")
                    with stat_col2:
                        st.metric("📥 Input Tokens", data_res['prompt_tokens'])
                    with stat_col3:
                        st.metric("📤 Output Tokens", data_res['completion_tokens'])
                    with stat_col4:
                        db_status = "Saved successfully" if data_res['db_saved'] else "Save failed"
                        st.metric("🗄️ DB Archival", db_status)
                    with stat_col5:
                        disk_status = "Stored locally" if data_res['local_filepath'] else "Write failed"
                        st.metric("💾 Disk Archive", disk_status)
                        
                    if data_res.get("local_filepath"):
                        st.caption(f"Local file location: `{data_res['local_filepath']}`")
                        
                    st.markdown('<hr class="custom-divider" style="margin: 1rem 0;">', unsafe_allow_html=True)
                    
                    if data_res.get("error"):
                        st.error(f"❌ Model Generation Failed\n\n{data_res['error']}")
                    else:
                        st.markdown('<div class="report-card">', unsafe_allow_html=True)
                        st.markdown(data_res["report_text"])
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Download Button
                        st.download_button(
                            label=f"📥 Download {model_key} Report (Markdown)",
                            data=data_res["report_text"],
                            file_name=f"{creator}_{model_key.lower().replace(' ', '_')}_audit.md",
                            mime="text/markdown",
                            key=f"tab_dl_{model_key}",
                            use_container_width=True
                        )
                        
        # Debug Expanders
        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
        
        with st.expander("🔍 View Extracted flat JSON (Perception output)"):
            st.json(extracted)
            
        with st.expander("🔍 View Raw API Responses (Debug formatting and reasoning leaks)"):
            debug_info = {}
            for model_key, data_res in results.items():
                debug_info[model_key] = {
                    "raw_response": data_res["raw_response"],
                    "error": data_res.get("error")
                }
            st.json(debug_info)
