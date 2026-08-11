"""
Generates the character "wardrobe" ONCE — a small fixed set of pose/outfit
variants for the consistent host character, using Pollinations.ai
(free, no API key, no GPU required).

Run this once (or whenever you want to add a new outfit):
    python scripts/generate_wardrobe.py

Images are saved to assets/character/<id>.png and reused by every future
post/reel — this is what keeps the character looking "the same" across
content, same as the reference pages.
"""

import os
import time
import urllib.parse
import requests

import config


def build_prompt(variant_prompt: str) -> str:
    return f"{config.CHARACTER_BASE}, {variant_prompt}"


def generate_image(prompt: str, out_path: str, seed: int, width=1024, height=1024, retries=3):
    encoded = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={width}&height={height}&seed={seed}&nologo=true&model=flux"
    )
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(resp.content)
            return True
        except Exception as e:
            print(f"  attempt {attempt} failed: {e}")
            time.sleep(3)
    return False


def main():
    os.makedirs(config.CHARACTER_DIR, exist_ok=True)
    print(f"Generating {len(config.WARDROBE)} wardrobe variants...")
    for i, variant in enumerate(config.WARDROBE):
        out_path = os.path.join(config.CHARACTER_DIR, f"{variant['id']}.png")
        if os.path.exists(out_path):
            print(f"[{i+1}/{len(config.WARDROBE)}] {variant['id']} already exists, skipping")
            continue
        prompt = build_prompt(variant["prompt"])
        print(f"[{i+1}/{len(config.WARDROBE)}] generating {variant['id']}...")
        ok = generate_image(prompt, out_path, seed=config.CHARACTER_SEED + i)
        print("  done" if ok else "  FAILED after retries")
        time.sleep(2)  # be polite to the free API
    print("Wardrobe generation complete. Review assets/character/ and re-run for any that failed.")


if __name__ == "__main__":
    main()
