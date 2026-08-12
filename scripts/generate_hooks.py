"""
Periodic content generator - keeps the reel_hooks pool growing so the
account never has to repeat itself.

Runs on its own schedule (see .github/workflows/generate_hooks_weekly.yml),
separate from the posting workflow. Each run:
  1. Reads the existing reel_hooks pool (used both as style reference and
     as a duplicate-avoidance list).
  2. Calls a free-tier LLM (Groq, OpenAI-compatible endpoint) asking for a
     batch of new punchy, aphoristic cold-calling/sales-closing one-liners
     in the exact same voice as the existing bank, each with a caption
     that always ends in a link-in-bio CTA pointing at the paid playbook
     (the actual monetization intent of the whole page).
  3. Filters out anything too similar to what's already in the bank
     (difflib ratio), assigns clean ids, and appends the survivors to
     content_data/hooks_bank.json.

No web scraping of Instagram is involved anywhere in this pipeline --
there's no supported/safe way to programmatically browse "what's viral in
this niche" on IG, and scraping the app/site would violate its ToS and
risk the account getting flagged. This instead leans on an LLM that
already has broad exposure to what makes cold-calling/sales content work,
steered hard by the existing bank as few-shot examples of proven voice.
"""

import difflib
import json
import os
import re
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

BATCH_SIZE = int(os.environ.get("HOOK_BATCH_SIZE", "15"))
SIMILARITY_THRESHOLD = 0.72  # above this ratio vs an existing quote = treated as a dupe

PRODUCT_CONTEXT = (
    "The page sells a $2 digital PDF playbook called 'The Closer Code' "
    "(cold call scripts, a 5-step call framework, word-for-word objection "
    "responses to the 15 most common objections, voicemail scripts, and a "
    "follow-up cadence). The checkout links live in the Instagram bio."
)


def _load_bank():
    with open(config.HOOKS_JSON, "r") as f:
        return json.load(f)


def _save_bank(bank):
    with open(config.HOOKS_JSON, "w") as f:
        json.dump(bank, f, indent=2)


def _slug(text, max_len=28):
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return f"reel_{slug[:max_len]}" or "reel_hook"


def _is_dupe(candidate_quote, existing_quotes):
    for q in existing_quotes:
        if difflib.SequenceMatcher(None, candidate_quote.lower(), q.lower()).ratio() > SIMILARITY_THRESHOLD:
            return True
    return False


def _build_prompt(existing_hooks):
    examples = "\n".join(f'- "{h["quote"]}"' for h in existing_hooks[:12])
    system = (
        "You write short, punchy, aphoristic hooks for a cold-calling/sales-closing "
        "Instagram page called 'The Closer Code'. Each hook is a single sentence (max "
        "~16 words) displayed as bold white kinetic-typography text on a black "
        "background in a Reel -- it has to land instantly, feel quotable, and make "
        "someone in sales/SDR/closer roles stop scrolling. Tone: confident, a little "
        "blunt, no fluff, no emojis, no hashtags in the quote itself. Style is "
        "aphorism/contrarian-truth, never generic motivational-poster language."
    )
    user = (
        f"Here are examples of hooks already used (do NOT repeat these or anything "
        f"too close to them in phrasing or idea):\n{examples}\n\n"
        f"{PRODUCT_CONTEXT}\n\n"
        f"Write {BATCH_SIZE} brand-new hooks in the same voice, each covering a "
        f"different angle (rejection, confidence, objections, follow-up, discipline, "
        f"gatekeepers, voicemail, mindset, etc. -- vary it, don't cluster on one theme).\n\n"
        "Return ONLY a JSON array, no prose, no markdown fences, in this exact shape:\n"
        '[{"quote": "...", "emphasis": ["1-3 word phrase from the quote to highlight"], '
        '"caption": "2-3 short sentences expanding the idea, then a line that pushes '
        'to the playbook and always includes the literal phrase \'link in bio\'."}]'
    )
    return system, user


def generate():
    if not GROQ_API_KEY:
        print("GROQ_API_KEY not set - skipping generation this run (posting is unaffected).")
        return []

    bank = _load_bank()
    existing_hooks = bank.get("reel_hooks", [])
    existing_quotes = [h["quote"] for h in existing_hooks]
    existing_ids = {h["id"] for h in existing_hooks}

    system, user = _build_prompt(existing_hooks)
    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 1.0,
        },
        timeout=60,
    )
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"].strip()
    raw = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()

    try:
        candidates = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            print("Could not parse LLM output as JSON. Raw output:\n", raw)
            return []
        candidates = json.loads(match.group(0))

    added = []
    for c in candidates:
        quote = c.get("quote", "").strip()
        caption = c.get("caption", "").strip()
        if not quote or not caption:
            continue
        if _is_dupe(quote, existing_quotes):
            continue
        if "link in bio" not in caption.lower():
            caption = caption.rstrip() + "\n\nLink in bio."

        hook_id = _slug(quote)
        base_id = hook_id
        n = 2
        while hook_id in existing_ids:
            hook_id = f"{base_id}_{n}"
            n += 1

        hook = {
            "id": hook_id,
            "quote": quote,
            "emphasis": c.get("emphasis", []),
            "caption": caption,
        }
        existing_hooks.append(hook)
        existing_quotes.append(quote)
        existing_ids.add(hook_id)
        added.append(hook)

    bank["reel_hooks"] = existing_hooks
    _save_bank(bank)
    print(f"Added {len(added)} new hooks (pool is now {len(existing_hooks)} total).")
    for h in added:
        print(" +", h["id"], "|", h["quote"])
    return added


if __name__ == "__main__":
    generate()
