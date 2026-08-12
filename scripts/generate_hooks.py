"""
Periodic content generator - keeps the reel_hooks pool growing so the
account never has to repeat itself.

Runs on its own schedule (see .github/workflows/generate_hooks_weekly.yml),
separate from the posting workflow. Each run:
  1. Reads the existing reel_hooks pool (used both as style reference and
     as a duplicate-avoidance list).
  2. Calls a free-tier LLM (Groq, OpenAI-compatible endpoint) asking for a
     batch of new punchy, aphoristic cold-calling/sales-closing one-liners
     in the exact same voice as the hand-written originals, each with a
     caption that always ends in a link-in-bio CTA pointing at the paid
     playbook (the actual monetization intent of the whole page).
  3. Filters out anything too similar to what's already in the bank
     (difflib ratio) AND anything that reads like generic LinkedIn/listicle
     marketing copy (banned-phrase filter - see BANNED_PHRASES), assigns
     clean ids, and appends the survivors to content_data/hooks_bank.json.

No web scraping of Instagram is involved anywhere in this pipeline --
there's no supported/safe way to programmatically browse "what's viral in
this niche" on IG, and scraping the app/site would violate its ToS and
risk the account getting flagged. This instead leans on an LLM steered
hard by full quote+caption examples (not just quotes) so it copies voice,
sentence rhythm, and caption structure -- not just topic.
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

# Generic marketing/listicle tells that do NOT match this page's voice.
# If a candidate's quote OR caption contains any of these, it's rejected
# outright rather than kept as a lower-quality filler.
BANNED_PHRASES = [
    "learn how to", "get the strategies", "take the first step",
    "unlock", "discover", "get instant access", "develop the skills",
    "level up", "game-changer", "game changer", "in today's fast-paced",
    "elevate your", "master the art of", "here's how", "top tips",
    "the key to", "unleash", "supercharge",
]

PRODUCT_CONTEXT = (
    "The page sells a $2 digital PDF playbook called 'The Closer Code' "
    "(cold call scripts, a 5-step call framework, word-for-word objection "
    "responses to the 15 most common objections, voicemail scripts, and a "
    "follow-up cadence). The checkout links live in the Instagram bio."
)

# Full quote+caption pairs, not just quotes, so the model copies caption
# rhythm and CTA phrasing too, not only the one-liner style.
FEW_SHOT_EXAMPLES = [
    {
        "quote": "Nobody becomes a closer without getting hung up on first.",
        "caption": "Every closer you've ever admired ate hundreds of hang-ups before their first real yes. That part just doesn't make it into the highlight reel.\n\nFollow for the parts of this that don't get posted. Real calls, real numbers, link in bio.",
    },
    {
        "quote": "The silence after your pitch is doing more than your pitch ever did.",
        "caption": "Most reps rush to fill it. That's the exact moment they hand control of the call back to the prospect.\n\nMore on this, daily. Link in bio for the full breakdown.",
    },
    {
        "quote": "You do not need a better script. You need one more rep.",
        "caption": "Most people go looking for the perfect words before they've made enough calls to know what actually needs saying.\n\nLink in bio if you're ready to stop looking for the script and start building the reps.",
    },
    {
        "quote": "Every no is just a not yet wearing a bad mood.",
        "caption": "Doesn't mean chase everyone forever. Means don't treat one bad-timed call as a permanent verdict on the deal.\n\nFollow for more of this. Real system, real calls — link in bio.",
    },
]


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


def _has_banned_phrase(text):
    low = text.lower()
    return any(p in low for p in BANNED_PHRASES)


def _build_prompt(existing_hooks):
    style_quotes = "\n".join(f'- "{h["quote"]}"' for h in existing_hooks[:15])
    examples_block = "\n\n".join(
        f'Quote: "{ex["quote"]}"\nCaption: "{ex["caption"]}"' for ex in FEW_SHOT_EXAMPLES
    )
    system = (
        "You write hooks for 'The Closer Code', a cold-calling/sales-closing Instagram "
        "page. Voice: short, blunt, aphoristic one-liners that sound like something a "
        "hardened sales manager would actually say out loud, not something written by a "
        "marketing team. Structure is almost always a contrarian-truth turn: state the "
        "common assumption, then flip it in the second half of the sentence. Max ~16 "
        "words per quote. No emojis. No hashtags in the quote. NEVER use generic "
        "corporate/LinkedIn phrasing -- banned words and phrases include: 'learn how to', "
        "'unlock', 'discover', 'level up', 'game-changer', 'master the art of', 'elevate "
        "your', 'here's how', 'the key to', 'top tips', 'supercharge'. Captions are 2 "
        "short sentences of plain, specific, concrete observation (not vague encouragement), "
        "followed by a one-line push to the playbook that always includes the literal "
        "phrase 'link in bio', phrased differently each time (not the same template "
        "sentence repeated)."
    )
    user = (
        f"Here are full examples of the exact voice and caption structure to match:\n\n"
        f"{examples_block}\n\n"
        f"Here are more existing quotes (for topic/style reference only -- do NOT repeat "
        f"these or anything too close to them in phrasing or idea):\n{style_quotes}\n\n"
        f"{PRODUCT_CONTEXT}\n\n"
        f"Write {BATCH_SIZE} brand-new hooks that could be mistaken for ones this same "
        f"person wrote. Cover different angles (rejection, confidence, objections, "
        f"follow-up, discipline, gatekeepers, voicemail, mindset, quotas, burnout, "
        f"comparison to others, etc.) -- vary it, don't cluster on one theme.\n\n"
        f"IMPORTANT -- vary SENTENCE STRUCTURE across the batch too, not just topic. "
        f"Do not let more than 2-3 hooks in this batch use the same '<X> is not <Y>. "
        f"It's <Z>.' template back to back. Rotate between different structures such as: "
        f"a flat declarative statement (e.g. 'The scariest number to dial is always the "
        f"next one.'), a 'Most people do X. The ones who win do Y instead.' contrast, a "
        f"direct address to the reader ('You do not need X. You need Y.'), a reframe of "
        f"a common belief ('X is not the end of the call. It is the start of the real "
        f"one.'), and a standalone truth with no explicit contrast at all.\n\n"
        "Return ONLY a JSON array, no prose, no markdown fences, in this exact shape:\n"
        '[{"quote": "...", "emphasis": ["1-3 word phrase from the quote to highlight"], '
        '"caption": "..."}]'
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
            "temperature": 0.9,
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

    added, rejected_banned, rejected_dupe = [], 0, 0
    for c in candidates:
        quote = c.get("quote", "").strip()
        caption = c.get("caption", "").strip()
        if not quote or not caption:
            continue
        if _has_banned_phrase(quote) or _has_banned_phrase(caption):
            rejected_banned += 1
            continue
        if _is_dupe(quote, existing_quotes):
            rejected_dupe += 1
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
    print(f"Added {len(added)} new hooks (pool is now {len(existing_hooks)} total). "
          f"Rejected {rejected_banned} for generic marketing phrasing, {rejected_dupe} as near-duplicates.")
    for h in added:
        print(" +", h["id"], "|", h["quote"])
    return added


if __name__ == "__main__":
    generate()
