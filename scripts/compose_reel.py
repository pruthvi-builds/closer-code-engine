"""
Builds a vertical reel (1080x1920, mp4) — FULLY STATIC QUOTE CARD, INVERTED.

Same serif template as compose_post.py but with the palette flipped: black
background, white text. This is now the ONLY content format the engine
produces (posts/carousels were dropped) — this single asset is what gets
published as a Reel, which also shows on the profile grid, covering both
"reel" and "post" placement.

Held with ZERO motion for the entire duration. No zoom, no reveal, no
fade — the text does not move at all.

A procedurally generated ambient audio bed (scripts/audio.py) is muxed in
automatically so every upload has sound without any manual step or any
dependency on Instagram's own trending-audio catalog (which isn't
reachable via the official API — see audio.py's docstring for why).

CPU-only via moviepy/ffmpeg — no GPU needed.
"""

import os
import shutil
import subprocess
from moviepy import ImageClip

import config
import compose_post
import audio

W, H = 1080, 1920
DURATION = 6

REEL_BG = (0, 0, 0)
REEL_INK = (255, 255, 255)


def _mux_audio(video_path: str, wav_path: str, out_path: str):
    """Combine the silent video with the generated ambient bed using
    ffmpeg directly (more reliable than moviepy's audio pipeline for a
    simple single-track mux). Re-encodes audio to AAC, which Instagram's
    Graph API expects."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", wav_path,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        out_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def render_reel(headline: str, out_path: str, trigger_word: str = None, post_index: int = 0, duration=DURATION, kicker: str = None):
    # Render the same quote template used for stills, at reel dimensions,
    # with the palette inverted (black bg / white text), then hold it
    # perfectly still for the full clip.
    tmp_frame = out_path.rsplit(".", 1)[0] + "_frame.png"
    tmp_silent = out_path.rsplit(".", 1)[0] + "_silent.mp4"
    tmp_wav = out_path.rsplit(".", 1)[0] + "_bed.wav"
    emphasis = [trigger_word] if trigger_word else None

    compose_post.render_quote_post(headline, tmp_frame, emphasis=emphasis, canvas_w=W, canvas_h=H,
                                    bg=REEL_BG, ink=REEL_INK)

    clip = ImageClip(tmp_frame).with_duration(duration)
    clip.write_videofile(tmp_silent, fps=30, codec="libx264", audio=False, logger=None)

    if config.AUDIO_ENABLED:
        audio.generate_ambient_bed(duration + config.AUDIO_DURATION_PAD, tmp_wav, seed=hash(headline) % 10_000)
        _mux_audio(tmp_silent, tmp_wav, out_path)
    else:
        shutil.copyfile(tmp_silent, out_path)

    for tmp in (tmp_frame, tmp_silent, tmp_wav):
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass  # some sandboxes disallow deleting freshly-written files; harmless leftover

    return out_path


if __name__ == "__main__":
    os.makedirs(config.RENDER_DIR, exist_ok=True)
    render_reel(
        "Every objection is just fear wearing a work uniform.",
        os.path.join(config.RENDER_DIR, "sample_reel_v5.mp4"),
        trigger_word="fear",
    )
    print("Sample reel written to assets/renders/sample_reel_v5.mp4")
