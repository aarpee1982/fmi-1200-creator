from __future__ import annotations
from .utils import slugify

DEFAULT_COUNTRIES = ["United States", "Germany", "United Kingdom", "India", "China", "Brazil"]
DEFAULT_VARIABLES = ["market size", "regulatory approvals", "industry growth rate"]


def market_name_to_brief(market_name: str) -> dict:
    name = market_name.strip()
    return {
        "market_name":         name,
        "market_slug":         slugify(name),
        "domain":              "global",
        "geography":           "global",
        "parent_market":       "",
        "segments":            {},   # empty — reasoning model will determine real segments
        "priority_countries":  DEFAULT_COUNTRIES,
        "benchmark_variables": DEFAULT_VARIABLES,
        "notes":               ["Use authoritative public sources.", "Proxy estimation allowed."],
    }
