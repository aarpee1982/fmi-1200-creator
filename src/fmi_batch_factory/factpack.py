from __future__ import annotations

import json

from .deepseek_client import DeepSeekClient

FACTPACK_SYSTEM = """
You are a senior FMI market analyst building a structured fact pack.
Return only valid JSON. No markdown, no explanation.
Proxy-based estimation is allowed when direct market-size data is absent — say so in method_notes.
Do not invent citations. Do NOT write "generic manufacturers" or "various companies" for key_players.
"""


def build_factpack_prompt(
    brief: dict,
    evidence_pack: dict,
    foundation_check: dict,
    forecast_start: int,
    forecast_end: int,
) -> str:
    # Extract company mentions from evidence cards to help DeepSeek
    cards = evidence_pack.get("evidence_cards", [])
    company_mentions = []
    for card in cards:
        claim = card.get("claim", "")
        publisher = card.get("publisher", "")
        # Include publisher if it looks like a company (not a government body)
        if publisher and not any(x in publisher.lower() for x in ["government", "who", "fda", "ema", "cdc", "nih", "ministry"]):
            company_mentions.append(publisher)
        # Pull company names from claims
        if any(word in claim.lower() for word in ["acquired", "launched", "partnership", "revenue", "market share", "announced"]):
            company_mentions.append(claim[:200])

    company_context = "\n".join(set(company_mentions[:20])) if company_mentions else "None found in evidence — use your training knowledge of this market."

    years = forecast_end - forecast_start

    return f"""
Build a complete market fact pack for: {brief.get("market_name")}
Forecast period: {forecast_start} to {forecast_end} ({years} years)

COMPANY NAMES FOUND IN EVIDENCE (use these for key_players):
{company_context}

IMPORTANT RULE FOR key_players:
- List ACTUAL named companies (e.g. "Teva Pharmaceuticals", "Sartorius AG", "Thermo Fisher Scientific")
- Use your training knowledge of who the real players are in this market
- Never write "generic manufacturers", "various companies", or "major players"
- Minimum 6 specific company names, up to 12

Return this exact JSON shape:
{{
  "market_name": "...",
  "market_slug": "...",
  "status": "strong_foundation|moderate_foundation|weak_foundation",
  "confidence_score": 0,
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
    "segment_dim_1": [{{"segment": "...", "share_pct": 0.0, "basis": "..."}}],
    "segment_dim_2": [{{"segment": "...", "share_pct": 0.0, "basis": "..."}}],
    "segment_dim_3": [{{"segment": "...", "share_pct": 0.0, "basis": "..."}}]
  }},
  "definition": "...",
  "key_players": [
    "Company Name 1",
    "Company Name 2",
    "Company Name 3",
    "Company Name 4",
    "Company Name 5",
    "Company Name 6"
  ],
  "bibliography_items": [
    "Organization. Year. Title of document.",
    "Organization. Year. Title of document."
  ],
  "assumptions": ["..."],
  "method_notes": ["..."],
  "warnings": ["..."],
  "evidence_summary": ["..."]
}}

Validation rules:
- value_{forecast_end}_usd_bn must equal value_2026_usd_bn * (1 + cagr_pct/100)^{years} — check the math.
- value_2025_usd_bn should be slightly less than value_2026_usd_bn.
- All segment_shares within each dimension must sum to approximately 100%.
- country_cagrs must include all priority countries from the brief.
- key_players must be REAL named companies, minimum 6.
- bibliography_items: only real citable sources (regulatory bodies, company filings, government agencies). Format: "Organization. Year. Title."

Market brief:
{json.dumps(brief, ensure_ascii=False)}

Foundation check:
{json.dumps(foundation_check, ensure_ascii=False)}

Evidence pack (first 4000 chars):
{json.dumps(evidence_pack, ensure_ascii=False)[:4000]}
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
    return client.complete_json(FACTPACK_SYSTEM, prompt, temperature=0.2, max_tokens=5000)
