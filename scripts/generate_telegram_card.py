#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import datetime as dt
import io
import json
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except Exception as exc:  # pragma: no cover - dependency checked at runtime
    Image = None
    ImageDraw = None
    ImageFilter = None
    ImageFont = None
    PIL_IMPORT_ERROR = exc
else:
    PIL_IMPORT_ERROR = None


ROOT = Path(__file__).resolve().parents[1]
OFFERS_PATH = ROOT / "data" / "offers.json"
SITE_CONFIG_PATH = ROOT / "data" / "site-config.json"
SIZE = (1080, 1350)

FONT_PATHS = {
    "bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ],
    "regular": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ],
}

DIFFICULTY_LABELS = {
    "easy": "Facile",
    "medium": "Media",
    "hard": "Alta",
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_offer(slug: str, payload: dict) -> dict:
    for offer in payload.get("offers", []):
        if offer.get("slug") == slug:
            return offer
    raise SystemExit(f"Offerta non trovata: {slug}")


def resolve_base_url(site_config: dict, cli_base_url: str) -> str:
    if cli_base_url:
        return cli_base_url.rstrip("/")
    configured = site_config.get("site", {}).get("base_url", "").rstrip("/")
    if configured in {"", "https://example.com", "http://example.com"}:
        return ""
    return configured


def format_date(value: str) -> str:
    try:
        parsed = dt.date.fromisoformat(value)
        return parsed.strftime("%d/%m/%Y")
    except ValueError:
        return value


def is_new_customer_offer(offer: dict) -> bool:
    for item in offer.get("requirements", []):
        if "nuovo cliente" in item.lower():
            return True
    return False


def offer_status_label(offer: dict) -> str:
    return "BONUS ATTIVO" if offer.get("bonus_cliente_fixed") else "PROMO ATTIVA"


def offer_support_headline(offer: dict) -> str:
    difficulty = DIFFICULTY_LABELS.get(offer.get("difficulty", ""), offer.get("difficulty", ""))
    if offer.get("bonus_cliente_fixed") and offer.get("difficulty") == "easy":
        return f"Attivabile in tempi rapidi con procedura {difficulty.lower()}."
    if offer.get("bonus_cliente_fixed"):
        return f"Bonus chiaro per chi vuole seguire una procedura {difficulty.lower()} senza improvvisare."
    return "Importo variabile: controlla il premio in app e segui la guida passo passo."


def offer_conversion_line(offer: dict) -> str:
    if is_new_customer_offer(offer):
        return "Solo nuovi clienti"
    return "Guida consigliata"


def offer_risk_reversal_line(offer: dict) -> str:
    if offer.get("bonus_cliente_fixed"):
        return "Segui i passaggi in ordine per non perdere il bonus."
    return "Verifica bene importo e requisiti prima di completare i passaggi."


def load_font(weight: str, size: int):
    if ImageFont is None:
        raise SystemExit(
            "Pillow non installato. Installa pillow oppure usa il workflow GitHub che lo installa automaticamente."
        )
    for candidate in FONT_PATHS[weight]:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def interpolate(start: int, end: int, ratio: float) -> int:
    return int(round(start + (end - start) * ratio))


def draw_vertical_gradient(image, start_hex: str, end_hex: str) -> None:
    start = hex_to_rgb(start_hex)
    end = hex_to_rgb(end_hex)
    width, height = image.size
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / max(1, height - 1)
        color = tuple(interpolate(start[i], end[i], ratio) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)


def cover_image(image, size: tuple[int, int]):
    width, height = size
    source_ratio = image.width / image.height
    target_ratio = width / height

    if source_ratio > target_ratio:
        resized_height = height
        resized_width = int(height * source_ratio)
    else:
        resized_width = width
        resized_height = int(width / source_ratio)

    resized = image.resize((resized_width, resized_height), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - width) // 2)
    top = max(0, (resized.height - height) // 2)
    return resized.crop((left, top, left + width, top + height))


def wrap_text(draw, text: str, font, max_width: int, max_lines: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""

    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
            continue

        if current:
            lines.append(current)
        current = word

        if len(lines) == max_lines:
            break

    if current and len(lines) < max_lines:
        lines.append(current)

    if words and len(lines) == max_lines:
        joined = " ".join(lines)
        if joined != text:
            last = lines[-1]
            while draw.textlength(last + "...", font=font) > max_width and len(last) > 1:
                last = last[:-1]
            lines[-1] = last.rstrip() + "..."

    return lines


def text_block_height(draw, lines: list[str], font, spacing: int) -> int:
    if not lines:
        return 0
    bbox = draw.textbbox((0, 0), "Ag", font=font)
    line_height = bbox[3] - bbox[1]
    return line_height * len(lines) + spacing * (len(lines) - 1)


def draw_wrapped_text(draw, position: tuple[int, int], text: str, font, fill, max_width: int, max_lines: int, spacing: int = 8) -> int:
    lines = wrap_text(draw, text, font, max_width, max_lines)
    x, y = position
    draw.multiline_text((x, y), "\n".join(lines), font=font, fill=fill, spacing=spacing)
    return text_block_height(draw, lines, font, spacing)


def safe_image_label(offer: dict) -> str:
    name = offer["name"]
    if len(name) <= 24:
        return name
    return offer["slug"].replace("-", " ").title()


def build_background_prompt(offer: dict) -> str:
    visual = offer.get("visual", {})
    palette = ", ".join(filter(None, [visual.get("primary"), visual.get("secondary"), visual.get("accent")]))
    return "\n".join(
        [
            "Use case: infographic-diagram",
            "Asset type: Telegram promo card background",
            f"Primary request: premium abstract fintech poster background for a promotional image about {offer['name']}",
            "Scene/background: clean vertical composition with geometric shapes, subtle gradients, soft depth, and generous empty areas for overlay text",
            "Subject: abstract financial atmosphere only, no people, no devices, no cards",
            "Style/medium: polished editorial digital poster background",
            "Composition/framing: vertical 4:5 layout, keep the upper center and lower center clean for text boxes",
            "Lighting/mood: bright, trustworthy, modern, energetic",
            f"Color palette: {palette}" if palette else "Color palette: deep blue, electric cyan, fresh green",
            "Constraints: no text, no numbers, no logos, no trademarks, no watermark",
            "Avoid: clutter, fake app screenshots, fake cards, busy patterns, illegible symbols",
        ]
    )


def generate_ai_background(prompt: str, model: str, quality: str):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY non impostata.")

    try:
        from openai import OpenAI
    except Exception as exc:  # pragma: no cover - dependency checked at runtime
        raise SystemExit("Manca il pacchetto openai. Installa openai oppure usa il workflow GitHub.") from exc

    client = OpenAI(api_key=api_key)
    result = client.images.generate(
        model=model,
        prompt=prompt,
        size="1024x1536",
        quality=quality,
        output_format="png",
    )
    image_b64 = result.data[0].b64_json
    return Image.open(io.BytesIO(base64.b64decode(image_b64))).convert("RGBA")


def build_base_image(offer: dict, use_openai_background: bool, model: str, quality: str):
    if Image is None:
        raise SystemExit(f"Pillow non disponibile: {PIL_IMPORT_ERROR}")

    image = Image.new("RGBA", SIZE, (0, 0, 0, 255))
    visual = offer.get("visual", {})
    primary = visual.get("primary", "#102B50")
    secondary = visual.get("secondary", "#1A85E0")
    accent = visual.get("accent", "#74C947")

    if use_openai_background:
        try:
            generated = generate_ai_background(build_background_prompt(offer), model, quality)
            image = cover_image(generated, SIZE)
        except Exception as exc:
            print(f"AI background non disponibile, uso fallback locale: {exc}", file=sys.stderr)
            draw_vertical_gradient(image, primary, secondary)
    else:
        draw_vertical_gradient(image, primary, secondary)

    draw = ImageDraw.Draw(image, "RGBA")
    width, height = SIZE

    draw.ellipse((width - 340, 30, width - 60, 310), fill=(*hex_to_rgb(accent), 70))
    draw.ellipse((-120, height - 360, 260, height + 20), fill=(255, 255, 255, 50))
    draw.rounded_rectangle((40, 40, width - 40, height - 40), radius=44, outline=(255, 255, 255, 55), width=2)
    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay, "RGBA")
    overlay_draw.rectangle((0, 0, width, height), fill=(9, 16, 30, 70))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=12))
    image.alpha_composite(overlay)
    return image


def render_card(offer: dict, base_url: str, out_path: Path, use_openai_background: bool, model: str, quality: str) -> Path:
    image = build_base_image(offer, use_openai_background, model, quality)
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size

    primary = offer.get("visual", {}).get("primary", "#102B50")
    accent = offer.get("visual", {}).get("accent", "#74C947")
    accent_rgb = hex_to_rgb(accent)
    primary_rgb = hex_to_rgb(primary)

    font_brand = load_font("bold", 30)
    font_bank = load_font("bold", 42)
    font_status = load_font("bold", 28)
    font_kicker = load_font("bold", 30)
    font_bonus = load_font("bold", 126 if len(offer["bonus_cliente"]) <= 6 else 96)
    font_title = load_font("bold", 42)
    font_section = load_font("bold", 32)
    font_body = load_font("regular", 30)
    font_body_small = load_font("regular", 27)
    font_chip = load_font("bold", 26)
    font_small = load_font("regular", 23)

    draw.rounded_rectangle((54, 48, width - 54, height - 48), radius=46, outline=(255, 255, 255, 44), width=2)

    draw.rounded_rectangle((64, 58, 382, 112), radius=24, fill=(255, 255, 255, 235))
    draw.text((88, 73), "BONUSCONTIITALIA", font=font_brand, fill=primary_rgb)

    status_text = offer_status_label(offer)
    status_width = draw.textbbox((0, 0), status_text, font=font_status)[2] + 62
    draw.rounded_rectangle((width - status_width - 64, 58, width - 64, 112), radius=24, fill=(*accent_rgb, 235))
    draw.text((width - status_width - 34, 72), status_text, font=font_status, fill=(8, 15, 29))

    draw.rounded_rectangle((64, 144, width - 64, 490), radius=42, fill=(255, 255, 255, 242))
    draw.rounded_rectangle((86, 166, 340, 214), radius=18, fill=(*accent_rgb, 245))
    draw.text((112, 178), "BONUS CLIENTE", font=font_kicker, fill=(8, 15, 29))
    draw.text((96, 234), offer["bonus_cliente"], font=font_bonus, fill=primary_rgb)

    bank_label = safe_image_label(offer)
    draw_wrapped_text(draw, (402, 184), bank_label, font_bank, primary_rgb, 560, 2, spacing=2)
    draw_wrapped_text(draw, (402, 250), offer_support_headline(offer), font_body, (39, 50, 66), 560, 3, spacing=6)

    hero_chip_data = [
        offer_conversion_line(offer),
        DIFFICULTY_LABELS.get(offer.get("difficulty", ""), offer.get("difficulty", "")),
        offer["estimated_time"],
    ]
    chip_x = 402
    chip_y = 372
    chip_spacing = 16
    for chip in hero_chip_data:
        text_width = min(300, int(draw.textbbox((0, 0), chip, font=font_chip)[2] + 48))
        if chip_x + text_width > width - 84:
            chip_x = 402
            chip_y += 70
        draw.rounded_rectangle((chip_x, chip_y, chip_x + text_width, chip_y + 54), radius=18, fill=(13, 24, 43, 212))
        draw.text((chip_x + 22, chip_y + 14), chip, font=font_chip, fill=(255, 255, 255))
        chip_x += text_width + chip_spacing

    draw.rounded_rectangle((64, 524, width - 64, 588), radius=24, fill=(*accent_rgb, 232))
    draw_wrapped_text(
        draw,
        (96, 542),
        offer_risk_reversal_line(offer),
        font_section,
        (8, 15, 29),
        width - 192,
        2,
        spacing=4,
    )

    draw.rounded_rectangle((64, 618, width - 64, 972), radius=42, fill=(9, 16, 30, 196))
    draw.text((96, 650), "3 PASSAGGI DA COMPLETARE", font=font_title, fill=(255, 255, 255))
    draw.text((96, 700), "Seguili in ordine e non saltare nessun requisito.", font=font_body_small, fill=(200, 211, 226))

    step_y = 782
    for index, item in enumerate(offer.get("requirements", [])[:3], start=1):
        bubble_x = 114
        bubble_y = step_y + (index - 1) * 86
        draw.ellipse((bubble_x - 23, bubble_y - 23, bubble_x + 23, bubble_y + 23), fill=(*accent_rgb, 255))
        draw.text((bubble_x - 10, bubble_y - 18), str(index), font=font_chip, fill=(8, 15, 29))
        draw_wrapped_text(draw, (164, bubble_y - 24), item, font_body, (255, 255, 255), 780, 2, spacing=6)

    chip_top = 1012
    chip_width = (width - 64 * 2 - 24 * 2) // 3
    chips = [
        ("Guadagno", offer["effective_gain"]),
        ("Verifica", format_date(offer["last_verified_at"])),
        ("Extra", offer.get("bonus_note") or "Guida passo passo"),
    ]
    for index, (label, value) in enumerate(chips):
        left = 64 + index * (chip_width + 24)
        right = left + chip_width
        draw.rounded_rectangle((left, chip_top, right, chip_top + 148), radius=32, fill=(255, 255, 255, 232))
        draw.text((left + 26, chip_top + 24), label.upper(), font=font_small, fill=(67, 79, 100))
        draw_wrapped_text(draw, (left + 26, chip_top + 60), value, font_section, primary_rgb, chip_width - 52, 3, spacing=4)

    draw.rounded_rectangle((64, 1192, width - 64, 1286), radius=36, fill=(*accent_rgb, 255))
    draw.text((92, 1218), "APRI LA GUIDA E SEGUI I PASSAGGI", font=font_section, fill=(8, 15, 29))
    footer = base_url.replace("https://", "").replace("http://", "") if base_url else "Link completo nel post Telegram"
    draw_wrapped_text(draw, (94, 1250), footer, font_small, (8, 15, 29), width - 188, 1, spacing=4)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(out_path, format="PNG")
    return out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera una card promo Telegram per un'offerta.")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--base-url", default="")
    parser.add_argument("--out", default="tmp/telegram/promo-card.png")
    parser.add_argument("--use-openai-background", action="store_true")
    parser.add_argument("--openai-model", default="gpt-image-1-mini")
    parser.add_argument("--openai-quality", default="low")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    offers_payload = load_json(OFFERS_PATH)
    site_config = load_json(SITE_CONFIG_PATH)
    offer = find_offer(args.slug, offers_payload)
    base_url = resolve_base_url(site_config, args.base_url)
    output_path = render_card(
        offer,
        base_url,
        Path(args.out),
        use_openai_background=args.use_openai_background,
        model=args.openai_model,
        quality=args.openai_quality,
    )
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
