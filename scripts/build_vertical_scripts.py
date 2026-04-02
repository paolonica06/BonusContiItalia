#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import textwrap
from pathlib import Path

from build_content_pack import (
    DEFAULT_MODEL,
    OFFERS_PATH,
    ROOT,
    SITE_CONFIG_PATH,
    activation_line,
    build_guide_url,
    call_openai,
    contact_links,
    find_offer,
    front_matter,
    humanize_difficulty,
    load_json,
    pick_rotating_offer,
    resolve_base_url,
    support_line,
)


DEFAULT_VERTICAL_DIR = ROOT / "content" / "machine" / "verticals"


def cover_title(offer: dict) -> str:
    if offer.get("bonus_cliente_fixed"):
        return f"{offer['bonus_cliente']} con {offer['name']}"
    return f"{offer['name']}: promo da controllare"


def short_requirement(offer: dict) -> str:
    return offer.get("deposit_short") or offer.get("deposit_required", "controlla la guida")


def fast_steps(offer: dict) -> list[str]:
    requirements = offer.get("requirements", [])
    if requirements:
        return requirements[:3]
    return [
        f"Usa il percorso corretto: {activation_line(offer)}",
        "Completa registrazione e verifica identita",
        f"Ricorda il requisito chiave: {offer.get('deposit_required', 'controlla la guida')}",
    ]


def build_variants(offer: dict, guide_url: str, site_config: dict) -> list[dict]:
    name = offer["name"]
    bonus = offer["bonus_cliente"]
    gain = offer["effective_gain"]
    deposit = offer.get("deposit_required", "controlla la guida")
    deposit_short = short_requirement(offer)
    difficulty = humanize_difficulty(offer.get("difficulty", ""))
    support = support_line(offer)
    contacts = contact_links(site_config)
    primary_contact = contacts[0] if contacts else ("Contatto", guide_url)
    secondary_contact = contacts[1] if len(contacts) > 1 else primary_contact
    step_list = fast_steps(offer)

    return [
        {
            "title": "Bonus chiaro",
            "goal": "Spiegare subito quanto si guadagna e il requisito minimo reale.",
            "hook": f"{bonus} con {name}: ti spiego il passaggio che conta davvero.",
            "cover": cover_title(offer),
            "narration": [
                f"Se vuoi ottenere {gain} con {name}, non complicarti la vita.",
                f"Ti serve solo seguire il percorso giusto e ricordare questo requisito: {deposit}.",
                f"Primo step: {step_list[0]}.",
                f"Secondo step: {step_list[1]}.",
                f"Terzo step: {step_list[2]}.",
                f"Se vuoi, ti seguo io passo passo. Apri la guida o scrivimi su {primary_contact[0]}.",
            ],
            "overlay": [
                name,
                f"BONUS {bonus}",
                f"REQUISITO: {deposit_short}",
                f"DIFFICOLTA: {difficulty}",
                "GUIDA PRONTA",
            ],
            "cta": f"Apri la guida: {guide_url}",
            "caption": f"{name}: bonus {bonus}, requisito chiave {deposit}. Se vuoi partire senza errori trovi la guida qui: {guide_url}",
        },
        {
            "title": "Errore da evitare",
            "goal": "Usare paura di perdere il bonus per spingere l'attenzione.",
            "hook": f"Molti aprono {name} ma non prendono il bonus per un errore banale.",
            "cover": f"Errore da evitare su {name}",
            "narration": [
                f"L'errore piu comune con {name} e aprire il conto senza capire il requisito reale.",
                f"In questo caso devi ricordare soprattutto: {deposit}.",
                f"Se salti questo passaggio, rischi di non ottenere {gain}.",
                f"Per questo ti conviene usare il percorso corretto e seguire la guida in ordine.",
                f"Se hai dubbi, scrivimi su {secondary_contact[0]} prima di iniziare.",
            ],
            "overlay": [
                "NON SBAGLIARE",
                name,
                f"RISCHIO: PERDI {bonus}",
                f"RICORDA: {deposit_short}",
                "SCRIVIMI PRIMA",
            ],
            "cta": f"Contatto rapido: {secondary_contact[0]} -> {secondary_contact[1]}",
            "caption": f"Prima di aprire {name}, controlla questo dettaglio: {deposit}. Guida passo passo: {guide_url}",
        },
        {
            "title": "Supporto umano",
            "goal": "Abbassare la frizione e far scrivere l'utente in DM.",
            "hook": f"Vuoi iniziare con {name} ma non sai se conviene davvero?",
            "cover": f"{name}: ti aiuto io",
            "narration": [
                f"Con {name} puoi puntare a {gain}, ma capisco che all'inizio ci siano dubbi.",
                f"La difficolta e {difficulty} e il requisito chiave e {deposit}.",
                support,
                f"Se vuoi partire oggi, scrivimi su {primary_contact[0]} e ti dico esattamente cosa fare.",
                f"Poi trovi anche la guida completa sul sito: {guide_url}.",
            ],
            "overlay": [
                "TI AIUTO IO",
                name,
                f"BONUS {bonus}",
                f"PASSAGGIO: {deposit_short}",
                primary_contact[0].upper(),
            ],
            "cta": f"Scrivimi qui: {primary_contact[1]}",
            "caption": f"Se vuoi iniziare con {name} e non perdere tempo, scrivimi direttamente. Ti seguo passo passo e poi trovi la guida completa qui: {guide_url}",
        },
        {
            "title": "A chi conviene",
            "goal": "Filtrare il pubblico e migliorare la qualita dei contatti.",
            "hook": f"{name} conviene davvero oppure no? Dipende da questo.",
            "cover": f"A chi conviene {name}",
            "narration": [
                f"{name} ha un bonus cliente pari a {bonus} e un guadagno reale di {gain}.",
                f"Secondo me conviene soprattutto a chi cerca una promo con difficolta {difficulty}.",
                f"Il punto da guardare prima di tutto e {deposit}.",
                f"Se vuoi capire se fa per te, apri la guida o scrivimi su {primary_contact[0]}.",
                f"Se vuoi partire subito usa questo accesso: {activation_line(offer)}.",
            ],
            "overlay": [
                f"CONVIENE {name}?",
                f"BONUS {bonus}",
                f"DIFFICOLTA {difficulty}",
                f"CHIAVE: {deposit_short}",
                "GUIDA O DM",
            ],
            "cta": f"Guida + accesso: {guide_url}",
            "caption": f"{name}: ti conviene se vuoi una promo {difficulty} con requisito {deposit}. Guida completa: {guide_url}",
        },
        {
            "title": "Confronto rapido",
            "goal": "Spingere la comparazione e far emergere la convenienza reale.",
            "hook": f"Tra le promo attive, {name} quanto ti fa guadagnare davvero?",
            "cover": f"{name}: guadagno reale",
            "narration": [
                f"Se guardi solo il numero grande, rischi di scegliere male.",
                f"Con {name} oggi il punto vero e questo: puoi puntare a {gain}.",
                f"Per farlo devi completare {deposit}.",
                f"Se vuoi confrontarla bene con le altre promo, parti dalla guida.",
                f"Poi se vuoi ti mando io il percorso giusto su {primary_contact[0]}.",
            ],
            "overlay": [
                "GUADAGNO REALE",
                name,
                gain.upper(),
                f"RICHIESTA: {deposit_short}",
                "CONFRONTA LE GUIDE",
            ],
            "cta": f"Vai alla guida: {guide_url}",
            "caption": f"Il guadagno reale con {name} non e solo il titolo promo: conta soprattutto il requisito {deposit}. Guida qui: {guide_url}",
        },
    ]


def render_variant(index: int, variant: dict) -> str:
    lines = [
        f"## Variante {index} - {variant['title']}",
        "",
        f"- Obiettivo: {variant['goal']}",
        f"- Hook: {variant['hook']}",
        f"- Titolo cover: {variant['cover']}",
        "",
        "### Testo parlato",
        "",
        *[f"{step}. {line}" for step, line in enumerate(variant["narration"], start=1)],
        "",
        "### Testo overlay",
        "",
        *[f"- {line}" for line in variant["overlay"]],
        "",
        "### CTA finale",
        "",
        variant["cta"],
        "",
        "### Caption breve",
        "",
        variant["caption"],
        "",
    ]
    return "\n".join(lines)


def build_template_output(offer: dict, guide_url: str, site_config: dict, today: dt.date) -> tuple[str, str]:
    filename_slug = f"{today.isoformat()}-{offer['slug']}-vertical-scripts"
    title = f"Vertical Scripts {offer['name']} - {today.isoformat()}"
    front = front_matter(title, filename_slug, offer["slug"], today.isoformat())
    contacts = contact_links(site_config)
    variants = build_variants(offer, guide_url, site_config)

    body_lines = [
        "## Dati rapidi",
        "",
        f"- Offerta: **{offer['name']}**",
        f"- Bonus cliente: **{offer['bonus_cliente']}**",
        f"- Guadagno effettivo: **{offer['effective_gain']}**",
        f"- Requisito chiave: **{offer.get('deposit_required', 'Da verificare')}**",
        f"- Guida: {guide_url}",
        f"- Accesso referral: {activation_line(offer)}",
        f"- Supporto: {support_line(offer)}",
        "",
        "## CTA e contatti",
        "",
        f"- Guida: {guide_url}",
        f"- Referral: {activation_line(offer)}",
        *[f"- {label}: {url}" for label, url in contacts],
        "",
    ]

    variant_blocks = [render_variant(index, variant) for index, variant in enumerate(variants, start=1)]
    return filename_slug, front + "\n".join(body_lines) + "\n" + "\n".join(variant_blocks)


def build_openai_prompt(offer: dict, guide_url: str, site_config: dict) -> str:
    contacts = "\n".join(f"- {label}: {url}" for label, url in contact_links(site_config)) or "- Nessun contatto configurato"
    return textwrap.dedent(
        f"""\
        Scrivi un file Markdown in italiano con 5 script verticali ad alta conversione per un creator che promuove bonus referral.
        Restituisci solo Markdown, senza front matter.

        Dati offerta:
        - Nome: {offer['name']}
        - Bonus cliente: {offer['bonus_cliente']}
        - Guadagno effettivo: {offer['effective_gain']}
        - Difficolta: {humanize_difficulty(offer.get('difficulty', ''))}
        - Requisito chiave: {offer.get('deposit_required', 'Da verificare')}
        - Requisiti: {", ".join(offer.get('requirements', []))}
        - Guida: {guide_url}
        - Referral: {activation_line(offer)}
        - Supporto: {support_line(offer)}
        - Contatti:
        {contacts}

        Struttura obbligatoria:
        ## Dati rapidi
        ## CTA e contatti
        ## Variante 1 - ...
        ## Variante 2 - ...
        ## Variante 3 - ...
        ## Variante 4 - ...
        ## Variante 5 - ...

        Per ogni variante includi sempre:
        - Obiettivo
        - Hook
        - Titolo cover
        ### Testo parlato
        ### Testo overlay
        ### CTA finale
        ### Caption breve

        Regole:
        - Tono semplice, diretto, orientato alla conversione.
        - Non inventare bonus, cifre o requisiti.
        - Ogni script deve avere un angolo diverso: bonus chiaro, errore da evitare, supporto umano, a chi conviene, confronto rapido.
        - Massimo 900 parole totali.
        """
    )


def write_output(output_dir: Path, filename_slug: str, content: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{filename_slug}.md"
    output_path.write_text(content.strip() + "\n", encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera script verticali per le offerte attive.")
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
    offer = pick_rotating_offer(offers_payload, site_config, today) if args.slug == "auto" else find_offer(offers_payload, args.slug)
    guide_url = build_guide_url(base_url, offer["guide_url"])
    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_VERTICAL_DIR

    if args.use_openai:
        filename_slug = f"{today.isoformat()}-{offer['slug']}-vertical-scripts"
        front = front_matter(f"Vertical Scripts {offer['name']} - {today.isoformat()}", filename_slug, offer["slug"], today.isoformat())
        content = front + call_openai(build_openai_prompt(offer, guide_url, site_config), args.model)
    else:
        filename_slug, content = build_template_output(offer, guide_url, site_config, today)

    output_path = write_output(output_dir, filename_slug, content)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
