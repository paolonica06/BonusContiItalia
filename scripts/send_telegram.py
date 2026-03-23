#!/usr/bin/env python3

from __future__ import annotations

import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


def build_multipart_payload(fields: dict[str, str], files: dict[str, Path]) -> tuple[bytes, str]:
    boundary = f"----CodexTelegram{uuid.uuid4().hex}"
    chunks: list[bytes] = []

    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )

    for name, path in files.items():
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{path.name}"\r\n'
                ).encode("utf-8"),
                f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"),
                path.read_bytes(),
                b"\r\n",
            ]
        )

    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), boundary


def main() -> int:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()

    if not token or not chat_id:
        print("Mancano TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID.", file=sys.stderr)
        return 1

    if any(char.isspace() for char in token):
        print("TELEGRAM_BOT_TOKEN non valido: contiene spazi o ritorni a capo.", file=sys.stderr)
        return 1

    if any(char.isspace() for char in chat_id):
        print("TELEGRAM_CHAT_ID non valido: contiene spazi o ritorni a capo.", file=sys.stderr)
        return 1

    if sys.stdin.isatty():
        print("Passa il testo del messaggio via stdin.", file=sys.stderr)
        return 1

    raw_input = sys.stdin.read().strip()
    if not raw_input:
        print("Messaggio vuoto.", file=sys.stderr)
        return 1

    try:
        message_payload = json.loads(raw_input)
    except json.JSONDecodeError:
        message_payload = {"text": raw_input}

    if not isinstance(message_payload, dict) or not message_payload.get("text"):
        print("Payload Telegram non valido.", file=sys.stderr)
        return 1

    request_payload = {
        "chat_id": chat_id,
        "text": message_payload["text"],
        "disable_web_page_preview": str(message_payload.get("disable_web_page_preview", False)).lower(),
    }

    if message_payload.get("parse_mode"):
        request_payload["parse_mode"] = message_payload["parse_mode"]

    if message_payload.get("reply_markup"):
        request_payload["reply_markup"] = json.dumps(message_payload["reply_markup"], ensure_ascii=False)

    photo_path = message_payload.get("photo_path")
    if photo_path:
        path = Path(photo_path)
        if not path.exists():
            print(f"Immagine Telegram non trovata: {path}", file=sys.stderr)
            return 1

        payload = {
            "chat_id": chat_id,
            "caption": message_payload["text"],
        }
        if message_payload.get("parse_mode"):
            payload["parse_mode"] = message_payload["parse_mode"]
        if message_payload.get("reply_markup"):
            payload["reply_markup"] = json.dumps(message_payload["reply_markup"], ensure_ascii=False)

        multipart_body, boundary = build_multipart_payload(payload, {"photo": path})
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendPhoto",
            data=multipart_body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
    else:
        payload = urllib.parse.urlencode(request_payload).encode("utf-8")

        request = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            method="POST",
        )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        print(f"Errore Telegram API: {exc.code} {details}", file=sys.stderr)
        return 1

    print("Messaggio Telegram inviato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
