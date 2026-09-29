#!/usr/bin/env python3
"""Post Telegram solo quando un'offerta cambia, più riepilogo settimanale."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import subprocess
import sys
from pathlib import Path

import render_telegram_post as render

STATE_PATH = render.ROOT / "data" / "telegram-state.json"
CARD_PATH = render.ROOT / "tmp" / "telegram" / "promo-card.png"
SCRIPTS = Path(__file__).resolve().parent

# Campi che, se cambiano, meritano un post. Il resto (verifiche, colori, link) è ignorato.
FIELD_LABELS = {
    "name": "titolo",
    "status": "stato",
    "bonus_cliente": "importo del bonus",
    "bonus_cliente_fixed": "importo del bonus",
    "effective_gain": "guadagno effettivo",
    "bonus_note": "scadenza o note della promo",
    "requirements": "requisiti",
    "deposit_required": "requisiti",
    "effective_gain_note": "requisiti",
}
MODES = ("auto", "force-weekly", "dry-run")
EXPIRY_RE = re.compile(r"fino al ([^,.;]*\d{4})", re.IGNORECASE)


def short_hash(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def fingerprint(offer: dict) -> dict:
    fields = {name: short_hash(offer.get(name)) for name in FIELD_LABELS}
    return {"hash": short_hash(fields), "fields": fields}


def build_state(offers: list[dict]) -> dict:
    return {"version": 1, "offers": {o["slug"]: fingerprint(o) for o in offers}}


def describe_change(old: dict, new: dict) -> str:
    labels = []
    for name, digest in new["fields"].items():
        if old.get("fields", {}).get(name) == digest:
            continue
        label = FIELD_LABELS[name]
        if label not in labels:
            labels.append(label)
    return "Aggiornato: " + ", ".join(labels)


def detect_changes(offers: list[dict], state: dict) -> list[dict]:
    """Offerte nuove o cambiate rispetto allo stato salvato."""
    known = state.get("offers", {})
    changes = []
    for offer in offers:
        current = fingerprint(offer)
        previous = known.get(offer["slug"])
        if previous is None:
            note = "Novità: nuova offerta"
        elif previous.get("hash") != current["hash"]:
            note = describe_change(previous, current)
        else:
            continue
        changes.append({"offer": offer, "note": note})
    return changes


def mask(text: str, offers: list[dict]) -> str:
    """Nasconde codici invito e link referral prima di stampare nei log."""
    values = []
    for offer in offers:
        for key in ("referral_code", "referral_url"):
            value = (offer.get(key) or "").strip()
            if value:
                values.append(value)
    for value in sorted(values, key=len, reverse=True):
        text = text.replace(value, "***")
        text = text.replace(html.escape(value), "***")
    return text


def expiry_of(offer: dict) -> str:
    match = EXPIRY_RE.search(offer.get("bonus_note", ""))
    if match:
        return f"valida fino al {match.group(1).strip()}"
    return "scadenza non indicata"


def weekly_line(offer: dict, base_url: str) -> str:
    name = html.escape(offer["name"])
    bonus = html.escape(offer["bonus_cliente"])
    line = f"• <b>{name}</b>: {bonus}, {expiry_of(offer)}"
    guide = render.build_guide_url(base_url, offer.get("guide_url", ""))
    if guide:
        line += f' - <a href="{html.escape(guide)}">guida</a>'
    return line


def build_weekly_text(offers: list[dict], base_url: str) -> str:
    lines = ["📋 <b>Riepilogo settimanale: bonus attivi</b>", ""]
    lines.extend(weekly_line(offer, base_url) for offer in offers)
    lines.extend(["", "Apri la guida di ogni banca per passaggi e requisiti aggiornati."])
    return "\n".join(lines)


def weekly_payload(offers: list[dict], base_url: str) -> dict:
    return {
        "slug": "weekly",
        "offer_name": "Riepilogo settimanale",
        "text": build_weekly_text(offers, base_url),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }


def change_payload(change: dict, site_config: dict, base_url: str) -> dict:
    payload = render.build_payload(change["offer"], site_config, base_url)
    payload["text"] = f"🔔 <b>{html.escape(change['note'])}</b>\n\n" + payload["text"]
    return payload


def make_card(slug: str, base_url: str) -> str:
    command = [sys.executable, str(SCRIPTS / "generate_telegram_card.py")]
    command += ["--slug", slug, "--base-url", base_url, "--out", str(CARD_PATH)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"Card non generata per {slug}: invio senza immagine.")
        return ""
    return str(CARD_PATH)


def send(payload: dict) -> bool:
    """Invia via send_telegram.py: usa solo TELEGRAM_CHAT_ID dell'ambiente."""
    command = [sys.executable, str(SCRIPTS / "send_telegram.py")]
    body = json.dumps(payload, ensure_ascii=False)
    result = subprocess.run(command, input=body, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        print(f"Invio fallito per {payload.get('slug')}: {result.stderr.strip()[:200]}")
    return result.returncode == 0


def show(payload: dict, offers: list[dict]) -> None:
    print(f"--- {payload.get('offer_name')} ---")
    print(mask(payload["text"], offers))
    for row in payload.get("reply_markup", {}).get("inline_keyboard", []):
        print("[" + " | ".join(button["text"] for button in row) + "]")


def load_state(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    text = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")


def should_send_weekly(mode: str, today: dt.date) -> bool:
    if mode == "force-weekly":
        return True
    return today.weekday() == 0


def collect_messages(args: argparse.Namespace, ctx: dict) -> list[dict]:
    messages = []
    state = load_state(Path(args.state))
    if args.mode == "force-weekly":
        pass
    elif state is None:
        print("Stato iniziale assente: lo creo senza pubblicare nulla.")
    else:
        for change in detect_changes(ctx["active"], state):
            print(f"Cambio rilevato per {change['offer']['slug']}: {change['note']}")
            messages.append(change_payload(change, ctx["site_config"], ctx["base_url"]))
        if not messages:
            print("Nessuna offerta cambiata: non invio nulla.")
    if should_send_weekly(args.mode, ctx["today"]) and ctx["active"]:
        messages.append(weekly_payload(ctx["active"], ctx["base_url"]))
    return messages


def deliver(message: dict, base_url: str) -> bool:
    if message["slug"] != "weekly":
        photo = make_card(message["slug"], base_url)
        if photo:
            message["photo_path"] = photo
    if not send(message):
        return False
    print(f"Inviato: {message['offer_name']}")
    return True


def run(args: argparse.Namespace) -> int:
    payload = render.load_json(Path(args.offers))
    site_config = render.load_json(render.SITE_CONFIG_PATH)
    ctx = {
        "site_config": site_config,
        "base_url": render.resolve_base_url(site_config, args.base_url),
        "today": dt.date.fromisoformat(args.today) if args.today else dt.date.today(),
        "active": render.active_offers(payload, site_config),
    }
    all_offers = payload.get("offers", [])
    dry = args.mode == "dry-run"
    for message in collect_messages(args, ctx):
        if dry:
            show(message, all_offers)
        elif not deliver(message, ctx["base_url"]):
            return 1
    if dry or args.mode == "force-weekly":
        return 0
    save_state(Path(args.state), build_state(payload.get("offers", [])))
    print("Stato salvato.")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES, default="auto")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--today", default="")
    parser.add_argument("--state", default=str(STATE_PATH))
    parser.add_argument("--offers", default=str(render.OFFERS_PATH))
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
