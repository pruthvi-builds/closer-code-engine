"""
Generates a free, copyright-safe ambient background bed for reels.

Why this exists instead of pulling from Instagram's trending sounds:
Instagram's trending-audio catalog is only accessible from inside the
Instagram app itself. There is no official Graph API endpoint to browse or
attach a trending sound programmatically — the only way to do that in code
is via unofficial, reverse-engineered private-API tools that impersonate
the mobile app, which violate Instagram's Terms of Service and risk the
account getting flagged or banned. This project doesn't do that.

Instead, every reel gets a soft, procedurally generated ambient pad —
synthesized from sine waves in Python, not downloaded or sampled from
anywhere, so there is zero copyright risk and zero dependency on any
external service. Fully free, fully deterministic, fully local.

If you'd rather add a trending sound for extra reach, the video still
uploads fine with this bed under it — you can always open the specific
reel in the Instagram app afterward and layer a trending audio on top
manually. That one step is the only thing that can't be automated.
"""

import math
import os
import struct
import wave
import random

import config

SAMPLE_RATE = 44100

# A few calm chord voicings (Hz) to rotate between so not every reel has
# the identical bed — still fully procedural, no external audio files.
CHORDS_HZ = [
    [130.81, 164.81, 196.00],   # C3 major-ish pad
    [146.83, 185.00, 220.00],   # D3
    [110.00, 138.59, 164.81],   # A2
    [174.61, 220.00, 261.63],   # F3
]


def _sine(freq, t, phase=0.0):
    return math.sin(2 * math.pi * freq * t + phase)


def generate_ambient_bed(duration: float, out_path: str, seed: int = None):
    """Writes a WAV file of `duration` seconds: a soft layered pad with a
    slow amplitude swell, plus a very light rhythmic pulse so it doesn't
    feel like a dead tone. No external assets, no network calls."""
    rng = random.Random(seed)
    chord = rng.choice(CHORDS_HZ)
    n_samples = int(SAMPLE_RATE * duration)

    frames = bytearray()
    for i in range(n_samples):
        t = i / SAMPLE_RATE
        # slow global swell so the bed breathes instead of sitting static
        swell = 0.5 + 0.5 * math.sin(2 * math.pi * 0.05 * t)
        sample = 0.0
        for freq in chord:
            sample += _sine(freq, t) * 0.18
        # gentle rhythmic pulse, subtle, at ~1 beat/sec
        pulse = 0.05 * max(0.0, math.sin(2 * math.pi * 1.0 * t)) ** 3
        sample = (sample + pulse) * swell * 0.35  # overall headroom, quiet bed
        sample = max(-1.0, min(1.0, sample))
        val = int(sample * 32767)
        frames += struct.pack("<h", val)

    with wave.open(out_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(bytes(frames))
    return out_path


if __name__ == "__main__":
    os.makedirs(config.RENDER_DIR, exist_ok=True)
    generate_ambient_bed(6.0, os.path.join(config.RENDER_DIR, "sample_ambient.wav"), seed=1)
    print("Sample ambient bed written to assets/renders/sample_ambient.wav")
