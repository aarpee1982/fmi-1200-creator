from __future__ import annotations

import json

from .deepseek_client import DeepSeekClient

FACTPACK_SYSTEM = """
You are an FMI market analyst.
Return only valid JSON. No markdown, no explanation.
Use only the supplied market brief and evidence pack.
Proxy-based estimation is allowed when direct market-size data is absent.
Do not invent citations or companies.
"""


def build_factpack_prompt(
    brief: dict,
    evidence_pack: dict,
    foundation_check: dict,
    forecast_start: int,
    forecast_end: int,
) -> str:
    return f"""
Create a market fact pack in JSON using the supplied brief and evidence.

Forecast period: {forecast_start} to {forecast_end}

Return this JSON shape exactly:
{{
  "market_name": "...",
  "market_slug": "...",
  "status": "strong_foundation|moderate_foundation|weak_foundation",
  "confidence_score": 0,
  "value_2026_usd_bn": 0.0,
  "value_{forecast_end}_usd_bn": 0.0,
  "cagr_pct": 0.0,
  "country_cagrs": [{{"country":"...","cagr_pct":0.0,"basis":"..."}}],
  "segment_shares": {{
    "segment_key_1": [{{"segment":"...","share_pct":0.0,"basis":"..."}}],
    "segment_key_2": [{{"segment":"...","share_pct":0.0,"basis":"..."}}],
    "segment_key_3": [{{"segment":"...","share_pct":0.0,"basis":"..."}}]
  }},
  "definition": "...",
  "key_players": ["..."],
  "assumptions": ["..."],
  "method_notes": ["..."],
  "warnings": ["..."],
  "evidence_summary": ["..."]
}}

Rules:
- value_{forecast_end}_usd_bn must be mathematically consistent with value_2026_usd_bn and cagr_pct over {forecast_end - forecast_start} years.
- Use foundation_check.status as the fact-pack status.
- Segment keys should match the market brief's segment dimension names (e.g. dosage_form, product_type, application).
- All values must be positive numbers, never zero or null.
- Keep assumptions and warnings honest.
- If direct market-size observations are absent, infer from proxy evidence and say so in method_notes.

Market brief:
{json.dumps(brief, ensure_ascii=False)}

Foundation check:
{json.dumps(foundation_check, ensure_ascii=False)}

Evidence pack:
{json.dumps(evidence_pack, ensure_ascii=False)}
"""


def build_fact_pack(
    client: DeepSeekClient,
    brief: dict,
    evidence_pack: dict,
    foundation_check: dict,
    forecast_start: int,
    forecast_end: int,
) -> dict:
    prompt = build_factpack_prompt(brief, evidence_pack, foundation_check, forecast_start, forecast_end)
    return client.complete_json(FACTPACK_SYSTEM, prompt, temperature=0.2, max_tokens=4000)
