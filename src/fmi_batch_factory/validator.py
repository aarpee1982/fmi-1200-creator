from __future__ import annotations


BANNED_PHRASES = {
    "data limitations",
    "not feasible",
    "not quantified",
    "qualitative assessment only",
    "currently unavailable",
    "high uncertainty",
    "evidence limitations",
    "modelled analyst estimate",
    "working note",
    "internal note",
    "unspecified due to evidence limitations",
    "based on norms",
    "segmented by",
}

BIBLIO_BLOCKLIST = {
    "stats n data",
    "proprietary forecasting model",
    "primary research inputs",
    "grand view",
    "imarc",
    "market research",
}


def _walk_strings(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from _walk_strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_strings(value)
    elif isinstance(node, str):
        yield node


def validate_article(article: dict, fact_pack: dict) -> dict:
    hard_errors = []
    warnings = []

    market = fact_pack.get("market_name", "")
    sections = article.get("sections", {})
    title = sections.get("title_block", {})
    key_takeaways = sections.get("key_takeaways", {})
    bibliography = sections.get("bibliography", {})
    key_players = sections.get("key_players", {})

    if title.get("h1_title", "") != market:
        warnings.append("H1 title does not match market name.")

    if not str(title.get("segmentation_line", "")).startswith("By "):
        warnings.append("Segmentation line should start with 'By '.")

    heading = str(title.get("market_value_heading", ""))
    if "Size" not in heading or "Outlook" not in heading:
        warnings.append("Market value heading is weak.")

    for s in _walk_strings({
        "title_block": title,
        "key_takeaways": key_takeaways,
    }):
        low = s.lower()
        if "usd 0" in low or "0.0 billion" in low:
            hard_errors.append("Zero-value market number detected.")
            break

    for s in _walk_strings(article):
        low = s.lower()
        for bad in BANNED_PHRASES:
            if bad in low:
                warnings.append(f"Banned phrase detected: {bad}")
                break

    players = key_players.get("items", [])
    if not players:
        warnings.append("Key players are empty.")
    else:
        for p in players:
            if "various" in p.lower():
                warnings.append("Key players contain vague placeholder wording.")

    bib_items = bibliography.get("items", [])
    if not bib_items:
        warnings.append("Bibliography is empty.")
    else:
        for item in bib_items:
            low = item.lower()
            for bad in BIBLIO_BLOCKLIST:
                if bad in low:
                    warnings.append(f"Blocked bibliography source detected: {bad}")
                    break

    return {
        "hard_errors": hard_errors,
        "warnings": warnings,
    }
