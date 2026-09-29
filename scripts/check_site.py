#!/usr/bin/env python3
"""Controlli statici del sito. Solo libreria standard. Exit 1 se ci sono errori.

Non stampa mai URL referral o codici: solo nome file e tipo di problema.
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
errors = []
warnings = []
REFERRAL_WORDS = ("codice invito", "referral", "#adv")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#", "//", "data:", "javascript:")


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.has_title = False
        self.has_description = False
        self.has_viewport = False
        self.lang = ""
        self.links = []
        self.external = []
        self._in_title = False
        self._title_text = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = (a.get("lang") or "").lower()
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = (a.get("name") or "").lower()
            if name == "description" and (a.get("content") or "").strip():
                self.has_description = True
            if name == "viewport":
                self.has_viewport = True
        for key in ("href", "src"):
            value = a.get(key)
            if value is None:
                continue
            value = value.strip()
            if value.lower().startswith(("http://", "https://")):
                self.external.append(value)
            elif value and not value.lower().startswith(SKIP_PREFIXES):
                self.links.append(value)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
            self.has_title = bool(self._title_text.strip())

    def handle_data(self, data):
        if self._in_title:
            self._title_text += data


def check_json():
    count = 0
    for path in sorted((ROOT / "data").glob("**/*.json")):
        count += 1
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            errors.append(f"{path.relative_to(ROOT)}: JSON non valido")
    return count


def bank_domains():
    domains = set()
    try:
        data = json.loads((ROOT / "data" / "offers.json").read_text(encoding="utf-8"))
    except Exception:
        return domains
    for offer in data.get("offers", []):
        for key, value in offer.items():
            if key.endswith("_url") and isinstance(value, str):
                host = urlparse(value).netloc.lower()
                if host:
                    domains.add(host)
    return domains


def check_pages(domains):
    pages = sorted(ROOT.glob("*.html"))
    for page in pages:
        name = page.name
        text = page.read_text(encoding="utf-8", errors="replace")
        parser = PageParser()
        parser.feed(text)
        if not parser.has_title:
            errors.append(f"{name}: manca <title>")
        if not parser.has_description:
            errors.append(f"{name}: manca meta description")
        if not parser.has_viewport:
            errors.append(f"{name}: manca meta viewport")
        if not parser.lang.startswith("it"):
            errors.append(f"{name}: manca lang=\"it\"")
        for link in parser.links:
            target = re.split(r"[?#]", link)[0]
            if not target:
                continue
            base = ROOT if target.startswith("/") else page.parent
            if not (base / target.lstrip("/")).exists():
                errors.append(f"{name}: link interno rotto")
        has_bank_link = any(urlparse(u).netloc.lower() in domains for u in parser.external)
        if has_bank_link and not any(w in text.lower() for w in REFERRAL_WORDS):
            warnings.append(f"{name}: link referral senza dicitura referral")
    return len(pages)


def check_scripts():
    count = 0
    for path in sorted((ROOT / "scripts").glob("*.py")):
        count += 1
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except (SyntaxError, ValueError):
            errors.append(f"scripts/{path.name}: errore di compilazione")
    return count


def main():
    n_json = check_json()
    n_pages = check_pages(bank_domains())
    n_scripts = check_scripts()
    for line in errors:
        print(f"ERRORE {line}")
    for line in warnings:
        print(f"AVVISO {line}")
    print(
        f"{n_json} JSON, {n_pages} pagine, {n_scripts} script: "
        f"{len(errors)} errori, {len(warnings)} avvisi"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
