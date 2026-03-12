"""
FMI 1200 Creator — Streamlit UI
Light theme. Deployable on Streamlit Cloud.
"""
from __future__ import annotations

import json
import queue
import sys
import threading
import zipfile
from io import BytesIO
from pathlib import Path

import streamlit as st

# ── paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
SRC  = ROOT / "src"
sys.path.insert(0, str(SRC))

from fmi_batch_factory.pipeline import run_batch
from fmi_batch_factory.utils import slugify

BRIEFS_PATH = ROOT / "input" / "market_briefs.json"
SEEN_PATH   = ROOT / "state" / "processed_briefs.json"
OUTPUT_DIR  = ROOT / "output"
ENV_PATH    = ROOT / ".env"

for _p in [BRIEFS_PATH.parent, SEEN_PATH.parent, OUTPUT_DIR]:
    _p.mkdir(parents=True, exist_ok=True)


# ── key loading: Streamlit secrets → .env file → empty ──────────────────────

ENV_DEFAULTS = {
    "DEEPSEEK_API_KEY":  "",
    "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
    "DEEPSEEK_MODEL":    "deepseek-chat",
    "KIMI_API_KEY":      "",
    "KIMI_BASE_URL":     "https://api.moonshot.cn/v1",
    "KIMI_MODEL":        "moonshot-v1-32k",
    "OPENAI_API_KEY":    "",
}


def _load_env() -> dict:
    """Load from Streamlit secrets first, then .env file, then defaults."""
    cfg = dict(ENV_DEFAULTS)

    # 1. Try Streamlit Cloud secrets
    try:
        for k in cfg:
            if k in st.secrets:
                cfg[k] = st.secrets[k]
    except Exception:
        pass

    # 2. Overlay with local .env file (for local runs)
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            if k in cfg and v.strip():
                cfg[k] = v.strip()

    return cfg


def _save_env(cfg: dict) -> None:
    """Save to local .env (only relevant for local runs; on Cloud use secrets)."""
    try:
        ENV_PATH.write_text("\n".join(f"{k}={v}" for k, v in cfg.items()), encoding="utf-8")
    except Exception:
        pass  # read-only filesystem on Streamlit Cloud — that's fine


def _keys_from_env(cfg: dict) -> dict:
    return {
        "deepseek":       cfg["DEEPSEEK_API_KEY"],
        "deepseek_base":  cfg["DEEPSEEK_BASE_URL"],
        "deepseek_model": cfg["DEEPSEEK_MODEL"],
        "kimi":           cfg["KIMI_API_KEY"],
        "kimi_base":      cfg["KIMI_BASE_URL"],
        "kimi_model":     cfg["KIMI_MODEL"],
        "openai":         cfg["OPENAI_API_KEY"],
    }


def _keys_complete(k: dict) -> bool:
    return bool(k.get("deepseek") and k.get("kimi") and k.get("openai"))


# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FMI 1200 Creator",
    page_icon="📝",
    layout="wide",
)

st.markdown("""
<style>
/* Light theme overrides */
.main-header {
    font-size: 2rem;
    font-weight: 700;
    color: #1a56db;
    margin-bottom: 0.2rem;
}
.sub-header {
    color: #6b7280;
    margin-bottom: 1.5rem;
    font-size: 0.95rem;
}
.metric-box {
    background: #f0f4f8;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    border: 1px solid #e2e8f0;
}
.metric-num {
    font-size: 2rem;
    font-weight: 700;
    color: #1a56db;
}
.metric-lbl {
    font-size: 0.82rem;
    color: #6b7280;
    margin-top: 2px;
}
.agent-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-left: 8px;
}
.badge-ds    { background: #dbeafe; color: #1e40af; }
.badge-kimi  { background: #ede9fe; color: #5b21b6; }
.badge-oai   { background: #d1fae5; color: #065f46; }
.badge-unknown { background: #f3f4f6; color: #6b7280; }
.cloud-note {
    background: #eff6ff;
    border-left: 4px solid #1a56db;
    padding: 0.75rem 1rem;
    border-radius: 0 8px 8px 0;
    font-size: 0.88rem;
    color: #1e3a5f;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ── session bootstrap ─────────────────────────────────────────────────────────
if "env_cfg"   not in st.session_state: st.session_state["env_cfg"]   = _load_env()
if "running"   not in st.session_state: st.session_state["running"]   = False
if "log_lines" not in st.session_state: st.session_state["log_lines"] = []
if "summary"   not in st.session_state: st.session_state["summary"]   = None
if "log_queue" not in st.session_state: st.session_state["log_queue"] = queue.Queue()


# ── helpers ───────────────────────────────────────────────────────────────────

def _agent_badge(agent: str) -> str:
    cls = {"DeepSeek": "badge-ds", "Kimi": "badge-kimi", "OpenAI-GPT4o": "badge-oai"}.get(agent, "badge-unknown")
    return f'<span class="agent-badge {cls}">{agent}</span>'

def _load_briefs() -> list[dict]:
    if not BRIEFS_PATH.exists(): return []
    try: return json.loads(BRIEFS_PATH.read_text(encoding="utf-8"))
    except: return []

def _load_seen() -> set[str]:
    if not SEEN_PATH.exists(): return set()
    try: return set(json.loads(SEEN_PATH.read_text(encoding="utf-8")))
    except: return set()

def _save_briefs(b: list) -> None:
    BRIEFS_PATH.write_text(json.dumps(b, indent=2, ensure_ascii=False), encoding="utf-8")

def _collect_docx() -> list[Path]:
    return sorted(OUTPUT_DIR.rglob("*.docx"))

def _zip_docx() -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in _collect_docx(): zf.write(f, f.name)
    return buf.getvalue()

def _start_batch(api_keys: dict, batch_size: int, concurrency: int) -> None:
    st.session_state.running   = True
    st.session_state.log_lines = []
    st.session_state.summary   = None
    log_q: queue.Queue = st.session_state.log_queue

    def _log(msg): log_q.put(msg)

    def _worker():
        try:
            s = run_batch(
                briefs_path=BRIEFS_PATH, output_dir=OUTPUT_DIR, seen_path=SEEN_PATH,
                openai_key=api_keys["openai"],
                deepseek_key=api_keys["deepseek"],
                deepseek_base_url=api_keys["deepseek_base"],
                deepseek_model=api_keys["deepseek_model"],
                kimi_key=api_keys["kimi"],
                kimi_base_url=api_keys["kimi_base"],
                kimi_model=api_keys["kimi_model"],
                log=_log, batch_size=batch_size, concurrency=concurrency,
            )
            log_q.put(f"__DONE__{json.dumps(s)}")
        except Exception as e:
            log_q.put(f"__ERROR__{e}")

    threading.Thread(target=_worker, daemon=True).start()


# ═══════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="main-header">📊 FMI 1200 Creator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Batch article generation · 3 prose agents per article · DeepSeek + Kimi + OpenAI GPT-4o</div>', unsafe_allow_html=True)

tab_settings, tab_run, tab_briefs, tab_outputs = st.tabs(["⚙ Settings", "▶ Run Batch", "📋 Manage Briefs", "📁 Outputs"])


# ═══════════════════════════════════════════════════════════════════════════
# SETTINGS TAB
# ═══════════════════════════════════════════════════════════════════════════
with tab_settings:
    st.subheader("API Keys & Model Configuration")

    # Detect if running on Streamlit Cloud
    is_cloud = False
    try:
        is_cloud = bool(st.secrets.get("OPENAI_API_KEY") or st.secrets.get("DEEPSEEK_API_KEY"))
    except Exception:
        pass

    if is_cloud:
        st.markdown("""
        <div class="cloud-note">
        <strong>Running on Streamlit Cloud.</strong> API keys are loaded from your app's Secrets.
        To update keys: go to your app on <strong>share.streamlit.io</strong> → Settings → Secrets.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption("Local run: keys save to a `.env` file in the app folder. For Streamlit Cloud, add keys in app Secrets instead.")

    env = st.session_state["env_cfg"]
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### DeepSeek — Fact Extraction + Prose Agent")
        v_ds_key   = st.text_input("DeepSeek API Key",  value=env["DEEPSEEK_API_KEY"],  type="password", key="f_ds_key")
        v_ds_base  = st.text_input("DeepSeek Base URL", value=env["DEEPSEEK_BASE_URL"],                  key="f_ds_base")
        v_ds_model = st.text_input("DeepSeek Model",    value=env["DEEPSEEK_MODEL"],                     key="f_ds_model")

        st.markdown("---")
        st.markdown("##### Kimi (Moonshot) — Prose Agent")
        v_kimi_key   = st.text_input("Kimi API Key",  value=env["KIMI_API_KEY"],  type="password", key="f_kimi_key")
        v_kimi_base  = st.text_input("Kimi Base URL", value=env["KIMI_BASE_URL"],                  key="f_kimi_base")
        v_kimi_model = st.text_input("Kimi Model",    value=env["KIMI_MODEL"],                     key="f_kimi_model")

    with col2:
        st.markdown("##### OpenAI — Web Search + GPT-4o Prose Agent")
        v_oai_key = st.text_input("OpenAI API Key", value=env["OPENAI_API_KEY"], type="password", key="f_oai_key")
        st.info("**Web search** uses `gpt-4o-mini`. **Prose** uses `gpt-4o` (top model). Same key for both.")

        st.markdown("---")
        st.markdown("##### Status")
        cur_keys = _keys_from_env(env)
        if _keys_complete(cur_keys):
            st.success("All 3 keys set. Ready to run.")
        else:
            missing = [n for n, k in [("DeepSeek", cur_keys["deepseek"]),
                                       ("Kimi", cur_keys["kimi"]),
                                       ("OpenAI", cur_keys["openai"])] if not k]
            st.warning(f"Missing keys: {', '.join(missing)}")

    st.markdown("")

    if is_cloud:
        st.info("On Streamlit Cloud, update keys via the Secrets panel in your app settings. The form above reflects currently loaded values.")
    else:
        if st.button("💾 Save Settings", type="primary"):
            new_cfg = {
                "DEEPSEEK_API_KEY":  v_ds_key,
                "DEEPSEEK_BASE_URL": v_ds_base,
                "DEEPSEEK_MODEL":    v_ds_model,
                "KIMI_API_KEY":      v_kimi_key,
                "KIMI_BASE_URL":     v_kimi_base,
                "KIMI_MODEL":        v_kimi_model,
                "OPENAI_API_KEY":    v_oai_key,
            }
            _save_env(new_cfg)
            st.session_state["env_cfg"] = new_cfg
            st.success("Saved to `.env` and active now.")
            st.rerun()

    st.markdown("---")
    st.markdown("#### How to deploy on Streamlit Cloud")
    with st.expander("Step-by-step instructions"):
        st.markdown("""
1. Push this project folder to a **GitHub repository** (public or private).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app** → select your repo → set main file as `app.py`.
4. Before deploying, click **Advanced settings → Secrets** and paste:
```
DEEPSEEK_API_KEY = "your-key-here"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
KIMI_API_KEY = "your-key-here"
KIMI_BASE_URL = "https://api.moonshot.cn/v1"
KIMI_MODEL = "moonshot-v1-32k"
OPENAI_API_KEY = "your-key-here"
```
5. Click **Deploy**. The app will be live at a public URL.

**Note on output files:** Streamlit Cloud has an ephemeral filesystem — DOCX files are lost on restart.
Use the **Download ZIP** button in the Outputs tab immediately after each batch run to save your files.
        """)


# ═══════════════════════════════════════════════════════════════════════════
# RUN BATCH TAB
# ═══════════════════════════════════════════════════════════════════════════
with tab_run:
    env      = st.session_state["env_cfg"]
    api_keys = _keys_from_env(env)
    keys_ok  = _keys_complete(api_keys)

    if not keys_ok:
        st.warning("Go to ⚙ Settings, enter your API keys, and click Save Settings.")

    briefs  = _load_briefs()
    seen    = _load_seen()
    pending = [b for b in briefs if b.get("market_slug", slugify(b.get("market_name", ""))) not in seen]

    m1, m2, m3, m4 = st.columns(4)
    for col, num, lbl in [(m1, len(briefs), "Total Briefs"), (m2, len(pending), "Pending"),
                           (m3, len(seen), "Completed"), (m4, len(_collect_docx()), "DOCX Files")]:
        with col:
            st.markdown(f'<div class="metric-box"><div class="metric-num">{num}</div><div class="metric-lbl">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("")
    c1, c2 = st.columns(2)
    with c1: batch_size  = st.slider("Batch size (articles per run)", 1, 10, 10)
    with c2: concurrency = st.slider("Concurrency (articles at a time)", 1, 5, 3)
    st.caption("Each article fires DeepSeek + Kimi + GPT-4o in parallel. Best prose output wins.")

    bc, rc = st.columns([2, 1])
    with bc:
        if st.button("▶ Start Batch",
                     disabled=(not keys_ok or st.session_state.running or not pending),
                     use_container_width=True, type="primary"):
            _start_batch(api_keys, batch_size, concurrency)
            st.rerun()
    with rc:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    if st.session_state.running or st.session_state.log_lines:
        st.markdown("---")
        st.subheader("Live Log")
        log_q: queue.Queue = st.session_state.log_queue
        while not log_q.empty():
            msg = log_q.get_nowait()
            if msg.startswith("__DONE__"):
                st.session_state.summary = json.loads(msg[8:])
                st.session_state.running = False
            elif msg.startswith("__ERROR__"):
                st.session_state.log_lines.append(f"ERROR: {msg[9:]}")
                st.session_state.running = False
            else:
                st.session_state.log_lines.append(msg)

        for line in st.session_state.log_lines[-60:]:
            st.text(line)
        if st.session_state.running:
            st.info("Processing... click Refresh to update.")

    summary = st.session_state.get("summary")
    if summary:
        st.markdown("---")
        st.subheader("Batch Summary")
        c1, c2 = st.columns(2)
        with c1: st.metric("Processed", summary.get("processed", 0))
        with c2: st.metric("Failed",    summary.get("failed", 0))
        for item in summary.get("items", []):
            icon  = "✅" if item.get("status") == "processed" else "❌"
            agent = item.get("winning_agent", "")
            with st.expander(f"{icon} {item.get('market_name', '')}"):
                if agent:
                    st.markdown(f"Winning agent: {_agent_badge(agent)}", unsafe_allow_html=True)
                st.json(item)


# ═══════════════════════════════════════════════════════════════════════════
# MANAGE BRIEFS TAB
# ═══════════════════════════════════════════════════════════════════════════
with tab_briefs:
    from fmi_batch_factory.briefs import market_name_to_brief

    briefs = _load_briefs()
    seen   = _load_seen()

    # ── Paste market names ────────────────────────────────────────────────
    st.subheader("Add Markets")
    st.caption("Paste up to 10 market names, one per line. Click Add.")

    pasted = st.text_area(
        "Market names",
        placeholder="Closed System Bioprocessing Market\nAmitriptyline Hydrochloride Market\nContinuous Bioprocessing Market",
        height=220,
        label_visibility="collapsed",
    )

    if st.button("➕ Add to Queue", type="primary"):
        lines = [l.strip() for l in pasted.splitlines() if l.strip()][:10]
        existing_names = {b["market_name"].lower() for b in briefs}
        added = []
        for name in lines:
            if name.lower() not in existing_names:
                briefs.append(market_name_to_brief(name))
                existing_names.add(name.lower())
                added.append(name)
        if added:
            _save_briefs(briefs)
            st.success(f"Added {len(added)} market(s): {', '.join(added)}")
            st.rerun()
        else:
            st.info("All names already in queue.")

    # ── Current queue ─────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader(f"Current Queue ({len(briefs)} markets)")

    if not briefs:
        st.info("Queue is empty. Paste market names above.")
    else:
        col_clear, col_reset = st.columns([1, 1])
        with col_clear:
            if st.button("🗑 Clear all markets"):
                _save_briefs([])
                SEEN_PATH.write_text("[]", encoding="utf-8")
                st.success("Queue cleared.")
                st.rerun()
        with col_reset:
            if st.button("🔄 Reset completed (reprocess all)"):
                SEEN_PATH.write_text("[]", encoding="utf-8")
                st.success("All marked as pending again.")
                st.rerun()

        st.markdown("")
        for i, b in enumerate(briefs):
            slug = b.get("market_slug", slugify(b.get("market_name", "")))
            status = "✅ Done" if slug in seen else "⏳ Pending"
            col_name, col_status, col_remove = st.columns([6, 2, 1])
            with col_name:
                st.write(b.get("market_name", ""))
            with col_status:
                st.write(status)
            with col_remove:
                if st.button("✕", key=f"rm_{i}"):
                    briefs.pop(i)
                    _save_briefs(briefs)
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# OUTPUTS TAB
# ═══════════════════════════════════════════════════════════════════════════
with tab_outputs:
    st.subheader("Generated Articles")
    st.info("On Streamlit Cloud, files are temporary. Download the ZIP right after each batch run.")

    docs = _collect_docx()
    if not docs:
        st.write("No DOCX files yet. Run a batch first.")
    else:
        st.download_button(
            f"⬇ Download all {len(docs)} files as ZIP",
            _zip_docx(), "fmi_articles.zip", "application/zip",
        )
        st.markdown("---")
        for f in docs:
            cn, cd = st.columns([5, 1])
            with cn: st.write(f.name)
            with cd:
                with open(f, "rb") as fh:
                    st.download_button("⬇", fh.read(), f.name,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"dl_{f.stem}")

        st.markdown("---")
        st.subheader("Inspect JSON")
        chosen = st.selectbox("Select article", [f.parent.name for f in docs])
        if chosen:
            for fname, lbl in [("article.json", "Article"), ("fact_pack.json", "Fact Pack"),
                                ("evidence_pack.json", "Evidence Pack")]:
                p = OUTPUT_DIR / chosen / fname
                if p.exists():
                    with st.expander(lbl):
                        st.json(json.loads(p.read_text(encoding="utf-8")))
