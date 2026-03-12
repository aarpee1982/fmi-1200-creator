from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

import requests

BLOCKED_DOMAINS = {
    "grandviewresearch.com", "imarcgroup.com", "marketresearchintellect.com",
    "introspectivemarketresearch.com", "flairinsights.com", "wiseguyreports.com",
    "fortunebusinessinsights.com", "marketsandmarkets.com", "precedenceresearch.com",
    "verifiedmarketresearch.com", "coherentmarketinsights.com", "researchandmarkets.com",
    "openpr.com", "globenewswire.com", "prnewswire.com", "businesswire.com", "statista.com",
}

PREFERRED_DOMAIN_KEYWORDS = [
    ".gov", ".edu", "who.int", "fda.gov", "ema.europa.eu", "nih.gov",
    "ncbi.nlm.nih.gov", "cdc.gov", "oecd.org", "worldbank.org", "imf.org",
    "europa.eu", "un.org", "fred.stlouisfed.org", "census.gov", "bea.gov",
    "bls.gov", "trade.gov", "usitc.gov", "comtrade", "wits.worldbank.org",
]

OPENAI_TOP_MODEL = "gpt-4o"


class OpenAIWebSearchClient:
    def __init__(self, api_key: str, search_model: str = "gpt-4o-mini"):
        self.api_key      = api_key
        self.search_model = search_model

    def search_once(self, query: str, allow_company_sources: bool = False) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if allow_company_sources:
            source_guidance = (
                "Search broadly — include company annual reports, investor relations pages, "
                "company press releases, Wikipedia, industry association pages, and public filings "
                "in addition to government sources. The goal is to find ACTUAL COMPANY NAMES, "
                "recent M&A activity, and product launches. Do NOT use commercial market research firms."
            )
        else:
            source_guidance = (
                "Strongly prefer government sites, regulators, multilateral agencies, public statistical bodies, "
                "public health agencies, public trade or customs databases, public prescription datasets, "
                "and first-party public company filings. Do NOT use commercial market-research firms, "
                "press-release syndication sites, or SEO listicles."
            )

        user_prompt = (
            f"{source_guidance} "
            "Return ONLY structured JSON with an array called evidence_cards. "
            "Each card must have: source, publisher, url, date, claim, metric, unit, geography, time_period, "
            "authority_type, numeric_signal, confidence, why_relevant, non_commercial_likely. "
            f"Query: {query}"
        )

        payload = {
            "model": self.search_model,
            "input": user_prompt,
            "tools": [{"type": "web_search"}],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "evidence_cards_response",
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "evidence_cards": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "source":               {"type": "string"},
                                        "publisher":            {"type": "string"},
                                        "url":                  {"type": "string"},
                                        "date":                 {"type": "string"},
                                        "claim":                {"type": "string"},
                                        "metric":               {"type": "string"},
                                        "unit":                 {"type": "string"},
                                        "geography":            {"type": "string"},
                                        "time_period":          {"type": "string"},
                                        "authority_type":       {"type": "string"},
                                        "numeric_signal":       {"type": "string"},
                                        "confidence":           {"type": "string"},
                                        "why_relevant":         {"type": "string"},
                                        "non_commercial_likely": {"type": "boolean"},
                                    },
                                    "required": [
                                        "source", "publisher", "url", "date", "claim",
                                        "metric", "unit", "geography", "time_period",
                                        "authority_type", "numeric_signal", "confidence",
                                        "why_relevant", "non_commercial_likely",
                                    ],
                                },
                            }
                        },
                        "required": ["evidence_cards"],
                    },
                }
            },
        }

        resp = requests.post("https://api.openai.com/v1/responses", headers=headers, json=payload, timeout=300)
        resp.raise_for_status()
        data = resp.json()

        output_text = (data.get("output_text") or "").strip()
        if not output_text:
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for content in item.get("content", []):
                        if content.get("type") in {"output_text", "text"}:
                            output_text = (content.get("text") or "").strip()
                            break
                if output_text:
                    break

        if not output_text:
            raise ValueError(f"OpenAI search returned no output_text. Response: {json.dumps(data)[:2000]}")

        if output_text.startswith("```"):
            output_text = output_text.strip("`")
            if output_text.startswith("json"):
                output_text = output_text[4:].strip()

        parsed = json.loads(output_text)
        cards  = parsed.get("evidence_cards", [])
        filtered = self._filter(cards, allow_company_sources)

        return {
            "evidence_cards":            filtered,
            "raw_evidence_card_count":   len(cards),
            "filtered_evidence_card_count": len(filtered),
        }

    def _filter(self, cards: list[dict], allow_company_sources: bool) -> list[dict]:
        kept = []
        for card in cards:
            url    = (card.get("url") or "").strip()
            domain = self._domain(url)
            card["domain"] = domain

            if self._is_blocked(domain):
                continue

            if allow_company_sources:
                # Relaxed filter — keep anything not on the blocked list
                kept.append(card)
            else:
                # Strict filter — prefer government and authoritative sources
                authority = (card.get("authority_type") or "").strip().lower()
                preferred = any(k in domain for k in PREFERRED_DOMAIN_KEYWORDS) if domain else False
                if authority or preferred or bool(card.get("non_commercial_likely", False)):
                    kept.append(card)

        # Sort: non-commercial first, numeric signal second
        kept.sort(key=lambda c: (
            0 if bool(c.get("non_commercial_likely", False)) else 1,
            0 if str(c.get("numeric_signal", "")).strip() else 1,
        ))
        return kept[:30]

    def _domain(self, url: str) -> str:
        try:
            netloc = urlparse(url).netloc.lower().strip()
            return netloc[4:] if netloc.startswith("www.") else netloc
        except Exception:
            return ""

    def _is_blocked(self, domain: str) -> bool:
        if not domain:
            return False
        return any(domain == b or domain.endswith("." + b) for b in BLOCKED_DOMAINS)


class OpenAIProseClient:
    def __init__(self, api_key: str, model: str = OPENAI_TOP_MODEL):
        self.api_key = api_key
        self.model   = model

    def complete_json(self, system: str, user: str, temperature: float = 0.4, max_tokens: int = 6000) -> dict[str, Any]:
        text = self.complete_text(system, user, temperature=temperature, max_tokens=max_tokens)
        text = (text or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        return json.loads(text)

    def complete_text(self, system: str, user: str, temperature: float = 0.4, max_tokens: int = 6000) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "temperature":     temperature,
            "max_tokens":      max_tokens,
            "response_format": {"type": "json_object"},
        }
        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
