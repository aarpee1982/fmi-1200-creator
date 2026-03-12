from __future__ import annotations

import math
import re
from pathlib import Path


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')


def clean_title(text: str) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'market size.*$', 'Market', text, flags=re.IGNORECASE)
    return text


def filename_for_market(title: str) -> str:
    return f"{title}.docx"


def calc_future_value(base: float, cagr_pct: float, years: int) -> float:
    return round(base * ((1 + cagr_pct / 100.0) ** years), 2)


def word_count(text: str) -> int:
    return len(re.findall(r'\b\w+\b', text or ''))
