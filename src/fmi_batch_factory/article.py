from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .deepseek_client import DeepSeekClient
from .kimi_client import KimiClient
from .openai_client import OpenAIProseClient
from .style_guide import FULL_STYLE_BLOCK


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def _fmt_bn(v: Any) -> str:
    try:
        return f"USD {float(v):.1f} billion"
    except Exception:
        return "USD 0.0 billion"


def _fmt_pct(v: Any) -> str:
    try:
        return f"{float(v):.1f}%"
    except Exception:
        return "0.0%"


def _title_case(key: str) -> str:
    return str(key).replace("_", " ").title()


def _as_list(v: Any) -> list:
    if v is None: return []
    if isinstance(v, list): return v
    if isinstance(v, dict): return [v]
    if isinstance(v, str): return [v] if v.strip() else []
    return []


def _norm_segments(v: Any) -> list[dict]:
    rows = []
    for item in _as_list(v):
        if isinstance(item, dict):
            rows.append({
                "segment": item.get("segment") or item.get("name") or item.get("label") or "",
                "share_pct": item.get("share_pct") or item.get("share") or "",
            })
        elif isinstance(item, str):
            rows.append({"segment": item, "share_pct": ""})
    return [r for r in rows if r.get("segment")]


def _norm_countries(v: Any) -> list[dict]:
    rows = []
    for item in _as_list(v):
        if isinstance(item, dict):
            rows.append({
                "country": item.get("country") or item.get("name") or "",
                "cagr_pct": item.get("cagr_pct") or item.get("cagr") or "",
            })
    return [r for r in rows if r.get("country")]


def _norm_strings(v: Any) -> list[str]:
    out = []
    for item in _as_list(v):
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, dict):
            name = item.get("name") or item.get("company") or item.get("title") or item.get("source")
            if isinstance(name, str) and name.strip():
                out.append(name.strip())
    return out


def _segmentation_line(fact_pack: dict) -> str:
    ss = fact_pack.get("segment_shares", {}) or {}
    labels = [_title_case(k) for k in ss.keys()] if isinstance(ss, dict) else []
    if "Region" not in labels:
        labels.append("Region")
    if len(labels) == 1: return f"By {labels[0]}"
    if len(labels) == 2: return f"By {labels[0]} and {labels[1]}"
    return f"By {', '.join(labels[:-1])}, and {labels[-1]}"


def _country_cagr_rows(fact_pack: dict) -> list[dict]:
    rows = []
    for item in _norm_countries(fact_pack.get("country_cagrs", [])):
        country = item["country"]
        cagr = item["cagr_pct"]
        if country and cagr not in ("", None):
            try:
                rows.append({"country": country, "cagr": f"{float(cagr):.1f}%"})
            except Exception:
                pass
    return rows[:10]


def _leading_segments(fact_pack: dict) -> list[dict]:
    """Return the leading segment per dimension with share."""
    ss = fact_pack.get("segment_shares", {}) or {}
    leads = []
    if isinstance(ss, dict):
        for dim, vals in ss.items():
            normalized = _norm_segments(vals)
            if normalized:
                lead = normalized[0]
                leads.append({
                    "dimension": _title_case(dim),
                    "segment": lead.get("segment", ""),
                    "share_pct": lead.get("share_pct", ""),
                })
    return leads


# ---------------------------------------------------------------------------
# Deterministic sections
# ---------------------------------------------------------------------------

def _det_scope(fact_pack: dict, forecast_start: int, forecast_end: int) -> dict:
    ss = fact_pack.get("segment_shares", {}) or {}
    seg_keys = list(ss.keys()) if isinstance(ss, dict) else []

    rows = [
        {"metric": "Market Value", "value": f"{_fmt_bn(fact_pack.get('value_2026_usd_bn'))} in 2026 to {_fmt_bn(fact_pack.get(f'value_{forecast_end}_usd_bn'))} by {forecast_end}"},
        {"metric": "CAGR", "value": f"{_fmt_pct(fact_pack.get('cagr_pct'))} from {forecast_start} to {forecast_end}"},
        {"metric": "Base Year", "value": "2025"},
        {"metric": "Forecast Period", "value": f"{forecast_start} to {forecast_end}"},
    ]
    for k in seg_keys:
        normalized = _norm_segments(ss[k])
        segs = [x["segment"] for x in normalized if x.get("segment")]
        rows.append({"metric": f"{_title_case(k)} Segmentation", "value": ", ".join(segs)})

    rows.append({"metric": "Regions Covered", "value": "North America, Latin America, Europe, East Asia, South Asia Pacific, Middle East and Africa"})

    return {"heading": "Scope of the Report", "table_rows": rows}


def _det_key_players(fact_pack: dict) -> dict:
    players = [p for p in _norm_strings(fact_pack.get("key_players", [])) if "various" not in p.lower()]
    return {"heading": f"Key Players in {fact_pack.get('market_name', 'Market')}", "items": players[:12]}


def _det_faqs(fact_pack: dict, forecast_end: int) -> list[dict]:
    """Build the base required FAQs. AI will extend these."""
    market = fact_pack.get("market_name", "market")
    v2025 = _fmt_bn(fact_pack.get("value_2025_usd_bn") or fact_pack.get("value_2026_usd_bn"))
    vend = _fmt_bn(fact_pack.get(f"value_{forecast_end}_usd_bn"))
    cagr = _fmt_pct(fact_pack.get("cagr_pct"))
    return [
        {"question": f"How large is the {market} in 2025?",
         "answer": f"The global {market} is estimated at {v2025} in 2025."},
        {"question": f"What will be the {market} size by {forecast_end}?",
         "answer": f"The {market} is projected to reach {vend} by {forecast_end}."},
        {"question": "What is the expected growth rate during the forecast period?",
         "answer": f"The {market} is projected to expand at a CAGR of {cagr} from 2026 to {forecast_end}."},
    ]


def _det_bibliography(fact_pack: dict, evidence_pack: dict) -> dict:
    items = [x for x in _norm_strings(fact_pack.get("bibliography_items", [])) if x]
    blocked = ("stats n data", "proprietary", "primary research", "grand view", "imarc",
               "market research future", "verified market", "fortune business")
    if not items:
        cards = evidence_pack.get("evidence_cards", []) if isinstance(evidence_pack, dict) else []
        seen: set[str] = set()
        for card in cards:
            if not isinstance(card, dict) or not card.get("non_commercial_likely"):
                continue
            publisher = (card.get("publisher") or card.get("source") or "").strip()
            date = (card.get("date") or "").strip()
            claim = (card.get("claim") or "").strip()
            url = (card.get("url") or "").strip()
            # format as proper citation
            year = date[:4] if len(date) >= 4 else date
            text = f"{publisher}. {year}. {claim[:120]}."
            low = text.lower()
            if not publisher or text in seen:
                continue
            if any(b in low for b in blocked):
                continue
            seen.add(text)
            items.append(text)
            if len(items) >= 7:
                break
    return {"heading": "Bibliography", "items": items[:7]}


# ---------------------------------------------------------------------------
# AI prose prompt — one prompt that covers the whole article
# ---------------------------------------------------------------------------

PROSE_SYSTEM = f"""
You are a senior analyst at Future Market Insights (FMI) writing a professional market research article.
Return ONLY valid JSON. No markdown. No preamble. No explanation outside the JSON.

{FULL_STYLE_BLOCK}
"""


def _build_prose_prompt(fact_pack: dict, forecast_start: int, forecast_end: int) -> str:
    market = fact_pack.get("market_name", "Market")
    v2025 = _fmt_bn(fact_pack.get("value_2025_usd_bn") or fact_pack.get("value_2026_usd_bn"))
    v2026 = _fmt_bn(fact_pack.get("value_2026_usd_bn"))
    vend  = _fmt_bn(fact_pack.get(f"value_{forecast_end}_usd_bn"))
    cagr  = _fmt_pct(fact_pack.get("cagr_pct"))

    leads = _leading_segments(fact_pack)
    leads_text = "\n".join(
        f"  - {l['dimension']}: {l['segment']} leads with {l['share_pct']}% share in 2026"
        for l in leads
    ) or "  - Segment share data not available"

    country_rows = _country_cagr_rows(fact_pack)
    country_text = "\n".join(f"  - {r['country']}: {r['cagr']} CAGR" for r in country_rows) or "  - Country data not available"

    ss = fact_pack.get("segment_shares", {}) or {}
    seg_dims = []
    if isinstance(ss, dict):
        for dim, vals in ss.items():
            normalized = _norm_segments(vals)
            segs = [x["segment"] for x in normalized]
            seg_dims.append(f"{_title_case(dim)}: {', '.join(segs)}")

    key_players = _norm_strings(fact_pack.get("key_players", []))

    return f"""
Write a complete FMI market research article for: {market}

NUMBERS — use these exactly, do not change them:
- 2025 market value: {v2025}
- 2026 market value: {v2026}
- {forecast_end} market value: {vend}
- CAGR: {cagr} from {forecast_start} to {forecast_end}

LEADING SEGMENTS (use in opening block and segmental analysis):
{leads_text}

COUNTRY GROWTH RATES (use in regional analysis):
{country_text}

SEGMENT DIMENSIONS (use in Key Segments Analyzed and Scope):
{chr(10).join(seg_dims)}

KEY PLAYERS available:
{', '.join(key_players[:12]) if key_players else 'Not specified'}

FACT PACK (use for context, drivers, definition, methodology):
{json.dumps(fact_pack, ensure_ascii=False)[:3000]}

Return ONLY this JSON structure:

{{
  "opening_paragraph": "One dense paragraph with 2025 value, 2026 value, {forecast_end} value, CAGR, and leading segment shares per dimension.",

  "summary_key_drivers": [
    "Label: One sentence explanation.",
    "Label: One sentence explanation.",
    "Label: One sentence explanation.",
    "Label: One sentence explanation."
  ],

  "summary_key_segments": [
    "Dimension 1: segment A, segment B, segment C, ...",
    "Dimension 2: segment A, segment B, ...",
    "Region: North America, Latin America, Europe, East Asia, South Asia Pacific, Middle East and Africa"
  ],

  "summary_analyst_opinion": "[Analyst Name], [Title] at FMI says, \\"[Specific insight about where value sits in this market. Market-specific. Not generic.]\\"",

  "market_definition_paragraph": "One clear paragraph on what the market covers — product categories, operations, manufacturing environments. No bullets.",

  "inclusions_bullets": [
    "Specific inclusion 1",
    "Specific inclusion 2",
    "Specific inclusion 3"
  ],

  "exclusions_bullets": [
    "Specific exclusion 1",
    "Specific exclusion 2",
    "Specific exclusion 3"
  ],

  "methodology_paragraph": "One paragraph on how the market was sized — base year, evidence inputs, triangulation approach. Specific to this market.",

  "drivers_paragraph": "One prose paragraph covering 4-5 demand forces specific to this market. Name specific regulations, therapy types, operational pressures. NO bullets.",

  "restraints_paragraph": "One prose paragraph covering 3-4 friction points: supply concerns, validation costs, switching barriers. NO bullets.",

  "trends_paragraph": "One prose paragraph covering 2-4 structural shifts: how buyer behavior and supplier positioning are changing. NO bullets.",

  "segmental_analysis": [
    {{
      "subheading": "{market} Analysis by [Dimension Name]",
      "paragraph": "One prose paragraph. State which segment leads with its exact share %. Explain WHY with a specific operational or commercial reason. Cite a company or regulatory reference if possible. NO bullets."
    }}
  ],

  "competitive_aligners_para1": "What actually wins in this market. What buyers require. Name 1-2 specific companies and what they signal about competitive dynamics.",

  "competitive_aligners_para2": "How competitive advantage is shifting. Name specific M&A, partnerships, or moves. End with what market leadership is being built around.",

  "strategic_outlook_paragraph": "FMI house view on where this market goes next. Specific to this market's structural dynamics. What shift is underway. What determines who wins.",

  "additional_faqs": [
    {{
      "question": "Which [dimension 1] leads the {market}?",
      "answer": "..."
    }},
    {{
      "question": "Which [dimension 2] is dominant in the {market}?",
      "answer": "..."
    }},
    {{
      "question": "Which end-user segment contributes the largest share?",
      "answer": "..."
    }},
    {{
      "question": "Which region is the largest market for [market name short]?",
      "answer": "..."
    }},
    {{
      "question": "Which region grows the fastest in the {market}?",
      "answer": "..."
    }},
    {{
      "question": "What is the main structural shift in the {market}?",
      "answer": "..."
    }},
    {{
      "question": "Why do [key commercial dynamic, e.g. recurring consumables] matter so much in the {market}?",
      "answer": "..."
    }}
  ]
}}

CRITICAL RULES:
- opening_paragraph MUST include all 3 values (2025, 2026, {forecast_end}) AND leading segment shares
- drivers_paragraph, restraints_paragraph, trends_paragraph: PROSE ONLY — no bullets, no numbered lists
- segmental_analysis paragraph entries: PROSE ONLY — no bullets
- competitive_aligners paragraphs: PROSE ONLY — no bullets
- Do not invent market numbers. Use only the numbers provided above.
- Do not use em dashes anywhere
- Analyst opinion must name a specific analyst (use "Sabyasachi Ghosh, Principal Consultant" if no name in fact pack)
- additional_faqs must be specific to this market's segments and dynamics — not generic
"""


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

def _score_prose(result: dict) -> float:
    if not isinstance(result, dict):
        return -999.0

    score = 0.0
    text = json.dumps(result)

    penalties = [
        " — ", "\u2014", "not only this but also", "furthermore,",
        "additionally,", "moreover,", "data limitations", "not quantified",
        "high uncertainty", "modelled analyst estimate", "working note",
        "it is worth noting", "it should be noted",
    ]
    for p in penalties:
        score -= text.lower().count(p.lower()) * 2.0

    required = [
        "opening_paragraph", "summary_key_drivers", "summary_key_segments",
        "summary_analyst_opinion", "market_definition_paragraph",
        "inclusions_bullets", "exclusions_bullets", "methodology_paragraph",
        "drivers_paragraph", "restraints_paragraph", "trends_paragraph",
        "segmental_analysis", "competitive_aligners_para1",
        "competitive_aligners_para2", "strategic_outlook_paragraph",
        "additional_faqs",
    ]
    for k in required:
        if k in result and result[k]:
            score += 4.0

    score += min(len(text) / 500, 15.0)

    # Penalize bullet-style content in prose sections
    for prose_key in ["drivers_paragraph", "restraints_paragraph", "trends_paragraph"]:
        val = result.get(prose_key, "")
        if isinstance(val, list):
            score -= 10.0  # supposed to be a string, not a list

    return score


# ---------------------------------------------------------------------------
# Parallel agent runner
# ---------------------------------------------------------------------------

def _run_agent(client: Any, system: str, prompt: str, label: str) -> tuple[str, dict, float]:
    try:
        result = client.complete_json(system, prompt, temperature=0.4, max_tokens=7000)
        quality = _score_prose(result)
        return label, result, quality
    except Exception as e:
        return label, {}, -999.0


def _build_prose_parallel(
    ds_client: DeepSeekClient,
    kimi_client: KimiClient,
    openai_prose_client: OpenAIProseClient,
    fact_pack: dict,
    forecast_start: int,
    forecast_end: int,
) -> tuple[dict, str]:
    prompt = _build_prose_prompt(fact_pack, forecast_start, forecast_end)
    agents = [
        (ds_client, "DeepSeek"),
        (kimi_client, "Kimi"),
        (openai_prose_client, "OpenAI-GPT4o"),
    ]
    results = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(_run_agent, client, PROSE_SYSTEM, prompt, label): label
                   for client, label in agents}
        for fut in as_completed(futures):
            results.append(fut.result())

    results.sort(key=lambda x: x[2], reverse=True)
    return results[0][1], results[0][0]


# ---------------------------------------------------------------------------
# Sanitizer
# ---------------------------------------------------------------------------

def _sanitize(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _sanitize(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_sanitize(v) for v in node]
    if isinstance(node, str):
        replacements = {
            " — ": ", ", "\u2014": ",",
            "modelled analyst estimate": "market estimate",
            "data limitations": "available market evidence",
            "not quantified": "not separately disclosed",
            "high uncertainty": "measured visibility",
            "working note": "market note",
            "internal note": "market note",
        }
        for old, new in replacements.items():
            node = node.replace(old, new)
        return node
    return node


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_article(
    ds_client: DeepSeekClient,
    kimi_client: KimiClient,
    openai_prose_client: OpenAIProseClient,
    fact_pack: dict,
    evidence_pack: dict,
    forecast_start: int,
    forecast_end: int,
) -> dict:
    market = fact_pack.get("market_name", "Market")

    prose, winning_agent = _build_prose_parallel(
        ds_client, kimi_client, openai_prose_client, fact_pack, forecast_start, forecast_end
    )

    # Base required FAQs (deterministic) + AI-generated additional FAQs
    base_faqs = _det_faqs(fact_pack, forecast_end)
    extra_faqs = prose.get("additional_faqs", [])
    if isinstance(extra_faqs, list):
        all_faqs = base_faqs + [f for f in extra_faqs if isinstance(f, dict)]
    else:
        all_faqs = base_faqs

    article = {
        "market_name": market,
        "winning_agent": winning_agent,
        "sections": {

            # Title / segmentation line (used by renderer for H1 and subtitle)
            "title_block": {
                "h1_title": market,
                "segmentation_line": _segmentation_line(fact_pack),
                "forecast_period": f"{forecast_start} to {forecast_end}",
            },

            # Section 1 — Opening block
            "opening_block": {
                "heading": f"{market} Size and Share Forecast Outlook By FMI",
                "paragraph": prose.get("opening_paragraph", ""),
            },

            # Section 2 — Summary
            "summary": {
                "heading": f"Summary of {market}",
                "key_drivers_heading": "Key Drivers",
                "key_drivers": prose.get("summary_key_drivers", []),
                "key_segments_heading": "Key Segments Analyzed in the Report",
                "key_segments": prose.get("summary_key_segments", []),
                "analyst_opinion_heading": "Analyst Opinion",
                "analyst_opinion": prose.get("summary_analyst_opinion", ""),
            },

            # Section 3 — Definition
            "market_definition": {
                "heading": f"{market} Definition",
                "paragraph": prose.get("market_definition_paragraph", ""),
            },

            # Section 4 — Inclusions
            "inclusions": {
                "heading": f"{market} Inclusions",
                "bullets": prose.get("inclusions_bullets", []),
            },

            # Section 5 — Exclusions
            "exclusions": {
                "heading": f"{market} Exclusions",
                "bullets": prose.get("exclusions_bullets", []),
            },

            # Section 6 — Methodology
            "methodology": {
                "heading": f"{market} Research Methodology",
                "paragraph": prose.get("methodology_paragraph", ""),
            },

            # Section 7 — Drivers, Restraints, Trends
            "market_dynamics": {
                "heading": f"Key Drivers, Restraints, and Trends in {market}",
                "drivers_heading": "Drivers",
                "drivers_paragraph": prose.get("drivers_paragraph", ""),
                "restraints_heading": "Restraints",
                "restraints_paragraph": prose.get("restraints_paragraph", ""),
                "trends_heading": "Trends",
                "trends_paragraph": prose.get("trends_paragraph", ""),
            },

            # Section 8 — Segmental Analysis
            "segmental_analysis": {
                "heading": "Segmental Analysis",
                "items": prose.get("segmental_analysis", []),
            },

            # Section 9 — Competitive Aligners
            "competitive_aligners": {
                "heading": "Competitive Aligners for Market Players",
                "paragraph_1": prose.get("competitive_aligners_para1", ""),
                "paragraph_2": prose.get("competitive_aligners_para2", ""),
            },

            # Section 10 — Key Players
            "key_players": _det_key_players(fact_pack),

            # Section 11 — Strategic Outlook
            "strategic_outlook": {
                "heading": f"Strategic Outlook by FMI on {market}",
                "paragraph": prose.get("strategic_outlook_paragraph", ""),
            },

            # Section 12 — Scope
            "scope_of_report": _det_scope(fact_pack, forecast_start, forecast_end),

            # Section 13 — Bibliography
            "bibliography": _det_bibliography(fact_pack, evidence_pack),

            # Section 14 — FAQs
            "faqs": {
                "heading": "Frequently Asked Questions",
                "items": all_faqs,
            },
        },
    }

    return _sanitize(article)
