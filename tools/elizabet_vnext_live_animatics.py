#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'live-assets'
OUT = ROOT / 'live-animatics'
WORK = OUT / '.work'
W, H, FPS = 360, 640, 30
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

EXPECTED = {
    'gift': ('wrapped-gift-live.mp4', '238810b731cfe0ce3fd149ef55c12d1c3d2a53e5b25182af71124edaac70f35e'),
    'polaroid': ('couple-polaroid-live.mp4', '8363999e93aa3bdddb21fe71a402bedbae7860822a98e82e5c99ec58e4efa700'),
    'memory': ('memory-book-live.mp4', '09e99a1c21f48d4f16347d2e949e7e5ff150c4e8fbd8ca39d6a72db23371c603'),
    'letter': ('handwritten-letter-live.mp4', 'ea2b64c7ec20f84258080a2c1ba56996e99495d31933303a985363512fd6c489'),
    'walk': ('city-couple-walk-mixed-live.mp4', 'a515bedc4eea1fb5822b2c1f75e73a67d3dd315177f70eb5aecc9ab6bd3a5be0'),
    'reaction': ('couple-gift-reaction-live.mp4', 'a74e09f120392bae9864273aa0cdb6e76a5ba0af58d902309e8588edc1cef056'),
}

CONCEPTS = {
    'gift-memory-arc': {
        'hypothesis': 'tactile gift hook -> shared-memory specificity -> compact product bridge -> real reaction payoff',
        'segments': [
            ('gift', 1.0, 1.2),
            ('polaroid', 0.5, 1.5),
            ('memory', 1.0, 1.5),
            ('letter', 2.0, 1.5),
            ('walk', 0.5, 1.6),
            ('polaroid', 4.0, 1.6),
            ('proof', 0.0, 1.6),
            ('reaction', 1.8, 4.5),
        ],
        'captions': [
            (0.00, 1.20, 'Не ещё одна вещь.', 'main'),
            (1.20, 2.70, 'То, что уже ваше.', 'main'),
            (2.70, 4.20, 'Ваши фото.', 'main'),
            (4.20, 5.70, 'Ваши слова.', 'main'),
            (5.70, 7.30, 'Ваше место.', 'main'),
            (7.30, 8.90, 'Собери моменты вместе.', 'main'),
            (10.50, 13.20, 'Подарок, к которому возвращаются.', 'main'),
            (13.20, 15.00, 'Собрать Gift Room →', 'cta'),
            (0.65, 2.70, 'Gift Room · из ваших моментов', 'brand'),
        ],
    },
    'problem-solution': {
        'hypothesis': 'relatable gift problem -> reject generic object framing -> personal ingredients -> solution -> reaction',
        'segments': [
            ('gift', 1.0, 1.4),
            ('walk', 0.7, 1.4),
            ('memory', 1.0, 1.5),
            ('letter', 2.0, 1.5),
            ('polaroid', 0.5, 1.4),
            ('proof', 0.0, 2.0),
            ('reaction', 1.8, 5.8),
        ],
        'captions': [
            (0.00, 1.40, 'Что подарить человеку,\nу которого всё есть?', 'main'),
            (1.40, 2.80, 'Не ещё одну случайную вещь.', 'main'),
            (2.80, 4.30, 'Возьми ваши фото.', 'main'),
            (4.30, 5.80, 'Ваши слова.', 'main'),
            (5.80, 7.20, 'То, что помните только вы.', 'main'),
            (9.20, 12.60, 'И подари это как одно целое.', 'main'),
            (12.60, 15.00, 'Собрать Gift Room →', 'cta'),
            (0.70, 2.80, 'Gift Room · личный подарок', 'brand'),
        ],
    },
    'memory-match-cut': {
        'hypothesis': 'fast tactile match-cut burst -> concise product bridge -> gift handoff -> sustained emotional reaction',
        'segments': [
            ('gift', 1.6, 0.8),
            ('polaroid', 1.0, 0.8),
            ('letter', 2.2, 0.8),
            ('walk', 1.0, 0.8),
            ('memory', 2.0, 1.2),
            ('polaroid', 4.2, 1.2),
            ('proof', 0.0, 1.6),
            ('gift', 2.3, 2.0),
            ('reaction', 1.8, 5.8),
        ],
        'captions': [
            (0.00, 0.80, 'Подарок.', 'main'),
            (0.80, 1.60, 'Фото.', 'main'),
            (1.60, 2.40, 'Слова.', 'main'),
            (2.40, 3.20, 'Место.', 'main'),
            (3.20, 5.60, 'Ваши маленькие вещи,\nкоторые значат всё.', 'main'),
            (7.20, 9.20, 'Не покупай историю.\nСобери вашу.', 'main'),
            (9.20, 12.50, 'Gift Room', 'main'),
            (12.50, 15.00, 'Собрать →', 'cta'),
            (0.55, 3.20, 'Gift Room', 'brand'),
        ],
    },
}


def run(args: list[str]) -> None:
    subprocess.run(args, check=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def ass_time(value: float) -> str:
    centis = int(round(value * 100))
    h, rest = divmod(centis, 360000)
    m, rest = divmod(rest, 6000)
    s, cs = divmod(rest, 100)
    return f'{h}:{m:02d}:{s:02d}.{cs:02d}'


def ass_escape(text: str) -> str:
    return text.replace('\\', r'\\').replace('{', r'\{').replace('}', r'\}').replace('\n', r'\N')


def write_ass(path: Path, captions: list[tuple[float, float, str, str]]) -> None:
    header = f'''[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Main,DejaVu Sans,30,&H00F7F4F0,&H000000FF,&H70000000,&H50000000,-1,0,0,0,100,100,0,0,1,2,0,8,24,24,64,1\nStyle: Brand,DejaVu Sans,15,&H00F7F4F0,&H000000FF,&H70000000,&H50000000,-1,0,0,0,100,100,0,0,1,1,0,8,24,24,118,1\nStyle: CTA,DejaVu Sans,30,&H00FFFFFF,&H000000FF,&H70000000,&H70000000,-1,0,0,0,100,100,0,0,3,1,0,2,30,30,98,1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n'''
    lines = []
    for start, end, text, kind in captions:
        style = {'main': 'Main', 'brand': 'Brand', 'cta': 'CTA'}[kind]
        lines.append(f'Dialogue: 0,{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{ass_escape(text)}')
    path.write_text(header + '\n'.join(lines) + '\n', encoding='utf-8')


def make_proof() -> Path:
    proof_png = WORK / 'proof.png'
    proof_mp4 = WORK / 'proof.mp4'
    img = Image.new('RGB', (W, H), '#1b1118')
    draw = ImageDraw.Draw(img)
    title = ImageFont.truetype(FONT_BOLD, 42)
    subtitle = ImageFont.truetype(FONT, 18)
    chip = ImageFont.truetype(FONT_BOLD, 18)
    tiny = ImageFont.truetype(FONT, 13)
    draw.text((34, 92), 'Gift Room', font=title, fill='#fff7ef')
    draw.text((35, 146), 'один подарок из ваших моментов', font=subtitle, fill='#e9d8d1')
    labels = [('ФОТО', '#ff897d'), ('СЛОВА', '#f1bd75'), ('МЕСТА', '#8fc7b9'), ('ПЛАНЫ', '#b9a4e8')]
    y = 224
    for label, color in labels:
        draw.rounded_rectangle((36, y, 324, y + 58), radius=16, fill='#2b2028', outline=color, width=2)
        draw.text((56, y + 17), label, font=chip, fill='#fff7ef')
        y += 72
    draw.text((36, 535), 'личное пространство · без публичной ленты', font=tiny, fill='#bcaeb4')
    proof_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(proof_png, quality=95)
    run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-loop', '1', '-i', str(proof_png),
        '-t', '2.2', '-vf', f'fps={FPS},format=yuv420p', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', str(proof_mp4),
    ])
    return proof_mp4


def normalize_clip(key: str, start: float, duration: float, target: Path) -> None:
    source = ASSETS / EXPECTED[key][0]
    run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', f'{start:.3f}', '-i', str(source), '-t', f'{duration:.3f}',
        '-an', '-vf', f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1,format=yuv420p',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-movflags', '+faststart', str(target),
    ])


def render_concept(name: str, spec: dict, proof: Path) -> dict:
    concept_dir = WORK / name
    concept_dir.mkdir(parents=True, exist_ok=True)
    concat_file = concept_dir / 'concat.txt'
    timeline = []
    cursor = 0.0
    pieces = []
    for i, (key, start, duration) in enumerate(spec['segments']):
        target = concept_dir / f'{i:02d}-{key}.mp4'
        if key == 'proof':
            run([
                'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(proof), '-t', f'{duration:.3f}',
                '-an', '-vf', f'fps={FPS},format=yuv420p', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', str(target),
            ])
        else:
            normalize_clip(key, start, duration, target)
        pieces.append(target)
        timeline.append({
            'shot': i + 1,
            'asset': key,
            'source_in_seconds': start,
            'source_out_seconds': start + duration,
            'timeline_in_seconds': cursor,
            'timeline_out_seconds': cursor + duration,
        })
        cursor += duration
    if abs(cursor - 15.0) > 0.02:
        raise RuntimeError(f'{name}: timeline duration {cursor} != 15')
    concat_file.write_text(''.join(f"file '{p.as_posix()}'\n" for p in pieces), encoding='utf-8')
    clean = concept_dir / 'clean.mp4'
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat_file), '-c', 'copy', str(clean)])
    ass = concept_dir / 'captions.ass'
    write_ass(ass, spec['captions'])
    final = OUT / f'{name}.mp4'
    run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(clean),
        '-vf', f"subtitles={ass.as_posix()}:fontsdir=/usr/share/fonts/truetype/dejavu",
        '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-movflags', '+faststart', str(final),
    ])
    sheet = OUT / f'{name}-contact-sheet.jpg'
    run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(final),
        '-vf', 'fps=8/15,scale=180:320:flags=lanczos,tile=4x2:padding=6:margin=6:color=0x151116',
        '-frames:v', '1', '-q:v', '2', str(sheet),
    ])
    return {
        'id': name,
        'hypothesis': spec['hypothesis'],
        'video': final.relative_to(ROOT).as_posix(),
        'sha256': sha256(final),
        'contact_sheet': sheet.relative_to(ROOT).as_posix(),
        'duration_seconds': 15.0,
        'resolution': [W, H],
        'fps': FPS,
        'audio': 'intentionally_absent_visual_semantic_preflight',
        'timeline': timeline,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    sources = {}
    for key, (filename, expected) in EXPECTED.items():
        path = ASSETS / filename
        if not path.is_file():
            raise SystemExit(f'missing source: {path}')
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f'{key}: SHA mismatch expected={expected} actual={actual}')
        sources[key] = {'file': filename, 'sha256': actual}
    proof = make_proof()
    concepts = [render_concept(name, spec, proof) for name, spec in CONCEPTS.items()]
    manifest = {
        'schema_version': '2026-08-23.elizabet-vnext-live-animatics.v1',
        'product_id': 'elizabet',
        'offer': 'Gift Room',
        'state': 'SEMANTIC_VISUAL_PREFLIGHT_ONLY',
        'render_engine': 'deterministic_ffmpeg_clip_edit_plus_ass_typography',
        'source_assets': sources,
        'concepts': concepts,
        'required_review': [
            'watch_all_three_full_duration_at_normal_speed',
            'compare_hook_semantic_clarity',
            'compare_tiktok_native_edit_feel',
            'compare_human_warmth_and_specificity',
            'compare_product_cue_timing_without_ui_dominance',
            'compare_payoff_and_cta_liveliness',
        ],
        'audio_finalization_required_after_visual_winner': True,
        'exact_1080x1920_render_authority': False,
        'publication_authority': False,
        'paid_social_authority': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'ok': True, 'concepts': [(c['id'], c['sha256']) for c in concepts]}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
