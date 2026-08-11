"""
Composes still assets — PURE QUOTE TEMPLATE.

Plain white background, centered serif quote, italics for emphasis. No
kicker label, no handle watermark, no CTA button/text — nothing but the
words. Font size scales up for short quotes so they read as prominent,
poster-like statements rather than shrinking to fit a fixed size.

Pure PIL, runs anywhere, no GPU. Uses assets/fonts/Serif-Regular.ttf and
assets/fonts/Serif-Italic.ttf (Lora, free/open license). Falls back to
DejaVu Serif if missing.
"""

import os
from PIL import Image, ImageDraw, ImageFont

import config

CANVAS_W, CANVAS_H = 1080, 1350  # IG portrait 4:5
FONT_DIR = os.path.join(config.ROOT, "assets", "fonts")

BG = (255, 255, 255)   # pure white
INK = (17, 17, 17)     # near-black, prominent contrast


def _font(size, italic=False):
    path = os.path.join(FONT_DIR, "Serif-Italic.ttf" if italic else "Serif-Regular.ttf")
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    fallback = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf" if italic \
        else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
    try:
        return ImageFont.truetype(fallback, size)
    except Exception:
        return ImageFont.load_default()


def _italic_flags(words, phrases):
    """Given the tokenized headline `words` and a set of (possibly
    multi-word) phrases to emphasize, return a list of booleans aligned to
    `words` marking which tokens fall inside any matched phrase."""
    clean = [w.strip(".,!?”“\"'").lower() for w in words]
    flags = [False] * len(words)
    for phrase in phrases:
        p_words = phrase.lower().split()
        n = len(p_words)
        if n == 0:
            continue
        for i in range(len(clean) - n + 1):
            if clean[i:i + n] == p_words:
                for j in range(i, i + n):
                    flags[j] = True
    return flags


def _wrap_runs(draw, text, size, max_width, italic_words):
    """Word-wrap while tracking which words should render in italics.
    italic_words: set of lowercase words/phrases (single or multi-word) to italicize."""
    reg = _font(size)
    ita = _font(size, italic=True)
    words = text.split()
    flags = _italic_flags(words, italic_words) if italic_words else [False] * len(words)
    lines, cur, cur_w = [], [], 0
    space_w = draw.textlength(" ", font=reg)
    for w, is_ital in zip(words, flags):
        f = ita if is_ital else reg
        ww = draw.textlength(w, font=f)
        add = ww if not cur else space_w + ww
        if cur_w + add <= max_width or not cur:
            cur.append((w, f, is_ital))
            cur_w += add
        else:
            lines.append(cur)
            cur = [(w, f, is_ital)]
            cur_w = ww
    if cur:
        lines.append(cur)
    return lines, space_w


def _auto_size(word_count: int) -> int:
    """Bigger, more prominent type for short quotes; scales down for longer
    ones so they still fit comfortably within the margins."""
    if word_count <= 6:
        return 92
    if word_count <= 10:
        return 78
    if word_count <= 16:
        return 64
    if word_count <= 22:
        return 54
    return 46


def render_quote_post(quote: str, out_path: str, emphasis: list = None, kicker: str = None, post_index: int = 0,
                       canvas_w: int = None, canvas_h: int = None, bg: tuple = None, ink: tuple = None):
    """quote: the full line/lines of copy, e.g. one crisp aphorism.
    emphasis: list of words/phrases to italicize (case-insensitive).
    bg/ink: override the default white-bg/black-text palette (used by
    compose_reel.py to render an inverted black-bg/white-text version for
    reels, so posts and reels are visually distinct at a glance).
    kicker/post_index: accepted for backward compatibility, unused (no
    labels or watermarks in this template by design).
    """
    w_, h_ = canvas_w or CANVAS_W, canvas_h or CANVAS_H
    bg_color = bg or BG
    ink_color = ink or INK
    emphasis_set = {w.lower() for w in (emphasis or [])}
    canvas = Image.new("RGB", (w_, h_), bg_color)
    draw = ImageDraw.Draw(canvas)

    size = _auto_size(len(quote.split()))
    max_width = w_ - 180
    lines, space_w = _wrap_runs(draw, quote, size, max_width, emphasis_set)
    line_h = int(size * 1.42)
    total_h = len(lines) * line_h
    y = (h_ - total_h) // 2

    for line in lines:
        line_w = sum(draw.textlength(w, font=f) for w, f, _ in line) + space_w * (len(line) - 1)
        x = (w_ - line_w) // 2
        for w, f, _ in line:
            draw.text((x, y), w, font=f, fill=ink_color)
            x += draw.textlength(w, font=f) + space_w
        y += line_h

    canvas.save(out_path)
    return out_path


# Backward-compatible name used by main.py
def render_headline_post(headline: str, out_path: str, trigger_word: str = None, post_index: int = 0):
    emphasis = [trigger_word] if trigger_word else None
    return render_quote_post(headline, out_path, emphasis=emphasis)


def render_carousel(title: str, slides: list, out_dir: str, post_index: int = 0, emphasis: list = None):
    """Slide 0 = title card. Slides 1-N = one point per slide. Same plain
    white background, no labels, no watermark — a small muted page number
    is the only element besides the text, so slides stay orientable."""
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    page_color = (160, 160, 160)

    cover = Image.new("RGB", (CANVAS_W, CANVAS_H), BG)
    draw = ImageDraw.Draw(cover)
    size = _auto_size(len(title.split()))
    lines, space_w = _wrap_runs(draw, title, min(size, 64), CANVAS_W - 180, {w.lower() for w in (emphasis or [])})
    line_h = int(min(size, 64) * 1.35)
    total_h = len(lines) * line_h
    y = (CANVAS_H - total_h) // 2
    for line in lines:
        line_w = sum(draw.textlength(w, font=f) for w, f, _ in line) + space_w * (len(line) - 1)
        x = (CANVAS_W - line_w) // 2
        for w, f, _ in line:
            draw.text((x, y), w, font=f, fill=INK)
            x += draw.textlength(w, font=f) + space_w
        y += line_h
    cover_path = os.path.join(out_dir, "slide_00_cover.png")
    cover.save(cover_path)
    paths.append(cover_path)

    total_slides = len(slides)
    for i, point in enumerate(slides, start=1):
        slide = Image.new("RGB", (CANVAS_W, CANVAS_H), BG)
        draw = ImageDraw.Draw(slide)
        pf = _font(26)
        page_label = f"{i} / {total_slides}"
        pw = draw.textlength(page_label, font=pf)
        draw.text(((CANVAS_W - pw) // 2, 70), page_label, font=pf, fill=page_color)

        size = _auto_size(len(point.split()))
        lines, space_w = _wrap_runs(draw, point, min(size, 58), CANVAS_W - 180, set())
        line_h = int(min(size, 58) * 1.4)
        total_h = len(lines) * line_h
        y = (CANVAS_H - total_h) // 2
        for line in lines:
            line_w = sum(draw.textlength(w, font=f) for w, f, _ in line) + space_w * (len(line) - 1)
            x = (CANVAS_W - line_w) // 2
            for w, f, _ in line:
                draw.text((x, y), w, font=f, fill=INK)
                x += draw.textlength(w, font=f) + space_w
            y += line_h
        slide_path = os.path.join(out_dir, f"slide_{i:02d}.png")
        slide.save(slide_path)
        paths.append(slide_path)

    return paths


if __name__ == "__main__":
    os.makedirs(config.RENDER_DIR, exist_ok=True)
    render_quote_post(
        "Every objection is just fear wearing a work uniform.",
        os.path.join(config.RENDER_DIR, "sample_quote_v4.png"),
        emphasis=["fear"],
    )
    render_quote_post(
        "The close begins the moment you stop needing it.",
        os.path.join(config.RENDER_DIR, "sample_quote_v4b.png"),
        emphasis=["stop needing"],
    )
    render_carousel(
        "Seven objections, and what they actually mean",
        [
            "“Send me an email” means you haven't earned the next ten seconds yet.",
            "“I need to think about it” means you never named the real concern.",
            "“We already have someone” means you haven't asked what they'd change.",
        ],
        os.path.join(config.RENDER_DIR, "sample_carousel_v4"),
    )
    print("Sample renders written to assets/renders/")
