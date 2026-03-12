from __future__ import annotations


def assess_foundation(evidence_pack: dict, minimum_cards: int = 5, minimum_numeric: int = 2) -> dict:
    if isinstance(evidence_pack, dict):
        cards = evidence_pack.get("evidence_cards", [])
    elif isinstance(evidence_pack, list):
        cards = evidence_pack
    else:
        cards = []

    total = len(cards)
    numeric = sum(1 for c in cards if isinstance(c, dict) and str(c.get("numeric_signal", "")).strip())
    non_commercial = sum(1 for c in cards if isinstance(c, dict) and c.get("non_commercial_likely") is True)
    preferred_authority = sum(
        1 for c in cards
        if isinstance(c, dict) and (c.get("authority_type") or "").lower() in {
            "government", "regulator", "multilateral", "public_statistical_body",
            "public_health_agency", "public_trade_database",
            "public_prescription_dataset", "first_party_public_filing"
        }
    )

    score = min(total, 10) * 4 + min(non_commercial, 10) * 5 + min(preferred_authority, 10) * 4 + min(numeric, 10) * 2
    score = min(score, 100)

    if non_commercial < 5:
        status = "weak_foundation"
    elif non_commercial < 8 or preferred_authority < 5:
        status = "moderate_foundation"
    else:
        status = "strong_foundation"

    return {
        "passed": total >= minimum_cards and numeric >= minimum_numeric,
        "status": status,
        "score": score,
        "evidence_cards": total,
        "numeric_cards": numeric,
        "non_commercial_cards": non_commercial,
        "preferred_authority_cards": preferred_authority,
        "notes": [
            "Score is a routing signal, not a guarantee of accuracy.",
            "Weak/moderate foundation means wider forecast ranges and stronger caveats.",
        ],
    }
