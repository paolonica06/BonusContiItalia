#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
import urllib.parse
import urllib.request


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Mancano TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID.", file=sys.stderr)
        return 1

    if sys.stdin.isatty():
        print("Passa il testo del messaggio via stdin.", file=sys.stderr)
        return 1

    message = sys.stdin.read().strip()
    if not message:
        print("Messaggio vuoto.", file=sys.stderr)
        return 1

    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": "false",
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()

    print("Messaggio Telegram inviato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
