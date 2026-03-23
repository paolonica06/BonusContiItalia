#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OFFERS_PATH = ROOT / "data" / "offers.json"
SITE_CONFIG_PATH = ROOT / "data" / "site-config.json"

DIFFICULTY_LABELS = {
    "easy": "facile",
    "medium": "media",
    "hard": "alta",
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_base_url(site_config: dict, cli_base_url: str) -> str:
    if cli_base_url:
        return cli_base_url.rstrip("/")
    configured = site_config.get("site", {}).get("base_url", "").rstrip("/")
    if configured in {"", "https://example.com", "http://example.com"}:
        return ""
    return configured


def build_guide_url(base_url: str, guide_url: str) -> str:
    if not base_url or not guide_url:
        return ""
    return f"{base_url}/{guide_url.lstrip('/')}"


def build_channel_url(site_config: dict) -> str:
    explicit = site_config.get("socials", {}).get("telegram_url", "").strip()
    if explicit:
        return explicit

    channel_name = site_config.get("telegram", {}).get("channel_name", "").strip()
    if channel_name.startswith("@"):
        return f"https://t.me/{channel_name[1:]}"
    return ""


def get_first_social_button(site_config: dict) -> tuple[str, str] | None:
    socials = site_config.get("socials", {})
    options = [
        ("TikTok", socials.get("tiktok_url", "").strip()),
        ("Instagram", socials.get("instagram_url", "").strip()),
        ("YouTube", socials.get("youtube_url", "").strip()),
    ]
    for label, url in options:
        if url:
            return label, url
    return None


def humanize_difficulty(value: str) -> str:
    return DIFFICULTY_LABELS.get(value, value)


def format_date(value: str) -> str:
    try:
        parsed = dt.date.fromisoformat(value)
        return parsed.strftime("%d/%m/%Y")
    except ValueError:
        return value


def active_offers(payload: dict, site_config: dict) -> list[dict]:
    offers_by_slug = {
        offer.get("slug"): offer for offer in payload.get("offers", []) if offer.get("status") == "active"
    }
    preferred = site_config.get("content", {}).get("primary_offers", [])
    ordered = [offers_by_slug[slug] for slug in preferred if slug in offers_by_slug]
    fallback = [offer for slug, offer in offers_by_slug.items() if slug not in preferred]
    return ordered + fallback


def business_day_offset(anchor: dt.date, today: dt.date) -> int:
    if today <= anchor:
        return 0

    delta_days = (today - anchor).days
    weeks, extra_days = divmod(delta_days, 7)
    business_days = weeks * 5

    for step in range(1, extra_days + 1):
        weekday = (anchor.weekday() + step) % 7
        if weekday < 5:
            business_days += 1

    return business_days


def pick_rotating_offer(
    payload: dict, site_config: dict, today: dt.date, rotation_index: int | None = None
) -> dict:
    offers = active_offers(payload, site_config)
    if not offers:
        raise SystemExit("Nessuna offerta attiva disponibile per la rotazione.")

    if rotation_index is not None:
        index = rotation_index % len(offers)
        return offers[index]

    anchor_raw = site_config.get("telegram", {}).get("rotation_anchor_date", "")
    try:
        anchor = dt.date.fromisoformat(anchor_raw) if anchor_raw else today
    except ValueError:
        anchor = today

    index = business_day_offset(anchor, today) % len(offers)
    return offers[index]


def find_offer(slug: str, payload: dict) -> dict:
    for offer in payload.get("offers", []):
        if offer.get("slug") == slug:
            return offer
    raise SystemExit(f"Offerta non trovata: {slug}")


def is_new_customer_offer(offer: dict) -> bool:
    for item in offer.get("requirements", []):
        if "nuovo cliente" in item.lower():
            return True
    return False


def bonus_hook(offer: dict) -> str:
    difficulty = humanize_difficulty(offer.get("difficulty", ""))
    if offer.get("bonus_cliente_fixed"):
        return (
            f"Bonus <b>{html.escape(offer['bonus_cliente'])}</b> con procedura "
            f"<b>{difficulty}</b> in circa <b>{html.escape(offer['estimated_time'])}</b>."
        )
    return (
        f"Bonus <b>{html.escape(offer['bonus_cliente'])}</b>: "
        f"controlla l'importo finale nell'app prima di completare i passaggi."
    )


def conversion_angle(offer: dict) -> str:
    if offer.get("bonus_cliente_fixed") and offer.get("difficulty") == "easy":
        return "Promo semplice da completare se vuoi partire con un bonus chiaro."
    if offer.get("bonus_cliente_fixed"):
        return "Promo utile se vuoi un bonus chiaro seguendo una guida passo passo."
    return "Promo da controllare bene: il valore finale puo cambiare, quindi segui la guida senza errori."


def safety_line(offer: dict) -> str:
    if offer.get("bonus_cliente_fixed"):
        return "Segui i passaggi in ordine per non perdere il bonus."
    return "Controlla l'importo in app e completa ogni requisito prima di aspettare il premio."


def build_text(offer: dict, guide_url: str) -> str:
    name = html.escape(offer["name"])
    difficulty = html.escape(humanize_difficulty(offer.get("difficulty", "")))
    effective_gain = html.escape(offer["effective_gain"])
    effective_note = html.escape(offer["effective_gain_note"])
    bonus_note = html.escape(offer.get("bonus_note", ""))
    verified_at = html.escape(format_date(offer["last_verified_at"]))
    intro = html.escape(conversion_angle(offer))
    safe_tip = html.escape(safety_line(offer))
    audience_parts = []
    if is_new_customer_offer(offer):
        audience_parts.append("solo nuovi clienti")
    audience_parts.append(difficulty)
    audience_parts.append(html.escape(offer['estimated_time']))
    audience_line = " | ".join(audience_parts)

    call_to_action = (
        "👇 Apri la guida e parti da li."
        if guide_url
        else "👇 Apri l'offerta dal pulsante qui sotto."
    )

    lines = [
        f"🔥 <b>{name}: bonus {html.escape(offer['bonus_cliente'])}</b>",
        "",
        bonus_hook(offer),
        "",
        intro,
        "",
        f"🎯 <b>Ideale per:</b> {audience_line}",
        "",
        "✅ <b>Passaggi da seguire</b>",
        "1. Apri il servizio dalla guida qui sotto." if guide_url else "1. Apri il servizio dal pulsante qui sotto.",
        "2. Completa registrazione e verifica identita.",
        "3. Completa questi requisiti:",
    ]

    for item in offer.get("requirements", [])[:3]:
        lines.append(f"• {html.escape(item)}")

    lines.extend(
        [
            "4. Attendi il bonus previsto dalla campagna.",
            "",
            f"💸 <b>Guadagno reale:</b> {effective_gain}",
            effective_note,
        ]
    )

    if bonus_note:
        lines.extend(["", f"📌 <b>Nota utile:</b> {bonus_note}"])

    lines.extend(
        [
            "",
            f"🛡 <b>Consiglio:</b> {safe_tip}",
            "",
            f"🔎 <b>Dati verificati:</b> {verified_at}",
            "",
            call_to_action,
        ]
    )

    return "\n".join(lines)


def build_reply_markup(offer: dict, site_config: dict, base_url: str) -> dict:
    guide_url = build_guide_url(base_url, offer.get("guide_url", ""))
    site_url = base_url
    channel_url = build_channel_url(site_config)
    extra_social = get_first_social_button(site_config)

    inline_keyboard: list[list[dict[str, str]]] = []

    first_row: list[dict[str, str]] = []
    if guide_url:
        first_row.append({"text": "Apri guida bonus", "url": guide_url})
    elif offer.get("official_url"):
        first_row.append({"text": "Attiva la promo", "url": offer["official_url"]})

    if site_url:
        first_row.append({"text": "Vai al sito", "url": site_url})

    if first_row:
        inline_keyboard.append(first_row[:2])

    second_row: list[dict[str, str]] = []
    if channel_url:
        second_row.append({"text": "Altri bonus attivi", "url": channel_url})

    if extra_social and extra_social[1] != channel_url:
        second_row.append({"text": extra_social[0], "url": extra_social[1]})

    if second_row:
        inline_keyboard.append(second_row[:2])

    if guide_url and offer.get("official_url"):
        inline_keyboard.append([{"text": "Controlla termini", "url": offer["official_url"]}])

    return {"inline_keyboard": inline_keyboard}


def build_payload(offer: dict, site_config: dict, base_url: str) -> dict:
    guide_url = build_guide_url(base_url, offer.get("guide_url", ""))
    return {
        "slug": offer["slug"],
        "offer_name": offer["name"],
        "text": build_text(offer, guide_url),
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
        "reply_markup": build_reply_markup(offer, site_config, base_url),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera un messaggio Telegram per una promo.")
    parser.add_argument(
        "--slug",
        default="auto",
        help="Slug dell'offerta, ad esempio bbva. Usa 'auto' per la rotazione automatica.",
    )
    parser.add_argument("--base-url", default="", help="Dominio pubblico del sito.")
    parser.add_argument(
        "--today",
        default="",
        help="Data di riferimento in formato YYYY-MM-DD, utile per testare la rotazione.",
    )
    parser.add_argument(
        "--rotation-index",
        type=int,
        default=None,
        help="Indice numerico opzionale per forzare la rotazione, utile nei workflow automatici.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = load_json(OFFERS_PATH)
    site_config = load_json(SITE_CONFIG_PATH)
    base_url = resolve_base_url(site_config, args.base_url)
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()

    if args.slug == "auto":
        offer = pick_rotating_offer(payload, site_config, today, args.rotation_index)
    else:
        offer = find_offer(args.slug, payload)

    message_payload = build_payload(offer, site_config, base_url)
    print(json.dumps(message_payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
