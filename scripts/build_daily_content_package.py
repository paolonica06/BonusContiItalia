#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import textwrap
from pathlib import Path

from build_content_pack import (
    DEFAULT_MODEL,
    OFFERS_PATH,
    ROOT,
    SITE_CONFIG_PATH,
    build_offer_openai_prompt,
    build_offer_pack_template,
    build_guide_url,
    call_openai,
    contact_links,
    load_json,
    resolve_base_url,
)
from build_vertical_scripts import build_openai_prompt as build_vertical_openai_prompt
from build_vertical_scripts import build_template_output as build_vertical_template_output
from generate_telegram_card import render_card
from render_telegram_post import build_payload, find_offer, pick_rotating_offer


DEFAULT_DAILY_DIR = ROOT / "content" / "machine" / "daily"


def strip_html_tags(value: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", value)
    text = re.sub(r"</?(b|strong|i|em|u|code)>", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, content: str) -> Path:
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return path


def write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def social_caption_pack(offer: dict, guide_url: str, site_config: dict) -> dict[str, str]:
    contacts = dict(contact_links(site_config))
    whatsapp = contacts.get("WhatsApp", "")
    telegram_direct = contacts.get("Telegram diretto", "")
    channel = contacts.get("Canale Telegram", "")
    name = offer["name"]
    bonus = offer["bonus_cliente"]
    gain = offer["effective_gain"]
    deposit = offer.get("deposit_required", "controlla la guida")
    support = offer.get("support_note", "").strip()

    instagram = textwrap.dedent(
        f"""\
        {name}: bonus {bonus}

        Guadagno reale: {gain}
        Requisito chiave: {deposit}

        Se vuoi partire senza errori trovi la guida completa qui:
        {guide_url}

        {support}
        """
    ).strip()

    tiktok = textwrap.dedent(
        f"""\
        {name}: bonus {bonus}
        Quanto puoi ottenere davvero? {gain}
        Cosa devi fare? {deposit}

        Guida completa: {guide_url}
        """
    ).strip()

    story = textwrap.dedent(
        f"""\
        Slide 1: {name} - bonus {bonus}
        Slide 2: Guadagno reale -> {gain}
        Slide 3: Requisito chiave -> {deposit}
        Slide 4: CTA -> apri la guida {guide_url}
        """
    ).strip()

    comment_lines = [f"Guida completa: {guide_url}"]
    if whatsapp:
        comment_lines.append(f"WhatsApp: {whatsapp}")
    if telegram_direct:
        comment_lines.append(f"Telegram diretto: {telegram_direct}")
    if channel:
        comment_lines.append(f"Canale Telegram: {channel}")

    dm_reply = textwrap.dedent(
        f"""\
        Ciao, per {name} il punto da ricordare e questo: {deposit}.
        Qui trovi la guida completa: {guide_url}
        Se vuoi ti seguo passo passo fin dall'inizio.
        """
    ).strip()

    return {
        "instagram-caption.txt": instagram,
        "tiktok-caption.txt": tiktok,
        "story-sequence.txt": story,
        "pinned-comment.txt": "\n".join(comment_lines),
        "dm-reply.txt": dm_reply,
    }


def publish_brief(offer: dict, guide_url: str, base_dir: Path, site_config: dict) -> str:
    contacts = contact_links(site_config)
    asset_lines = [
        f"- Card Telegram: `{(base_dir / 'promo-card.png').name}`",
        f"- Messaggio Telegram: `{(base_dir / 'telegram-message.json').name}`",
        f"- Caption Telegram leggibile: `{(base_dir / 'telegram-caption.html').name}`",
        f"- Content pack completo: `{(base_dir / 'content-pack.md').name}`",
        f"- Script verticali: `{(base_dir / 'vertical-scripts.md').name}`",
        f"- Caption social: `{(base_dir / 'instagram-caption.txt').name}`, `{(base_dir / 'tiktok-caption.txt').name}`",
    ]
    contact_lines = [f"- {label}: {url}" for label, url in contacts]
    sections = [
        "# Daily Content Package",
        "",
        "## Focus del giorno",
        "",
        f"- Offerta: **{offer['name']}**",
        f"- Bonus cliente: **{offer['bonus_cliente']}**",
        f"- Guadagno effettivo: **{offer['effective_gain']}**",
        f"- Requisito chiave: **{offer.get('deposit_required', 'Da verificare')}**",
        f"- Guida da spingere: {guide_url}",
        "",
        "## Ordine di pubblicazione consigliato",
        "",
        "1. Pubblica la card e il messaggio Telegram.",
        "2. Usa `vertical-scripts.md` per scegliere il Reel o Short del giorno.",
        "3. Copia la caption social piu adatta e chiudi con la CTA verso guida o contatto diretto.",
        "4. Riprendi il contatto migliore nei DM per chi chiede conferma.",
        "",
        "## Asset inclusi",
        "",
        *asset_lines,
        "",
        "## Contatti da spingere",
        "",
        *(contact_lines if contact_lines else ["- Nessun contatto configurato"]),
    ]
    return "\n".join(sections)


def write_package(
    offer: dict,
    site_config: dict,
    base_url: str,
    output_dir: Path,
    today: dt.date,
    use_openai: bool,
    model: str,
) -> Path:
    guide_url = build_guide_url(base_url, offer["guide_url"])
    package_dir = ensure_directory(output_dir / f"{today.isoformat()}-{offer['slug']}")

    if use_openai:
        filename_slug, prompt = build_offer_openai_prompt(offer, base_url, today, site_config)
        content_pack = (
            textwrap.dedent(
                f"""\
                ---
                title: "Daily Content Pack {offer['name']} - {today.isoformat()}"
                slug: "{filename_slug}"
                offer: "{offer['slug']}"
                status: "draft"
                created_at: "{today.isoformat()}"
                ---

                """
            )
            + call_openai(prompt, model)
        )
        vertical_content = (
            textwrap.dedent(
                f"""\
                ---
                title: "Daily Vertical Scripts {offer['name']} - {today.isoformat()}"
                slug: "{today.isoformat()}-{offer['slug']}-vertical-scripts"
                offer: "{offer['slug']}"
                status: "draft"
                created_at: "{today.isoformat()}"
                ---

                """
            )
            + call_openai(build_vertical_openai_prompt(offer, guide_url, site_config), model)
        )
    else:
        _pack_slug, content_pack, _guide_url = build_offer_pack_template(offer, base_url, today, site_config)
        _vertical_slug, vertical_content = build_vertical_template_output(offer, guide_url, site_config, today)

    telegram_payload = build_payload(offer, site_config, base_url)
    telegram_caption = telegram_payload.get("text", "")
    card_path = package_dir / "promo-card.png"
    render_card(offer, base_url, card_path, use_openai_background=False, model="gpt-image-1-mini", quality="low")

    write_text(package_dir / "content-pack.md", content_pack)
    write_text(package_dir / "vertical-scripts.md", vertical_content)
    write_json(package_dir / "telegram-message.json", telegram_payload)
    write_text(package_dir / "telegram-caption.html", telegram_caption)

    for filename, body in social_caption_pack(offer, guide_url, site_config).items():
        write_text(package_dir / filename, body)

    write_text(package_dir / "daily-brief.md", publish_brief(offer, guide_url, package_dir, site_config))
    write_text(package_dir / "telegram-caption.txt", strip_html_tags(telegram_caption))
    metadata = {
        "date": today.isoformat(),
        "offer_slug": offer["slug"],
        "offer_name": offer["name"],
        "guide_url": guide_url,
        "base_url": base_url,
        "use_openai": use_openai,
        "files": sorted(path.name for path in package_dir.iterdir()),
    }
    write_json(package_dir / "metadata.json", metadata)

    return package_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera un daily content package completo per un'offerta.")
    parser.add_argument("--slug", default="auto")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--use-openai", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--today", default="")
    parser.add_argument("--rotation-index", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    offers_payload = load_json(OFFERS_PATH)
    site_config = load_json(SITE_CONFIG_PATH)
    base_url = resolve_base_url(site_config, args.base_url)
    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_DAILY_DIR

    if args.slug == "auto":
        offer = pick_rotating_offer(offers_payload, site_config, today, args.rotation_index)
    else:
        offer = find_offer(args.slug, offers_payload)

    package_dir = write_package(
        offer=offer,
        site_config=site_config,
        base_url=base_url,
        output_dir=output_dir,
        today=today,
        use_openai=args.use_openai,
        model=args.model,
    )
    print(package_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
