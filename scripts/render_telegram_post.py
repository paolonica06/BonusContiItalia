#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OFFERS_PATH = ROOT / "data" / "offers.json"


def load_offers() -> dict:
    with OFFERS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_offer(slug: str, payload: dict) -> dict:
    for offer in payload.get("offers", []):
        if offer.get("slug") == slug:
            return offer
    raise SystemExit(f"Offerta non trovata: {slug}")


def render_message(offer: dict, base_url: str | None) -> str:
    guide_url = offer.get("guide_url", "")
    if base_url and guide_url:
        guide_url = f"{base_url.rstrip('/')}/{guide_url.lstrip('/')}"

    lines = [
        f"Nuovo aggiornamento: {offer['name']}",
        "",
        f"Bonus cliente: {offer['bonus_cliente']}",
        f"Guadagno effettivo: {offer['effective_gain']}",
        f"Difficolta: {offer['difficulty']}",
        f"Tempo stimato: {offer['estimated_time']}",
        "",
        "Cosa bisogna fare:",
    ]

    for item in offer.get("requirements", []):
        lines.append(f"- {item}")

    if offer.get("bonus_note"):
        lines.extend(["", f"Nota: {offer['bonus_note']}"])

    if guide_url:
        lines.extend(["", f"Guida completa: {guide_url}"])

    if offer.get("official_url"):
        lines.append(f"Fonte ufficiale: {offer['official_url']}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera un messaggio Telegram per una promo.")
    parser.add_argument("--slug", required=True, help="Slug dell'offerta, ad esempio bbva.")
    parser.add_argument("--base-url", default="", help="Dominio pubblico del sito.")
    args = parser.parse_args()

    payload = load_offers()
    offer = find_offer(args.slug, payload)
    print(render_message(offer, args.base_url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
