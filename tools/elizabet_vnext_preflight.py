#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

ROOT = Path(__file__).resolve().parents[1]
STOCK = ROOT / 'stock-vnext'
OUT = ROOT / 'vnext-preflight'
FRAMES = OUT / 'frames'
W, H, FPS, DURATION = 540, 960, 30, 15

ASSETS = {
    'couple': (5493219, '055e51ab4970696b3dfa1a41277983eaf24c3e8cb0f9b8aaba5cf4e8f8548136'),
    'gift': (7910649, 'b31cadb0f296e84be182a27e59c0ee991dba269e40c5894ccf81d1397f341964'),
    'hands': (7715723, '2c4e019bbfee0237b4cf9eaa7dd071d9b229b591c8851aba13f65034a0afe9df'),
    'polaroid': (6188753, 'e108091e08008f28e01008deabe0dc7869231982d0f964d7df86a98745e2c6b7'),
    'letter': (10660565, '189307064b4ff3f3afd47ded59ba23ed0d036da125da897bbe2a153f2a7c96c3'),
    'city': (7922285, 'ef3ad90421fdc21f0f0fe5723655e0b9f3d5b2066b5de912f87f87ef7544f506'),
}

# V3: the opening now reads as an actual gift immediately; the connection beat is
# unmistakably a couple's hands; the emotional payoff returns to the couple.
# Product proof remains only two seconds and never owns the ending.
BEATS = [
    (0.0, 1.25, 'gift', 'Не ещё одну вещь.', 'hook'),
    (1.25, 2.5, 'hands', 'То, что уже ваше.', 'copy'),
    (2.5, 4.2, 'polaroid', 'Фото, которые хочется сохранить.', 'copy'),
    (4.2, 5.9, 'letter', 'Слова, которые значат больше.', 'copy'),
    (5.9, 7.6, 'city', 'Место, с которого всё началось.', 'copy'),
    (7.6, 9.4, 'polaroid', 'Собери это в один подарок.', 'memories'),
    (9.4, 11.4, 'polaroid', '', 'proof'),
    (11.4, 13.1, 'couple', 'Подарок, к которому возвращаются.', 'copy'),
    (13.1, 15.0, 'couple', 'Собрать Gift Room →', 'cta'),
]

FONT_REG = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT = ImageFont.truetype(FONT_REG, 27)
FONT_SMALL = ImageFont.truetype(FONT_REG, 17)
FONT_TINY = ImageFont.truetype(FONT_BOLD, 12)
FONT_HOOK = ImageFont.truetype(FONT_BOLD, 43)
FONT_CTA = ImageFont.truetype(FONT_BOLD, 36)
FONT_BRAND = ImageFont.truetype(FONT_BOLD, 13)
FONT_PROOF = ImageFont.truetype(FONT_BOLD, 32)

FOCUS = {
    'couple': (.50, .47),
    'gift': (.50, .52),
    'hands': (.50, .54),
    'polaroid': (.50, .57),
    'letter': (.54, .48),
    'city': (.52, .52),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def cover(image: Image.Image, t: float, seed: float, key: str) -> Image.Image:
    scale = 1.045 + 0.026 * t
    ratio = max(W / image.width, H / image.height) * scale
    rw, rh = int(image.width * ratio), int(image.height * ratio)
    resized = image.resize((rw, rh), Image.Resampling.LANCZOS)
    max_x, max_y = max(0, rw - W), max(0, rh - H)
    fx, fy = FOCUS[key]
    drift_x = .012 * math.sin(seed * .61 + t * 1.15)
    drift_y = .010 * math.cos(seed * .49 + t * .92)
    x = int(max_x * clamp01(fx + drift_x))
    y = int(max_y * clamp01(fy + drift_y))
    frame = resized.crop((x, y, x + W, y + H))
    frame = ImageEnhance.Color(frame).enhance(.94)
    frame = ImageEnhance.Contrast(frame).enhance(1.025)
    frame = ImageEnhance.Brightness(frame).enhance(.99)
    return frame


def crossfade(images: dict[str, Image.Image], key: str, previous: str | None, p: float, seed: int) -> Image.Image:
    current = cover(images[key], p, seed, key)
    if previous is None or previous == key or p >= .16:
        return current
    previous_frame = cover(images[previous], 1.0, seed - 1, previous)
    mix = clamp01(p / .16)
    return Image.blend(previous_frame, current, mix)


def gradient(frame: Image.Image) -> Image.Image:
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    px = overlay.load()
    for y in range(H):
        u = y / (H - 1)
        bottom = max(0.0, (u - .56) / .44) ** 1.6
        top = max(0.0, (.14 - u) / .14) * .12
        alpha = int(5 + bottom * 188 + top * 80)
        for x in range(W):
            px[x, y] = (12, 8, 11, min(215, alpha))
    return Image.alpha_composite(frame.convert('RGBA'), overlay)


def brand(frame: Image.Image):
    draw = ImageDraw.Draw(frame)
    draw.ellipse((28, 35, 36, 43), fill=(255, 112, 104, 255))
    draw.text((44, 32), 'ELIZABETH', font=FONT_BRAND, fill=(255, 248, 239, 235))


def shadow_text(draw: ImageDraw.ImageDraw, xy, value: str, font, fill=(255, 248, 239), spacing=5):
    x, y = xy
    draw.multiline_text((x + 2, y + 3), value, font=font, fill=(0, 0, 0, 150), spacing=spacing)
    draw.multiline_text((x, y), value, font=font, fill=fill, spacing=spacing)


def memory_chips(frame: Image.Image, images: dict[str, Image.Image]):
    layer = Image.new('RGBA', frame.size, (0, 0, 0, 0))
    labels = [('Фото', 'polaroid'), ('Письмо', 'letter'), ('Место', 'city'), ('Мы', 'hands')]
    cell_w = 104
    start = 40
    for i, (label, key) in enumerate(labels):
        x = start + i * 115
        thumb = cover(images[key], .45, i + 7, key).resize((cell_w, 108), Image.Resampling.LANCZOS)
        mask = Image.new('L', thumb.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, cell_w, 108), radius=15, fill=245)
        thumb.putalpha(mask)
        layer.alpha_composite(thumb, (x, 708))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle((x + 14, 825, x + cell_w - 14, 854), radius=14, fill=(18, 14, 18, 160))
        d.text((x + cell_w // 2, 839), label, font=FONT_TINY, fill=(255, 248, 239, 235), anchor='mm')
    return Image.alpha_composite(frame, layer)


def proof_card(frame: Image.Image, images: dict[str, Image.Image]):
    layer = Image.new('RGBA', frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x1, y1, x2, y2 = 46, 604, W - 46, 855
    d.rounded_rectangle((x1, y1, x2, y2), radius=30, fill=(18, 15, 20, 220), outline=(255, 255, 255, 58), width=1)
    d.text((x1 + 24, y1 + 22), 'ВАША ИСТОРИЯ', font=FONT_TINY, fill=(235, 226, 219, 175))
    d.text((x1 + 24, y1 + 47), 'Gift Room', font=FONT_PROOF, fill=(255, 248, 239, 255))
    d.text((x1 + 24, y1 + 91), 'Фото · письма · места · планы', font=FONT_SMALL, fill=(245, 236, 231, 205))
    d.rounded_rectangle((x2 - 116, y1 + 22, x2 - 22, y1 + 56), radius=17, fill=(255, 112, 104, 230))
    d.text((x2 - 69, y1 + 39), 'ЛИЧНОЕ', font=FONT_TINY, fill=(24, 18, 22, 255), anchor='mm')
    keys = ['polaroid', 'letter', 'city', 'hands']
    labels = ['Фото', 'Письмо', 'Место', 'Мы']
    cell_w = 91
    for i, key in enumerate(keys):
        cx = x1 + 22 + i * 101
        thumb = cover(images[key], .52, i + 11, key).resize((cell_w, 72), Image.Resampling.LANCZOS)
        mask = Image.new('L', thumb.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, cell_w, 72), radius=10, fill=225)
        thumb.putalpha(mask)
        layer.alpha_composite(thumb, (cx, y1 + 132))
        d.text((cx + cell_w // 2, y1 + 218), labels[i], font=FONT_TINY, fill=(238, 230, 226, 205), anchor='ma')
    return Image.alpha_composite(frame, layer)


def beat_for(t: float):
    for index, beat in enumerate(BEATS):
        if beat[0] <= t < beat[1]:
            return index, beat
    return len(BEATS) - 1, BEATS[-1]


def main():
    OUT.mkdir(exist_ok=True)
    FRAMES.mkdir(parents=True, exist_ok=True)
    images: dict[str, Image.Image] = {}
    for key, (_, expected) in ASSETS.items():
        path = STOCK / f'{key}.jpg'
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f'{key}: digest mismatch {actual}')
        images[key] = Image.open(path).convert('RGB')

    for n in range(FPS * DURATION):
        t = n / FPS
        index, (start, end, key, copy, kind) = beat_for(t)
        p = clamp01((t - start) / (end - start))
        previous = BEATS[index - 1][2] if index > 0 else None
        frame = crossfade(images, key, previous, p, index + 1)
        frame = gradient(frame)
        brand(frame)

        if kind == 'memories':
            frame = memory_chips(frame, images)
        elif kind == 'proof':
            frame = proof_card(frame, images)

        d = ImageDraw.Draw(frame)
        if copy:
            if kind == 'hook':
                d.rounded_rectangle((30, 698, 190, 730), radius=16, fill=(255, 248, 239, 232))
                d.text((110, 714), 'ПОДАРОК ДЛЯ НЕЁ', font=FONT_TINY, fill=(25, 20, 22, 255), anchor='mm')
            font = FONT_CTA if kind == 'cta' else FONT_HOOK if kind == 'hook' else FONT
            y = 748 if kind == 'hook' else 780 if kind == 'cta' else 786
            shadow_text(d, (30, y), copy, font)
            if kind == 'cta':
                shadow_text(d, (30, y + 95), 'Фото · письма · места · планы\nтолько для вас двоих', FONT_SMALL, fill=(244, 234, 228, 220), spacing=4)
                d.rounded_rectangle((392, 39, 508, 73), radius=17, fill=(255, 112, 104, 225))
                d.text((450, 56), 'GIFT ROOM', font=FONT_TINY, fill=(20, 16, 20, 255), anchor='mm')

        frame.convert('RGB').save(FRAMES / f'frame-{n:04d}.jpg', quality=92, subsampling=0)

    mp4 = OUT / 'gift-room-vnext-portable-preflight.mp4'
    subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-framerate', str(FPS), '-start_number', '0',
        '-i', str(FRAMES / 'frame-%04d.jpg'), '-frames:v', str(FPS * DURATION), '-c:v', 'libx264',
        '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-movflags', '+faststart', str(mp4)
    ], check=True)

    sheet = OUT / 'gift-room-vnext-portable-contact-sheet.jpg'
    subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(mp4),
        '-vf', 'fps=8/15,scale=270:480:flags=lanczos,tile=4x2:padding=8:margin=8:color=0x151116',
        '-frames:v', '1', '-q:v', '2', str(sheet)
    ], check=True)
    print(f'VERIFIED_PREVIEW_V3 sha256={sha256(mp4)} file={mp4}')


if __name__ == '__main__':
    main()
