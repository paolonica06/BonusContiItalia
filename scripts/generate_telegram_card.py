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

    font_brand = load_font("bold", 34)
    font_bank = load_font("bold", 42)
    font_badge = load_font("bold", 30)
    font_bonus = load_font("bold", 118)
    font_section = load_font("bold", 34)
    font_body = load_font("regular", 30)
    font_small = load_font("regular", 24)

    draw.rounded_rectangle((64, 56, 420, 120), radius=28, fill=(255, 255, 255, 230))
    draw.text((92, 74), "BONUSCONTIITALIA", font=font_brand, fill=hex_to_rgb(primary))

    bank_label = safe_image_label(offer)
    bank_bbox = draw.textbbox((0, 0), bank_label, font=font_bank)
    bank_width = bank_bbox[2] - bank_bbox[0] + 88
    draw.rounded_rectangle((width - bank_width - 64, 56, width - 64, 128), radius=30, fill=(9, 16, 30, 180))
    draw.text((width - bank_width - 22, 76), bank_label, font=font_bank, fill=(255, 255, 255))

    draw.rounded_rectangle((64, 164, width - 64, 456), radius=42, fill=(255, 255, 255, 245))
    draw.rounded_rectangle((88, 190, 336, 244), radius=18, fill=hex_to_rgb(accent))
    draw.text((112, 203), "BONUS CLIENTE", font=font_badge, fill=(9, 16, 30))
    draw.text((98, 258), offer["bonus_cliente"], font=font_bonus, fill=hex_to_rgb(primary))

    bonus_right_x = 410
    draw.text((bonus_right_x, 230), "Guadagno reale", font=font_section, fill=hex_to_rgb(primary))
    draw_wrapped_text(draw, (bonus_right_x, 282), offer["effective_gain"], font_section, (16, 22, 37), 540, 2, spacing=6)
    draw_wrapped_text(
        draw,
        (bonus_right_x, 336),
        offer["effective_gain_note"],
        font_body,
        (56, 66, 82),
        540,
        3,
        spacing=6,
    )

    draw.rounded_rectangle((64, 500, width - 64, 900), radius=42, fill=(9, 16, 30, 190))
    draw.text((96, 536), "COME OTTENERE IL BONUS", font=font_section, fill=(255, 255, 255))

    bullet_y = 606
    for index, item in enumerate(offer.get("requirements", [])[:3], start=1):
        circle_x = 112
        circle_y = bullet_y + (index - 1) * 88
        draw.ellipse((circle_x - 20, circle_y - 20, circle_x + 20, circle_y + 20), fill=hex_to_rgb(accent))
        draw.text((circle_x - 8, circle_y - 16), str(index), font=font_badge, fill=(8, 15, 29))
        draw_wrapped_text(
            draw,
            (154, circle_y - 24),
            item,
            font_body,
            (255, 255, 255),
            780,
            2,
            spacing=6,
        )

    chip_top = 940
    chip_width = (width - 64 * 2 - 24 * 2) // 3
    chips = [
        ("Difficolta", DIFFICULTY_LABELS.get(offer.get("difficulty", ""), offer.get("difficulty", ""))),
        ("Tempo", offer["estimated_time"]),
        ("Verifica", format_date(offer["last_verified_at"])),
    ]
    for index, (label, value) in enumerate(chips):
        left = 64 + index * (chip_width + 24)
        right = left + chip_width
        draw.rounded_rectangle((left, chip_top, right, chip_top + 132), radius=32, fill=(255, 255, 255, 232))
        draw.text((left + 28, chip_top + 26), label.upper(), font=font_small, fill=(67, 79, 100))
        draw_wrapped_text(draw, (left + 28, chip_top + 62), value, font_section, hex_to_rgb(primary), chip_width - 56, 2, spacing=4)

    draw.rounded_rectangle((64, 1112, width - 64, 1260), radius=38, fill=hex_to_rgb(accent))
    draw.text((98, 1154), "GUIDA PASSO PASSO SU BONUSCONTIITALIA", font=font_section, fill=(8, 15, 29))
    footer = base_url.replace("https://", "").replace("http://", "") if base_url else "Canale Telegram e guida completa in descrizione"
    draw_wrapped_text(draw, (100, 1200), footer, font_body, (8, 15, 29), width - 180, 1, spacing=4)

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
