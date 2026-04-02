#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import textwrap
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OFFERS_PATH = ROOT / "data" / "offers.json"
SITE_CONFIG_PATH = ROOT / "data" / "site-config.json"
DEFAULT_PACK_DIR = ROOT / "content" / "machine" / "packs"
DEFAULT_PLAN_DIR = ROOT / "content" / "machine" / "plans"
DEFAULT_MODEL = "gpt-5-mini"

DIFFICULTY_LABELS = {
    "easy": "facile",
    "medium": "media",
    "hard": "alta",
}

WEEKDAY_LABELS = {
    0: "Lunedi",
    1: "Martedi",
    2: "Mercoledi",
    3: "Giovedi",
    4: "Venerdi",
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
    if not base_url:
        return guide_url
    return f"{base_url}/{guide_url.lstrip('/')}"


def contact_links(site_config: dict) -> list[tuple[str, str]]:
    socials = site_config.get("socials", {})
    entries = []
    if socials.get("whatsapp_url"):
        entries.append(("WhatsApp", socials["whatsapp_url"]))
    if socials.get("telegram_contact_url"):
        entries.append(("Telegram diretto", socials["telegram_contact_url"]))
    if socials.get("telegram_url"):
        entries.append(("Canale Telegram", socials["telegram_url"]))
    return entries


def ordered_active_offers(payload: dict, site_config: dict) -> list[dict]:
    offers_by_slug = {
        offer.get("slug"): offer for offer in payload.get("offers", []) if offer.get("status") == "active"
    }
    preferred = site_config.get("content", {}).get("primary_offers", [])
    ordered = [offers_by_slug[slug] for slug in preferred if slug in offers_by_slug]
    fallback = [offer for slug, offer in offers_by_slug.items() if slug not in preferred]
    return ordered + fallback


def find_offer(payload: dict, slug: str) -> dict:
    for offer in payload.get("offers", []):
        if offer.get("slug") == slug:
            return offer
    raise SystemExit(f"Offerta non trovata: {slug}")


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


def pick_rotating_offer(payload: dict, site_config: dict, today: dt.date) -> dict:
    offers = ordered_active_offers(payload, site_config)
    if not offers:
        raise SystemExit("Nessuna offerta attiva disponibile.")

    anchor_raw = site_config.get("telegram", {}).get("rotation_anchor_date", "")
    try:
        anchor = dt.date.fromisoformat(anchor_raw) if anchor_raw else today
    except ValueError:
        anchor = today

    index = business_day_offset(anchor, today) % len(offers)
    return offers[index]


def front_matter(title: str, slug: str, offer_slug: str, created_at: str) -> str:
    return textwrap.dedent(
        f"""\
        ---
        title: "{title}"
        slug: "{slug}"
        offer: "{offer_slug}"
        status: "draft"
        created_at: "{created_at}"
        ---

        """
    )


def humanize_difficulty(value: str) -> str:
    return DIFFICULTY_LABELS.get(value, value)


def activation_url(offer: dict) -> str:
    return offer.get("referral_url", "").strip() or offer.get("official_url", "").strip()


def activation_label(offer: dict) -> str:
    if offer.get("referral_url"):
        return "link invito"
    if offer.get("referral_code"):
        return "codice invito"
    return "percorso ufficiale"


def activation_line(offer: dict) -> str:
    if offer.get("referral_url"):
        return f"Link invito: {offer['referral_url']}"
    if offer.get("referral_code"):
        return f"Codice invito: {offer['referral_code']}"
    return f"Percorso ufficiale: {offer['official_url']}"


def support_line(offer: dict) -> str:
    support = offer.get("support_note", "").strip()
    return support or "Supporto diretto disponibile su WhatsApp e Telegram."


def core_benefit(offer: dict) -> str:
    if offer.get("bonus_cliente_fixed"):
        return f"{offer['bonus_cliente']} reali con passaggi {humanize_difficulty(offer.get('difficulty', ''))}"
    return f"campagna variabile da controllare bene, ma con guida gia pronta"


def offer_angles(offer: dict) -> list[str]:
    difficulty = humanize_difficulty(offer.get("difficulty", ""))
    deposit = offer.get("deposit_required", "requisito da verificare")
    name = offer["name"]
    angles = [
        f"Quanto guadagni davvero con {name} e cosa devi fare per non sbagliare.",
        f"Spiegazione semplice del deposito o della spesa richiesta: {deposit}.",
        f"Per chi e adatta questa promo: bonus {offer['bonus_cliente']} con difficolta {difficulty}.",
    ]
    if offer.get("referral_code"):
        angles.append(f"Tutorial rapido: dove inserire il codice invito {offer['referral_code']}.")
    else:
        angles.append(f"Perche conviene aprire {name} solo dal link invito corretto.")
    return angles


def video_hooks(offer: dict) -> list[str]:
    bonus = offer["bonus_cliente"]
    name = offer["name"]
    deposit = offer.get("deposit_short") or offer.get("deposit_required")
    return [
        f"{bonus} con {name}: ecco cosa devi fare davvero.",
        f"Se vuoi partire con {name}, il passaggio che conta davvero e questo.",
        f"Quanto devi spendere per sbloccare il bonus {name}? {deposit}.",
        f"Guida veloce {name}: bonus, requisiti e errore da evitare.",
        f"Prima di aprire {name}, controlla questo dettaglio.",
    ]


def video_script(offer: dict, guide_url: str) -> str:
    step_lines = offer.get("requirements", [])[:3]
    beats = [
        f"Hook: con {offer['name']} puoi puntare a {offer['effective_gain']}.",
        f"Problema: molti aprono il conto ma saltano il requisito chiave.",
        f"Step 1: usa il {activation_label(offer)} corretto.",
        "Step 2: completa registrazione e verifica identita.",
        f"Step 3: completa questo requisito: {step_lines[-1] if step_lines else offer.get('deposit_required', 'controlla i termini')}.",
        f"CTA: apri la guida {guide_url} oppure scrivimi prima di iniziare.",
    ]
    return "\n".join(f"- {beat}" for beat in beats)


def telegram_variations(offer: dict) -> list[str]:
    bonus = offer["bonus_cliente"]
    name = offer["name"]
    deposit = offer.get("deposit_required", "requisito da verificare")
    support = offer.get("support_short", "supporto diretto")
    return [
        f"{name}: bonus {bonus}. Requisito chiave: {deposit}. Se vuoi partire senza errori, guida pronta e {support.lower()}.",
        f"Promo {name} attiva: guarda quanto puoi ottenere e soprattutto cosa devi fare davvero per sbloccarla.",
    ]


def social_caption(offer: dict, guide_url: str) -> str:
    return (
        f"{offer['name']}: bonus {offer['bonus_cliente']}. "
        f"Guadagno cliente: {offer['effective_gain']}. "
        f"Requisito chiave: {offer.get('deposit_required', 'controlla la guida')}. "
        f"Guida completa: {guide_url}"
    )


def story_slides(offer: dict, guide_url: str) -> list[str]:
    slides = [
        f"Slide 1: {offer['name']} - bonus {offer['bonus_cliente']}",
        f"Slide 2: quanto puoi ottenere davvero -> {offer['effective_gain']}",
        f"Slide 3: cosa devi fare -> {offer.get('deposit_required', 'controlla la guida')}",
        f"Slide 4: supporto -> {support_line(offer)}",
        f"Slide 5: CTA -> apri la guida {guide_url}",
    ]
    return slides


def blog_titles(offer: dict, today: dt.date) -> list[str]:
    month = today.strftime("%m-%Y")
    return [
        f"Bonus {offer['name']} aggiornato {month}: quanto si guadagna davvero",
        f"Come funziona il referral {offer['name']}: guida semplice e aggiornata",
        f"{offer['name']} conviene davvero? Bonus, requisiti e errori da evitare",
    ]


def dm_replies(offer: dict) -> list[str]:
    activation = activation_line(offer)
    return [
        f"Se vuoi iniziare con {offer['name']}, usa questo percorso: {activation}",
        f"Il requisito che devi ricordare e questo: {offer.get('deposit_required', 'controlla la guida')}",
        f"Se vuoi ti seguo passo passo: {support_line(offer)}",
    ]


def overlay_copy(offer: dict) -> list[str]:
    return [
        offer["name"],
        f"BONUS {offer['bonus_cliente']}",
        f"GUADAGNO {offer['effective_gain']}",
        f"PASSAGGIO CHIAVE: {offer.get('deposit_short') or offer.get('deposit_required', 'verifica in guida')}",
        "GUIDA PASSO PASSO",
    ]


def visual_brief(offer: dict) -> list[str]:
    visual = offer.get("visual", {})
    return [
        f"Colore principale: {visual.get('primary', 'n/d')}",
        f"Colore secondario: {visual.get('secondary', 'n/d')}",
        f"Accent: {visual.get('accent', 'n/d')}",
        f"Numero principale in evidenza: {offer['bonus_cliente']}",
        f"Badge secondario: {offer.get('deposit_short') or offer.get('deposit_required', 'requisito chiave')}",
        "Elementi visuali consigliati: logo brand, badge bonus, badge requisito, CTA guida o contatto.",
    ]


def cta_stack(offer: dict, guide_url: str, site_config: dict) -> list[str]:
    lines = [
        f"Apri guida: {guide_url}",
        activation_line(offer),
    ]
    for label, url in contact_links(site_config):
        lines.append(f"{label}: {url}")
    return lines


def build_offer_pack_template(offer: dict, base_url: str, today: dt.date, site_config: dict) -> tuple[str, str, str]:
    guide_url = build_guide_url(base_url, offer["guide_url"])
    title = f"Content Pack {offer['name']} - {today.isoformat()}"
    filename_slug = f"{today.isoformat()}-{offer['slug']}-content-pack"
    front = front_matter(title, filename_slug, offer["slug"], today.isoformat())

    body = "\n".join(
        [
            "## Dati chiave",
            "",
            f"- Offerta: **{offer['name']}**",
            f"- Bonus cliente: **{offer['bonus_cliente']}**",
            f"- Guadagno effettivo: **{offer['effective_gain']}**",
            f"- Difficolta: **{humanize_difficulty(offer.get('difficulty', ''))}**",
            f"- Deposito / spesa richiesta: **{offer.get('deposit_required', 'Da verificare')}**",
            f"- Guida: {guide_url}",
            f"- Accesso referral: {activation_line(offer)}",
            "",
            "## Angoli contenuto",
            "",
            *[f"- {line}" for line in offer_angles(offer)],
            "",
            "## Hook video verticali",
            "",
            *[f"{index}. {line}" for index, line in enumerate(video_hooks(offer), start=1)],
            "",
            "## Script video 30 secondi",
            "",
            video_script(offer, guide_url),
            "",
            "## Caption social",
            "",
            social_caption(offer, guide_url),
            "",
            "## Varianti Telegram",
            "",
            *[f"- {line}" for line in telegram_variations(offer)],
            "",
            "## Story o carousel",
            "",
            *[f"- {line}" for line in story_slides(offer, guide_url)],
            "",
            "## Testo overlay video",
            "",
            *[f"- {line}" for line in overlay_copy(offer)],
            "",
            "## Titoli blog / SEO",
            "",
            *[f"- {line}" for line in blog_titles(offer, today)],
            "",
            "## Risposte rapide DM",
            "",
            *[f"- {line}" for line in dm_replies(offer)],
            "",
            "## CTA e link rapidi",
            "",
            *[f"- {line}" for line in cta_stack(offer, guide_url, site_config)],
            "",
            "## Brief visual",
            "",
            *[f"- {line}" for line in visual_brief(offer)],
            "",
            "## Note operative",
            "",
            f"- Fonte ufficiale: {offer['official_url']}",
            f"- Ultima verifica dati: {offer['last_verified_at']}",
            f"- Supporto: {support_line(offer)}",
        ]
    )

    return filename_slug, front + body + "\n", guide_url


def build_weekly_plan_template(offers: list[dict], base_url: str, today: dt.date, site_config: dict) -> tuple[str, str]:
    monday = today - dt.timedelta(days=today.weekday())
    filename_slug = f"{monday.isoformat()}-weekly-content-plan"
    title = f"Piano contenuti settimana del {monday.isoformat()}"
    front = front_matter(title, filename_slug, "weekly-plan", today.isoformat())

    plan_blocks = []
    formats = [
        "Reel bonus chiaro",
        "Post Telegram con card",
        "Video errori da evitare",
        "Story / carousel passo passo",
        "Roundup della settimana",
    ]
    focuses = [
        "quanto si guadagna davvero",
        "cosa devi fare senza sbagliare",
        "deposito o spesa minima richiesta",
        "supporto e dubbi comuni",
        "confronto tra offerte attive",
    ]

    for index in range(5):
        date_label = monday + dt.timedelta(days=index)
        weekday = WEEKDAY_LABELS.get(index, f"Giorno {index + 1}")
        offer = offers[index % len(offers)]
        guide_url = build_guide_url(base_url, offer["guide_url"])
        contact_suggestions = contact_links(site_config)
        contact_label, contact_url = contact_suggestions[index % len(contact_suggestions)] if contact_suggestions else ("Contatto", "Da configurare")
        plan_blocks.append(
            "\n".join(
                [
                    f"### {weekday} - {date_label.isoformat()}",
                    "",
                    f"- Offerta focus: **{offer['name']}**",
                    f"- Formato principale: **{formats[index]}**",
                    f"- Focus editoriale: **{focuses[index]}**",
                    f"- CTA: apri la guida {guide_url}",
                    f"- Accesso referral: {activation_line(offer)}",
                    f"- Hook suggerito: {video_hooks(offer)[0]}",
                    f"- Contatto da spingere: {contact_label} -> {contact_url}",
                ]
            )
        )

    body = "## Piano editoriale della settimana\n\n" + "\n\n".join(plan_blocks) + "\n"
    return filename_slug, front + body


def call_openai(prompt: str, model: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY non impostata.")

    payload = {"model": model, "input": prompt}
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Errore OpenAI API: {exc.code} {details}") from exc

    if body.get("output_text"):
        return body["output_text"].strip()

    fragments: list[str] = []
    for item in body.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                fragments.append(content["text"])
    if fragments:
        return "\n".join(fragments).strip()

    raise SystemExit("Risposta OpenAI senza testo utile.")


def build_offer_openai_prompt(offer: dict, base_url: str, today: dt.date, site_config: dict) -> tuple[str, str]:
    guide_url = build_guide_url(base_url, offer["guide_url"])
    filename_slug = f"{today.isoformat()}-{offer['slug']}-content-pack"
    contacts = "\n".join(f"- {label}: {url}" for label, url in contact_links(site_config)) or "- Nessun contatto configurato"
    prompt = textwrap.dedent(
        f"""\
        Scrivi un content pack editoriale in italiano, utile e concreto, per un creator che pubblica bonus referral.
        Restituisci solo Markdown, senza front matter.

        Dati offerta:
        - Nome: {offer['name']}
        - Bonus cliente: {offer['bonus_cliente']}
        - Guadagno effettivo: {offer['effective_gain']}
        - Deposito richiesto: {offer.get('deposit_required', 'Da verificare')}
        - Difficolta: {humanize_difficulty(offer.get('difficulty', ''))}
        - Requisiti: {", ".join(offer.get('requirements', []))}
        - Accesso referral: {activation_line(offer)}
        - Guida: {guide_url}
        - Fonte: {offer['official_url']}
        - Supporto: {support_line(offer)}
        - Contatti:
        {contacts}

        Struttura obbligatoria:
        ## Dati chiave
        ## Angoli contenuto
        ## Hook video verticali
        ## Script video 30 secondi
        ## Caption social
        ## Varianti Telegram
        ## Story o carousel
        ## Testo overlay video
        ## Titoli blog / SEO
        ## Risposte rapide DM
        ## CTA e link rapidi
        ## Brief visual
        ## Note operative

        Regole:
        - Non inventare bonus o condizioni.
        - Mantieni tono semplice, concreto e orientato alla conversione.
        - Inserisci CTA coerenti verso guida, WhatsApp o Telegram.
        - Massimo 750 parole.
        """
    )
    return filename_slug, prompt


def build_weekly_openai_prompt(offers: list[dict], base_url: str, today: dt.date) -> tuple[str, str]:
    monday = today - dt.timedelta(days=today.weekday())
    filename_slug = f"{monday.isoformat()}-weekly-content-plan"
    offer_lines = []
    for offer in offers:
        guide_url = build_guide_url(base_url, offer["guide_url"])
        offer_lines.append(
            f"- {offer['name']}: bonus {offer['bonus_cliente']}, guadagno {offer['effective_gain']}, deposito {offer.get('deposit_required', 'Da verificare')}, guida {guide_url}, referral {activation_line(offer)}"
        )

    prompt = textwrap.dedent(
        f"""\
        Scrivi un piano contenuti settimanale in italiano per un sito che parla di bonus referral.
        Restituisci solo Markdown, senza front matter.

        Offerte disponibili:
        {chr(10).join(offer_lines)}

        Struttura obbligatoria:
        ## Piano editoriale della settimana

        Regole:
        - Crea 5 giornate da lunedi a venerdi.
        - Per ogni giorno indica offerta focus, formato principale, focus editoriale, CTA, hook e contatto consigliato.
        - Alterna video verticali, Telegram, story, recap e confronto.
        - Non inventare importi o scadenze.
        """
    )
    return filename_slug, prompt


def write_output(output_dir: Path, filename_slug: str, content: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{filename_slug}.md"
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write(content.strip() + "\n")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera pacchetti contenuto per la macchina editoriale.")
    parser.add_argument("--mode", choices=["offer", "weekly"], default="offer")
    parser.add_argument("--slug", default="auto")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--use-openai", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--today", default="")
    args = parser.parse_args()

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    offers_payload = load_json(OFFERS_PATH)
    site_config = load_json(SITE_CONFIG_PATH)
    base_url = resolve_base_url(site_config, args.base_url)

    if args.mode == "offer":
        offer = pick_rotating_offer(offers_payload, site_config, today) if args.slug == "auto" else find_offer(offers_payload, args.slug)
        output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_PACK_DIR
        if args.use_openai:
            filename_slug, prompt = build_offer_openai_prompt(offer, base_url, today, site_config)
            front = front_matter(
                f"Content Pack {offer['name']} - {today.isoformat()}",
                filename_slug,
                offer["slug"],
                today.isoformat(),
            )
            content = front + call_openai(prompt, args.model)
        else:
            filename_slug, content, _guide_url = build_offer_pack_template(offer, base_url, today, site_config)
    else:
        offers = ordered_active_offers(offers_payload, site_config)
        output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_PLAN_DIR
        if args.use_openai:
            filename_slug, prompt = build_weekly_openai_prompt(offers, base_url, today)
            front = front_matter(
                f"Piano contenuti settimana del {(today - dt.timedelta(days=today.weekday())).isoformat()}",
                filename_slug,
                "weekly-plan",
                today.isoformat(),
            )
            content = front + call_openai(prompt, args.model)
        else:
            filename_slug, content = build_weekly_plan_template(offers, base_url, today, site_config)

    output_path = write_output(output_dir, filename_slug, content)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
