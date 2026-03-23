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
DEFAULT_OUTPUT_DIR = ROOT / "content" / "blog" / "drafts"
DEFAULT_MODEL = "gpt-5-mini"

DIFFICULTY_LABELS = {
    "easy": "facile",
    "medium": "media",
    "hard": "alta",
}

CATEGORY_LABELS = {
    "conto": "conto",
    "app": "app finanziaria",
    "investimento": "servizio di investimento",
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_offer(payload: dict, slug: str) -> dict:
    for offer in payload.get("offers", []):
        if offer.get("slug") == slug:
            return offer
    raise SystemExit(f"Offerta non trovata: {slug}")


def active_offers(payload: dict) -> list[dict]:
    return [offer for offer in payload.get("offers", []) if offer.get("status") == "active"]


def month_label(today: dt.date) -> str:
    months = [
        "gennaio",
        "febbraio",
        "marzo",
        "aprile",
        "maggio",
        "giugno",
        "luglio",
        "agosto",
        "settembre",
        "ottobre",
        "novembre",
        "dicembre",
    ]
    return f"{months[today.month - 1]} {today.year}"


def front_matter(title: str, slug: str, excerpt: str, tags: list[str], created_at: str) -> str:
    tags_list = ", ".join(f'"{tag}"' for tag in tags)
    return textwrap.dedent(
        f"""\
        ---
        title: "{title}"
        slug: "{slug}"
        excerpt: "{excerpt}"
        status: "draft"
        created_at: "{created_at}"
        tags: [{tags_list}]
        ---

        """
    )


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


def render_requirements(items: list[str]) -> str:
    if not items:
        return "- Controlla sempre le condizioni complete sulla pagina ufficiale."
    return "\n".join(f"- {item}" for item in items)


def humanize_difficulty(value: str) -> str:
    return DIFFICULTY_LABELS.get(value, value)


def humanize_category(value: str) -> str:
    return CATEGORY_LABELS.get(value, value)


def build_offer_template(offer: dict, base_url: str, today: dt.date) -> tuple[str, str, str]:
    title = f"Bonus {offer['name']} aggiornato a {month_label(today)}"
    filename_slug = f"{today.isoformat()}-{offer['slug']}"
    excerpt = f"Guida rapida al bonus {offer['name']}: importo cliente, requisiti principali e quando conviene."
    fm = front_matter(title, filename_slug, excerpt, ["bonus", offer["slug"], "conti"], today.isoformat())

    requirements = render_requirements(offer.get("requirements", []))
    guide_url = build_guide_url(base_url, offer["guide_url"])
    difficulty_label = humanize_difficulty(offer.get("difficulty", ""))
    category_label = humanize_category(offer.get("category", ""))

    body = "\n".join(
        [
            "## Quanto si guadagna",
            "",
            f"Il bonus cliente indicato per questa offerta e **{offer['bonus_cliente']}**.",
            "",
            f"**Guadagno effettivo:** {offer['effective_gain']}",
            "",
            offer["effective_gain_note"],
            "",
            "## Cosa bisogna fare",
            "",
            requirements,
            "",
            "## Quanto e difficile",
            "",
            f"Difficolta stimata: **{difficulty_label}**",
            "",
            f"Tempo medio: **{offer['estimated_time']}**",
            "",
            "## A chi conviene",
            "",
            (
                f"Questa offerta puo essere interessante per chi cerca una promo legata a un "
                f"{category_label} e preferisce una procedura di difficolta **{difficulty_label}**."
            ),
            "",
            "## Cosa controllare prima di iniziare",
            "",
            "- Verifica che la promo sia ancora attiva.",
            "- Controlla le condizioni complete sulla pagina ufficiale.",
            "- Segui la guida dedicata se vuoi una spiegazione piu ordinata.",
            "",
            "## Link utili",
            "",
            f"- Guida completa: {guide_url}",
            f"- Fonte ufficiale: {offer['official_url']}",
            f"- Ultima verifica dati: {offer['last_verified_at']}",
        ]
    )

    return title, filename_slug, fm + body + "\n"


def build_roundup_template(offers: list[dict], base_url: str, today: dt.date) -> tuple[str, str, str]:
    title = f"Migliori bonus conti aggiornati a {month_label(today)}"
    filename_slug = f"{today.isoformat()}-migliori-bonus-conti"
    excerpt = "Confronto aggiornato dei bonus piu interessanti tra BBVA, buddybank, Revolut e Trade Republic."
    fm = front_matter(title, filename_slug, excerpt, ["bonus", "confronto", "conti"], today.isoformat())

    rows = []
    for offer in offers:
        guide_url = build_guide_url(base_url, offer["guide_url"])
        difficulty_label = humanize_difficulty(offer.get("difficulty", ""))
        rows.append(
            "\n".join(
                [
                    f"### {offer['name']}",
                    "",
                    f"- Bonus cliente: **{offer['bonus_cliente']}**",
                    f"- Guadagno effettivo: **{offer['effective_gain']}**",
                    f"- Difficolta: **{difficulty_label}**",
                    f"- Tempo stimato: **{offer['estimated_time']}**",
                    f"- Guida: {guide_url}",
                    f"- Fonte ufficiale: {offer['official_url']}",
                ]
            )
        )

    summary = textwrap.dedent(
        """\
        ## Qual e il bonus migliore in questo momento

        In generale, le promo con importo cliente fisso e condizioni piu chiare sono quelle che rendono meglio per chi cerca un guadagno piu leggibile e meno variabile.

        ## Confronto veloce

        """
    )

    ending = textwrap.dedent(
        """\

        ## Come scegliere

        - Se vuoi una promo semplice: guarda prima BBVA.
        - Se vuoi il bonus cliente piu alto: controlla buddybank.
        - Se vuoi app molto conosciute: valuta Revolut.
        - Se vuoi una promo piu avanzata: leggi bene Trade Republic.
        """
    )

    body = summary + "\n\n".join(rows) + "\n\n" + ending.strip() + "\n"
    return title, filename_slug, fm + body


def build_openai_prompt_offer(offer: dict, base_url: str, today: dt.date) -> tuple[str, str, str]:
    title = f"Bonus {offer['name']} aggiornato a {month_label(today)}"
    filename_slug = f"{today.isoformat()}-{offer['slug']}"
    excerpt = f"Guida rapida al bonus {offer['name']}: importo cliente, requisiti principali e quando conviene."
    guide_url = build_guide_url(base_url, offer["guide_url"])
    prompt = textwrap.dedent(
        f"""\
        Scrivi un articolo blog in italiano, chiaro e affidabile, con tono semplice e utile per utenti finali.
        Restituisci solo il corpo in Markdown, senza front matter.

        Dati offerta:
        - Nome: {offer['name']}
        - Bonus cliente: {offer['bonus_cliente']}
        - Guadagno effettivo: {offer['effective_gain']}
        - Nota guadagno: {offer['effective_gain_note']}
        - Difficolta: {offer['difficulty']}
        - Tempo stimato: {offer['estimated_time']}
        - Requisiti: {", ".join(offer.get('requirements', []))}
        - Fonte ufficiale: {offer['official_url']}
        - Guida completa: {guide_url}
        - Ultima verifica: {offer['last_verified_at']}

        Struttura obbligatoria:
        ## Quanto si guadagna
        ## Cosa bisogna fare
        ## A chi conviene
        ## Cosa controllare prima di iniziare
        ## Link utili

        Regole:
        - Non inventare importi o condizioni.
        - Se un dato e variabile, dillo chiaramente.
        - Non usare tono promozionale aggressivo.
        - Massimo 500 parole.
        """
    )
    fm = front_matter(title, filename_slug, excerpt, ["bonus", offer["slug"], "conti"], today.isoformat())
    return filename_slug, fm, prompt


def build_openai_prompt_roundup(offers: list[dict], base_url: str, today: dt.date) -> tuple[str, str, str]:
    title = f"Migliori bonus conti aggiornati a {month_label(today)}"
    filename_slug = f"{today.isoformat()}-migliori-bonus-conti"
    excerpt = "Confronto aggiornato dei bonus piu interessanti tra BBVA, buddybank, Revolut e Trade Republic."

    offers_block = []
    for offer in offers:
        guide_url = build_guide_url(base_url, offer["guide_url"])
        offers_block.append(
            f"- {offer['name']}: bonus cliente {offer['bonus_cliente']}, guadagno effettivo {offer['effective_gain']}, difficolta {offer['difficulty']}, tempo {offer['estimated_time']}, fonte {offer['official_url']}, guida {guide_url}"
        )

    prompt = textwrap.dedent(
        f"""\
        Scrivi un articolo blog in italiano, chiaro e affidabile, che confronti le migliori offerte attive del sito.
        Restituisci solo il corpo in Markdown, senza front matter.

        Offerte:
        {chr(10).join(offers_block)}

        Struttura obbligatoria:
        ## Qual e il bonus migliore in questo momento
        ## Confronto veloce
        ## Come scegliere

        Regole:
        - Non inventare importi.
        - Distingui sempre tra bonus fisso e bonus variabile.
        - Mantieni tono utile e leggibile.
        - Massimo 700 parole.
        """
    )

    fm = front_matter(title, filename_slug, excerpt, ["bonus", "confronto", "conti"], today.isoformat())
    return filename_slug, fm, prompt


def call_openai(prompt: str, model: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY non impostata.")

    payload = {
        "model": model,
        "input": prompt
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
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


def write_output(output_dir: Path, filename_slug: str, content: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{filename_slug}.md"
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write(content.strip() + "\n")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera bozze blog automatiche dalle offerte.")
    parser.add_argument("--mode", choices=["offer", "roundup"], default="offer")
    parser.add_argument("--slug")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--base-url", default="")
    parser.add_argument("--use-openai", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    today = dt.date.today()
    offers_payload = load_json(OFFERS_PATH)
    site_config = load_json(SITE_CONFIG_PATH)
    output_dir = Path(args.output_dir)
    base_url = resolve_base_url(site_config, args.base_url)

    if args.mode == "offer":
        if not args.slug:
            raise SystemExit("Con mode=offer devi passare --slug.")
        offer = find_offer(offers_payload, args.slug)
        if args.use_openai:
            filename_slug, front, prompt = build_openai_prompt_offer(offer, base_url, today)
            content = front + call_openai(prompt, args.model)
        else:
            _title, filename_slug, content = build_offer_template(offer, base_url, today)
    else:
        offers = active_offers(offers_payload)
        if args.use_openai:
            filename_slug, front, prompt = build_openai_prompt_roundup(offers, base_url, today)
            content = front + call_openai(prompt, args.model)
        else:
            _title, filename_slug, content = build_roundup_template(offers, base_url, today)

    path = write_output(output_dir, filename_slug, content)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
