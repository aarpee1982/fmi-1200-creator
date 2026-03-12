"""
FMI 1200 Creator — Streamlit UI
OpenAI only: gpt-4o-mini for search, o3-mini for reasoning, gpt-4o for prose.
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

ENV_DEFAULTS = {"OPENAI_API_KEY": ""}

def _load_env() -> dict:
    cfg = dict(ENV_DEFAULTS)
    try:
        for k in cfg:
            if k in st.secrets:
                cfg[k] = st.secrets[k]
    except Exception:
        pass
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
    try:
        ENV_PATH.write_text("\n".join(f"{k}={v}" for k, v in cfg.items()), encoding="utf-8")
    except Exception:
        pass

def _keys_complete(cfg: dict) -> bool:
    return bool(cfg.get("OPENAI_API_KEY"))

st.set_page_config(page_title="FMI 1200 Creator", page_icon="📝", layout="wide")

st.markdown("""
<style>
.main-header { font-size:2rem; font-weight:700; color:#1a56db; margin-bottom:0.2rem; }
.sub-header  { color:#6b7280; margin-bottom:1.5rem; font-size:0.95rem; }
.metric-box  { background:#f0f4f8; border-radius:10px; padding:1rem; text-align:center; border:1px solid #e2e8f0; }
.metric-num  { font-size:2rem; font-weight:700; color:#1a56db; }
.metric-lbl  { font-size:0.82rem; color:#6b7280; margin-top:2px; }
</style>
""", unsafe_allow_html=True)

if "env_cfg"   not in st.session_state: st.session_state["env_cfg"]   = _load_env()
if "running"   not in st.session_state: st.session_state["running"]   = False
if "log_lines" not in st.session_state: st.session_state["log_lines"] = []
if "summary"   not in st.session_state: st.session_state["summary"]   = None
if "log_queue" not in st.session_state: st.session_state["log_queue"] = queue.Queue()

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

def _start_batch(openai_key: str, batch_size: int, concurrency: int) -> None:
    st.session_state.running   = True
    st.session_state.log_lines = []
    st.session_state.summary   = None
    log_q: queue.Queue = st.session_state.log_queue
    def _log(msg): log_q.put(msg)
    def _worker():
        try:
            s = run_batch(
                briefs_path=BRIEFS_PATH, output_dir=OUTPUT_DIR, seen_path=SEEN_PATH,
                openai_key=openai_key,
                log=_log, batch_size=batch_size, concurrency=concurrency,
            )
            log_q.put(f"__DONE__{json.dumps(s)}")
        except Exception as e:
            log_q.put(f"__ERROR__{e}")
    threading.Thread(target=_worker, daemon=True).start()

st.markdown('<div class="main-header">📝 FMI 1200 Creator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">OpenAI powered · gpt-4o-mini search · o3-mini reasoning · gpt-4o prose</div>', unsafe_allow_html=True)

tab_settings, tab_run, tab_briefs, tab_outputs = st.tabs(["⚙ Settings", "▶ Run Batch", "📋 Manage Briefs", "📁 Outputs"])

with tab_settings:
    st.subheader("API Configuration")
    is_cloud = False
    try:
        is_cloud = bool(st.secrets.get("OPENAI_API_KEY"))
    except Exception:
        pass
    if is_cloud:
        st.info("Running on Streamlit Cloud. Key loaded from Secrets. To update: share.streamlit.io → your app → Settings → Secrets.")
    env = st.session_state["env_cfg"]
    v_oai_key = st.text_input("OpenAI API Key", value=env["OPENAI_API_KEY"], type="password", key="f_oai_key")
    st.caption("One key powers everything: gpt-4o-mini for web search, o3-mini for market reasoning, gpt-4o for article writing.")
    st.markdown("")
    if _keys_complete(env):
        st.success("Key set. Ready to run.")
    else:
        st.warning("No OpenAI key found.")
    if not is_cloud:
        if st.button("💾 Save", type="primary"):
            new_cfg = {"OPENAI_API_KEY": v_oai_key}
            _save_env(new_cfg)
            st.session_state["env_cfg"] = new_cfg
            st.success("Saved.")
            st.rerun()

with tab_run:
    env     = st.session_state["env_cfg"]
    keys_ok = _keys_complete(env)
    if not keys_ok:
        st.warning("Go to Settings and enter your OpenAI API key.")
    briefs  = _load_briefs()
    seen    = _load_seen()
    pending = [b for b in briefs if b.get("market_slug", slugify(b.get("market_name",""))) not in seen]
    m1,m2,m3,m4 = st.columns(4)
    for col,num,lbl in [(m1,len(briefs),"Total"),(m2,len(pending),"Pending"),(m3,len(seen),"Completed"),(m4,len(_collect_docx()),"DOCX Files")]:
        with col:
            st.markdown(f'<div class="metric-box"><div class="metric-num">{num}</div><div class="metric-lbl">{lbl}</div></div>', unsafe_allow_html=True)
    st.markdown("")
    c1,c2 = st.columns(2)
    with c1: batch_size  = st.slider("Batch size", 1, 10, 5)
    with c2: concurrency = st.slider("Concurrency", 1, 3, 2)
    st.caption("Each article: 5 web searches → o3-mini reasoning → gpt-4o prose.")
    bc,rc = st.columns([2,1])
    with bc:
        if st.button("▶ Start Batch", disabled=(not keys_ok or st.session_state.running or not pending), use_container_width=True, type="primary"):
            _start_batch(env["OPENAI_API_KEY"], batch_size, concurrency)
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
        c1,c2 = st.columns(2)
        with c1: st.metric("Processed", summary.get("processed",0))
        with c2: st.metric("Failed", summary.get("failed",0))
        for item in summary.get("items",[]):
            icon = "✅" if item.get("status")=="processed" else "❌"
            with st.expander(f"{icon} {item.get('market_name','')}"):
                st.json(item)

with tab_briefs:
    from fmi_batch_factory.briefs import market_name_to_brief
    briefs = _load_briefs()
    seen   = _load_seen()
    st.subheader("Add Markets")
    st.caption("Paste up to 10 market names, one per line. Click Add.")
    pasted = st.text_area(
        "Market names",
        placeholder="Closed System Bioprocessing Market\nAmitriptyline Hydrochloride Market",
        height=220,
        label_visibility="collapsed",
    )
    if st.button("➕ Add to Queue", type="primary"):
        lines = [l.strip() for l in pasted.splitlines() if l.strip()][:10]
        existing = {b["market_name"].lower() for b in briefs}
        added = []
        for name in lines:
            if name.lower() not in existing:
                briefs.append(market_name_to_brief(name))
                existing.add(name.lower())
                added.append(name)
        if added:
            _save_briefs(briefs)
            st.success(f"Added {len(added)} market(s).")
            st.rerun()
        else:
            st.info("All names already in queue.")
    st.markdown("---")
    st.subheader(f"Current Queue ({len(briefs)} markets)")
    if not briefs:
        st.info("Queue is empty. Paste market names above.")
    else:
        col_clear, col_reset = st.columns(2)
        with col_clear:
            if st.button("🗑 Clear all"):
                _save_briefs([])
                SEEN_PATH.write_text("[]", encoding="utf-8")
                st.success("Cleared.")
                st.rerun()
        with col_reset:
            if st.button("🔄 Reset completed"):
                SEEN_PATH.write_text("[]", encoding="utf-8")
                st.success("All marked pending.")
                st.rerun()
        st.markdown("")
        for i, b in enumerate(briefs):
            slug = b.get("market_slug", slugify(b.get("market_name","")))
            status = "✅ Done" if slug in seen else "⏳ Pending"
            col_name, col_status, col_remove = st.columns([6,2,1])
            with col_name: st.write(b.get("market_name",""))
            with col_status: st.write(status)
            with col_remove:
                if st.button("✕", key=f"rm_{i}"):
                    briefs.pop(i); _save_briefs(briefs); st.rerun()

with tab_outputs:
    st.subheader("Generated Articles")
    st.info("On Streamlit Cloud, files are temporary. Download ZIP immediately after each batch run.")
    docs = _collect_docx()
    if not docs:
        st.write("No DOCX files yet. Run a batch first.")
    else:
        st.download_button(f"⬇ Download all {len(docs)} as ZIP", _zip_docx(), "fmi_articles.zip", "application/zip")
        st.markdown("---")
        for f in docs:
            cn,cd = st.columns([5,1])
            with cn: st.write(f.name)
            with cd:
                with open(f,"rb") as fh:
                    st.download_button("⬇", fh.read(), f.name,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"dl_{f.stem}")
        st.markdown("---")
        st.subheader("Inspect JSON")
        chosen = st.selectbox("Select article", [f.parent.name for f in docs])
        if chosen:
            for fname,lbl in [("article.json","Article"),("fact_pack.json","Fact Pack"),("evidence_pack.json","Evidence Pack")]:
                p = OUTPUT_DIR / chosen / fname
                if p.exists():
                    with st.expander(lbl):
                        st.json(json.loads(p.read_text(encoding="utf-8")))
