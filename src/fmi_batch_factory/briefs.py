from __future__ import annotations
from .utils import slugify


DEFAULT_SEGMENTS = {
    "product_type": ["Type A", "Type B", "Type C"],
    "application":  ["Application 1", "Application 2", "Application 3"],
    "end_user":     ["Segment 1", "Segment 2", "Segment 3"],
}

DEFAULT_COUNTRIES = ["United States", "Germany", "United Kingdom", "India", "China", "Brazil"]
DEFAULT_VARIABLES = ["market size", "regulatory approvals", "industry growth rate"]


def market_name_to_brief(market_name: str) -> dict:
    """Convert a plain market name string into a minimal brief dict."""
    name = market_name.strip()
    return {
        "market_name":         name,
        "market_slug":         slugify(name),
        "domain":              "global",
        "geography":           "global",
        "parent_market":       "",
        "segments":            DEFAULT_SEGMENTS,
        "priority_countries":  DEFAULT_COUNTRIES,
        "benchmark_variables": DEFAULT_VARIABLES,
        "notes":               ["Use authoritative public sources.", "Proxy estimation allowed."],
    }
