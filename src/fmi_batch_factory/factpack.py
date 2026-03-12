from __future__ import annotations

import json

from .openai_client import OpenAIReasoningClient

FACTPACK_SYSTEM = """
You are a senior FMI market analyst. Return only valid JSON. No markdown, no explanation.
You have deep knowledge of global industry markets. Use that knowledge to fill gaps when evidence is thin.
Never write "generic manufacturers", "various companies", "Type A", "Type B", "Segment 1", or placeholder text.
Every field must contain real, specific, accurate information for this exact market.
"""


def build_factpack_prompt(
    brief: dict,
    evidence_pack: dict,
    foundation_check: dict,
    forecast_start: int,
    forecast_end: int,
) -> str:
    cards = evidence_pack.get("evidence_cards", [])
    company_mentions = []
    for card in cards:
        claim     = card.get("claim", "")
        publisher = card.get("publisher", "")
        if publisher and not any(x in publisher.lower() for x in ["government", "who", "fda", "ema", "cdc", "nih", "ministry"]):
            company_mentions.append(publisher)
        if any(w in claim.lower() for w in ["acquired", "launched", "partnership", "revenue", "market share", "announced"]):
            company_mentions.append(claim[:200])

    company_context = "\n".join(set(company_mentions[:20])) if company_mentions else "Use your knowledge of this market."
    years = forecast_end - forecast_start
    market = brief.get("market_name", "")

    return f"""
Build a complete market fact pack for: {market}
Forecast period: {forecast_start} to {forecast_end} ({years} years)

STEP 1 — DETERMINE REAL SEGMENTS:
Based on your knowledge of the {market}, identify the 3 most important segmentation dimensions used in industry analysis.
For each dimension, list the real segment names used in this market (not placeholders like "Type A").
Example for a pharma market: dimensions would be "dosage_form", "indication", "distribution_channel"
Example for a bioprocessing market: dimensions would be "product_type", "workflow", "end_user"

COMPANY NAMES FROM EVIDENCE:
{company_context}

RULES:
- key_players: REAL named companies only. Minimum 6. Use your training knowledge.
- segment names: REAL industry-standard names for this specific market. No placeholders.
- segment shares must sum to ~100% within each dimension.
- bibliography_items: real citable sources only. Format: "Organization. Year. Title."

Return this exact JSON:
{{
  "market_name": "{market}",
  "market_slug": "{brief.get('market_slug', '')}",
  "status": "moderate_foundation",
  "confidence_score": 70,
  "value_2025_usd_bn": 0.0,
  "value_2026_usd_bn": 0.0,
  "value_{forecast_end}_usd_bn": 0.0,
  "cagr_pct": 0.0,
  "country_cagrs": [
    {{"country": "United States", "cagr_pct": 0.0, "basis": "..."}},
    {{"country": "Germany", "cagr_pct": 0.0, "basis": "..."}},
    {{"country": "China", "cagr_pct": 0.0, "basis": "..."}},
    {{"country": "India", "cagr_pct": 0.0, "basis": "..."}},
    {{"country": "United Kingdom", "cagr_pct": 0.0, "basis": "..."}},
    {{"country": "Brazil", "cagr_pct": 0.0, "basis": "..."}}
  ],
  "segment_shares": {{
    "real_dimension_1_name": [
      {{"segment": "Real Segment Name A", "share_pct": 0.0, "basis": "..."}},
      {{"segment": "Real Segment Name B", "share_pct": 0.0, "basis": "..."}},
      {{"segment": "Real Segment Name C", "share_pct": 0.0, "basis": "..."}}
    ],
    "real_dimension_2_name": [
      {{"segment": "Real Segment Name A", "share_pct": 0.0, "basis": "..."}},
      {{"segment": "Real Segment Name B", "share_pct": 0.0, "basis": "..."}}
    ],
    "real_dimension_3_name": [
      {{"segment": "Real Segment Name A", "share_pct": 0.0, "basis": "..."}},
      {{"segment": "Real Segment Name B", "share_pct": 0.0, "basis": "..."}},
      {{"segment": "Real Segment Name C", "share_pct": 0.0, "basis": "..."}}
    ]
  }},
  "definition": "One clear paragraph defining what this market covers.",
  "key_players": [
    "Real Company Name 1",
    "Real Company Name 2",
    "Real Company Name 3",
    "Real Company Name 4",
    "Real Company Name 5",
    "Real Company Name 6"
  ],
  "bibliography_items": [
    "Organization. Year. Title.",
    "Organization. Year. Title."
  ],
  "assumptions": ["..."],
  "method_notes": ["..."],
  "warnings": ["..."],
  "evidence_summary": ["..."]
}}

Math check: value_{forecast_end}_usd_bn = value_2026_usd_bn * (1 + cagr_pct/100)^{years}

Evidence pack summary (first 3000 chars):
{json.dumps(evidence_pack, ensure_ascii=False)[:3000]}
"""


def build_fact_pack(
    client: OpenAIReasoningClient,
    brief: dict,
    evidence_pack: dict,
    foundation_check: dict,
    forecast_start: int,
    forecast_end: int,
) -> dict:
    prompt = build_factpack_prompt(brief, evidence_pack, foundation_check, forecast_start, forecast_end)
    return client.complete_json(FACTPACK_SYSTEM, prompt, max_tokens=8000)
