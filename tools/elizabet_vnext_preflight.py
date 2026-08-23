#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
STOCK = ROOT / 'stock-vnext'
OUT = ROOT / 'vnext-preflight'
FRAMES = OUT / 'frames'
W, H, FPS, DURATION = 540, 960, 30, 15

ASSETS = {
    'gift': (5493219, '055e51ab4970696b3dfa1a41277983eaf24c3e8cb0f9b8aaba5cf4e8f8548136'),
    'phone': (9787927, '8d856002bc1aa9f2bb29144734a32e1da379777395db3ff70a5bcbbe4561cee3'),
    'hands': (6643009, 'f68efec89c7663736d870341782cea7b66b5a3119aeacf15e7f69e51cbadb68f'),
    'home': (35490265, 'dfc778c07cb9ec6381c8684fd5693564eb41e4fbcbceba131b22cd74b516ef68'),
}

BEATS = [
    (0.0, 0.8, 'gift', 'Не ещё одну вещь.', 'gift'),
    (0.8, 1.7, 'gift', 'Подарок, который уже про вас.', 'gift'),
    (1.7, 2.8, 'hands', 'Собери ваши моменты\nв Gift Room.', 'gift'),
    (2.8, 4.5, 'hands', 'Фото · слова · места · планы', 'memories'),
    (4.5, 6.2, 'phone', '', 'proof'),
    (6.2, 8.0, 'phone', 'Одно приватное место\nтолько для вас двоих', 'proof-small'),
    (8.0, 10.0, 'gift', 'Это уже ваше.', 'gift'),
    (10.0, 12.6, 'home', 'Подарок, к которому\nхочется возвращаться.', 'gift'),
    (12.6, 15.0, 'home', 'Собрать Gift Room →', 'cta'),
]

FONT_REG = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT = ImageFont.truetype(FONT_REG, 27)
FONT_SMALL = ImageFont.truetype(FONT_REG, 18)
FONT_TINY = ImageFont.truetype(FONT_BOLD, 13)
FONT_HOOK = ImageFont.truetype(FONT_BOLD, 45)
FONT_CTA = ImageFont.truetype(FONT_BOLD, 39)
FONT_BRAND = ImageFont.truetype(FONT_BOLD, 14)
FONT_PROOF = ImageFont.truetype(FONT_BOLD, 31)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def cover(image: Image.Image, t: float, seed: float) -> Image.Image:
    # Restrained Ken Burns; movement supports the photograph instead of becoming the subject.
    scale = 1.055 + 0.035 * t
    ratio = max(W / image.width, H / image.height) * scale
    rw, rh = int(image.width * ratio), int(image.height * ratio)
    resized = image.resize((rw, rh), Image.Resampling.LANCZOS)
    max_x, max_y = max(0, rw - W), max(0, rh - H)
    x = int(max_x * (0.48 + 0.025 * math.sin(seed + t * 1.1)))
    y = int(max_y * (0.47 + 0.018 * math.cos(seed * .7 + t * .9)))
    x, y = max(0, min(max_x, x)), max(0, min(max_y, y))
    frame = resized.crop((x, y, x + W, y + H))
    frame = ImageEnhance.Color(frame).enhance(.92)
    frame = ImageEnhance.Contrast(frame).enhance(1.035)
    return frame


def rounded_overlay(base: Image.Image, box: tuple[int, int, int, int], radius: int, fill: tuple[int, int, int, int], outline=None):
    layer = Image.new('RGBA', base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=1 if outline else 0)
    return Image.alpha_composite(base.convert('RGBA'), layer)


def text(draw: ImageDraw.ImageDraw, xy, value: str, font, fill=(255,248,239), spacing=6, anchor=None):
    x, y = xy
    draw.multiline_text((x + 2, y + 3), value, font=font, fill=(0,0,0,150), spacing=spacing, anchor=anchor)
    draw.multiline_text((x, y), value, font=font, fill=fill, spacing=spacing, anchor=anchor)


def gradient(frame: Image.Image) -> Image.Image:
    overlay = Image.new('RGBA', (W, H), (0,0,0,0))
    px = overlay.load()
    for y in range(H):
        u = y / (H - 1)
        alpha = int(8 + max(0.0, (u - .47) / .53) ** 1.65 * 205)
        edge = int(max(0.0, abs(u - .42) - .25) * 30)
        for x in range(W):
            px[x, y] = (13, 8, 12, min(225, alpha + edge))
    return Image.alpha_composite(frame.convert('RGBA'), overlay)


def brand(frame: Image.Image):
    draw = ImageDraw.Draw(frame)
    draw.ellipse((34, 41, 43, 50), fill=(255,112,104,255))
    draw.text((52, 37), 'ELIZABETH', font=FONT_BRAND, fill=(255,248,239,245))


def proof_card(frame: Image.Image, images: dict[str, Image.Image], small=False):
    x1, x2 = (62, W - 62) if not small else (72, W - 72)
    y1, y2 = (616, 846) if not small else (640, 844)
    card = Image.new('RGBA', frame.size, (0,0,0,0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((x1,y1,x2,y2), radius=28, fill=(20,17,22,218), outline=(255,255,255,58), width=1)
    d.text((x1+24,y1+22),'ВАША ИСТОРИЯ',font=FONT_TINY,fill=(235,226,219,175))
    d.text((x1+24,y1+46),'Gift Room',font=FONT_PROOF,fill=(255,248,239,255))
    labels = [('Фото','gift'),('Письмо','hands'),('Место','phone'),('План','home')]
    cell_w = int((x2-x1-54)/4)
    for i,(label,key) in enumerate(labels):
        cx = x1+20+i*(cell_w+4)
        thumb = cover(images[key], .35, i) .resize((cell_w,62), Image.Resampling.LANCZOS)
        mask = Image.new('L', thumb.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0,0,thumb.width,thumb.height),radius=10,fill=220)
        thumb.putalpha(mask)
        card.alpha_composite(thumb,(cx,y1+101))
        d.text((cx+cell_w//2,y1+169),label,font=FONT_TINY,fill=(238,230,226,205),anchor='ma')
    return Image.alpha_composite(frame, card)


def memory_strip(frame: Image.Image, images: dict[str, Image.Image]):
    card = Image.new('RGBA', frame.size, (0,0,0,0))
    d = ImageDraw.Draw(card)
    labels = [('Фото','gift'),('Письмо','hands'),('Место','phone'),('План','home')]
    cell_w = 101
    start = 44
    for i,(label,key) in enumerate(labels):
        x = start + i*112
        thumb = cover(images[key], .25, i+3).resize((cell_w,116), Image.Resampling.LANCZOS)
        mask = Image.new('L',thumb.size,0)
        ImageDraw.Draw(mask).rounded_rectangle((0,0,cell_w,116),radius=14,fill=245)
        thumb.putalpha(mask)
        card.alpha_composite(thumb,(x,720))
        d.text((x+cell_w//2,843),label,font=FONT_TINY,fill=(255,248,239,240),anchor='ma')
    return Image.alpha_composite(frame,card)


def beat_for(t: float):
    for beat in BEATS:
        if beat[0] <= t < beat[1]:
            return beat
    return BEATS[-1]


def main():
    OUT.mkdir(exist_ok=True)
    FRAMES.mkdir(parents=True, exist_ok=True)
    images = {}
    for key,(asset_id,expected) in ASSETS.items():
        path = STOCK / f'{key}.jpg'
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f'{key}: digest mismatch {actual}')
        images[key] = Image.open(path).convert('RGB')

    for n in range(FPS*DURATION):
        t = n/FPS
        start,end,key,copy,kind = beat_for(t)
        p = max(0,min(1,(t-start)/(end-start)))
        frame = cover(images[key], p, BEATS.index((start,end,key,copy,kind))+1)
        frame = gradient(frame)
        brand(frame)
        if kind == 'memories':
            frame = memory_strip(frame,images)
        if kind.startswith('proof'):
            frame = proof_card(frame,images,small=kind=='proof-small')
        if kind == 'cta':
            frame = rounded_overlay(frame,(377,43,496,77),18,(255,112,104,225))
            ImageDraw.Draw(frame).text((436,60),'GIFT ROOM',font=FONT_TINY,fill=(20,16,20,255),anchor='mm')
        if copy and kind != 'memories':
            d = ImageDraw.Draw(frame)
            font = FONT_CTA if kind=='cta' else FONT_HOOK if t < 2.8 else FONT
            y = 788 if kind=='cta' else 715 if t < 2.8 else 758
            if t < .8:
                frame = rounded_overlay(frame,(34,y-45,175,y-14),16,(255,248,239,232))
                d = ImageDraw.Draw(frame)
                d.text((104,y-29),'Подарок для неё',font=FONT_TINY,fill=(25,20,22,255),anchor='mm')
            text(d,(34,y),copy,font)
            if 1.7 <= t < 2.8:
                text(d,(34,y+112),'Не универсальная вещь.\nВаши реальные моменты — в одном подарке.',FONT_SMALL,fill=(244,234,228,225),spacing=4)
            if kind=='cta':
                text(d,(34,y+104),'Фото · письма · места · планы\nтолько для вас двоих',FONT_SMALL,fill=(244,234,228,220),spacing=4)
        frame.convert('RGB').save(FRAMES/f'frame-{n:04d}.jpg',quality=91,subsampling=0)

    mp4 = OUT/'gift-room-vnext-portable-preflight.mp4'
    subprocess.run([
        'ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-start_number','0','-i',str(FRAMES/'frame-%04d.jpg'),
        '-frames:v',str(FPS*DURATION),'-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-r',str(FPS),'-movflags','+faststart',str(mp4)
    ],check=True)
    # Whole-timeline sheet: 8 exact frames, no opening-only cherry-picking.
    sheet = OUT/'gift-room-vnext-portable-contact-sheet.jpg'
    subprocess.run([
        'ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(mp4),'-vf','fps=8/15,scale=270:480:flags=lanczos,tile=4x2:padding=8:margin=8:color=0x151116','-frames:v','1','-q:v','2',str(sheet)
    ],check=True)
    print(f'VERIFIED_PREVIEW sha256={sha256(mp4)} file={mp4}')

if __name__ == '__main__':
    main()
