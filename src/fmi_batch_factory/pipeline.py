from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from .article import build_article
from .deepseek_client import DeepSeekClient
from .foundation import assess_foundation
from .factpack import build_fact_pack
from .kimi_client import KimiClient
from .openai_client import OpenAIWebSearchClient, OpenAIProseClient
from .renderer import render_docx
from .utils import filename_for_market, slugify


BATCH_SIZE = 10          # max articles loaded per run
CONCURRENCY = 3          # articles processed at a time
FORECAST_START = 2026
FORECAST_END = 2036


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _query_for_brief(brief: dict) -> str:
    return (
        f"{brief['market_name']} global market size forecast public sources; "
        f"priority countries: {', '.join(brief.get('priority_countries', []))}; "
        f"benchmark variables: {', '.join(brief.get('benchmark_variables', []))}"
    )


def _load_seen(seen_path: Path) -> set[str]:
    if not seen_path.exists():
        return set()
    return set(json.loads(seen_path.read_text(encoding="utf-8")))


def _save_seen(seen_path: Path, seen: set[str]) -> None:
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    seen_path.write_text(json.dumps(sorted(seen), indent=2), encoding="utf-8")


def _has_valid_numbers(fp: dict, forecast_end: int) -> bool:
    keys = ["value_2026_usd_bn", f"value_{forecast_end}_usd_bn", "cagr_pct"]
    for k in keys:
        try:
            if fp.get(k) is None or float(fp[k]) <= 0:
                return False
        except Exception:
            return False
    return True


def _process_one(
    brief: dict,
    output_dir: Path,
    search_client: OpenAIWebSearchClient,
    ds_client: DeepSeekClient,
    kimi_client: KimiClient,
    openai_prose_client: OpenAIProseClient,
    log: Callable[[str], None],
) -> dict:
    market_name = brief.get("market_name", "Unknown")
    market_slug = brief.get("market_slug", slugify(market_name))
    market_dir = output_dir / market_slug

    try:
        log(f"[{market_name}] Searching for evidence...")
        evidence_pack = search_client.search_once(_query_for_brief(brief))

        log(f"[{market_name}] Assessing foundation ({evidence_pack.get('filtered_evidence_card_count', 0)} cards)...")
        foundation = assess_foundation(evidence_pack)

        log(f"[{market_name}] Building fact pack with DeepSeek...")
        fact_pack = build_fact_pack(ds_client, brief, evidence_pack, foundation, FORECAST_START, FORECAST_END)

        if not _has_valid_numbers(fact_pack, FORECAST_END):
            raise ValueError("Fact pack has zero or missing core numbers.")

        log(f"[{market_name}] Running 3 prose agents in parallel...")
        article = build_article(
            ds_client, kimi_client, openai_prose_client,
            fact_pack, evidence_pack, FORECAST_START, FORECAST_END,
        )
        winning = article.get("winning_agent", "unknown")
        log(f"[{market_name}] Best prose from: {winning}")

        _write_json(market_dir / "evidence_pack.json", evidence_pack)
        _write_json(market_dir / "foundation_check.json", foundation)
        _write_json(market_dir / "fact_pack.json", fact_pack)
        _write_json(market_dir / "article.json", article)

        docx_path = market_dir / filename_for_market(market_name)
        render_docx(article, docx_path)
        log(f"[{market_name}] Done. DOCX saved.")

        return {
            "market_name": market_name,
            "market_slug": market_slug,
            "status": "processed",
            "winning_agent": winning,
            "foundation_status": foundation["status"],
            "evidence_cards": foundation["evidence_cards"],
            "docx_path": str(docx_path),
        }

    except Exception as exc:
        fail = {
            "market_name": market_name,
            "market_slug": market_slug,
            "status": "failed",
            "error": str(exc),
        }
        market_dir.mkdir(parents=True, exist_ok=True)
        _write_json(market_dir / "run_result.json", fail)
        log(f"[{market_name}] FAILED: {exc}")
        return fail


def run_batch(
    briefs_path: Path,
    output_dir: Path,
    seen_path: Path,
    openai_key: str,
    deepseek_key: str,
    deepseek_base_url: str,
    deepseek_model: str,
    kimi_key: str,
    kimi_base_url: str,
    kimi_model: str,
    log: Callable[[str], None] = print,
    batch_size: int = BATCH_SIZE,
    concurrency: int = CONCURRENCY,
) -> dict:
    # Load briefs
    all_briefs = json.loads(briefs_path.read_text(encoding="utf-8"))
    seen = _load_seen(seen_path)
    pending = [b for b in all_briefs if b.get("market_slug", slugify(b.get("market_name", ""))) not in seen]
    batch = pending[:batch_size]

    if not batch:
        log("No pending briefs to process.")
        return {"processed": 0, "failed": 0, "items": []}

    log(f"Loaded {len(batch)} briefs. Running {concurrency} at a time.")

    # Instantiate clients
    search_client = OpenAIWebSearchClient(api_key=openai_key)
    ds_client = DeepSeekClient(api_key=deepseek_key, base_url=deepseek_base_url, model=deepseek_model)
    kimi_client = KimiClient(api_key=kimi_key, base_url=kimi_base_url, model=kimi_model)
    openai_prose_client = OpenAIProseClient(api_key=openai_key)

    summary = {"processed": 0, "failed": 0, "items": []}

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = {
            ex.submit(
                _process_one,
                brief, output_dir,
                search_client, ds_client, kimi_client, openai_prose_client,
                log,
            ): brief
            for brief in batch
        }
        for fut in as_completed(futures):
            result = fut.result()
            summary["items"].append(result)
            if result["status"] == "processed":
                summary["processed"] += 1
                seen.add(result["market_slug"])
            else:
                summary["failed"] += 1

    _write_json(output_dir / "batch_summary.json", summary)
    _save_seen(seen_path, seen)
    log(f"Batch complete. Processed: {summary['processed']}  Failed: {summary['failed']}")
    return summary
