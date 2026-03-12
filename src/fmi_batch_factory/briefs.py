from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class MarketBrief:
    market_name: str
    market_slug: str
    raw: dict[str, Any]


def load_pending_briefs(path: Path, seen: set[str], limit: int) -> list[MarketBrief]:
    rows = json.loads(path.read_text(encoding='utf-8'))
    out: list[MarketBrief] = []
    for row in rows:
        slug = row.get('market_slug') or row.get('market_name')
        if slug in seen:
            continue
        out.append(MarketBrief(market_name=row['market_name'], market_slug=slug, raw=row))
        if len(out) >= limit:
            break
    return out
