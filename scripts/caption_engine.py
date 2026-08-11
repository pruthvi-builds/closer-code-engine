"""
Picks the next piece of content (quote-card post or carousel topic, each
with a full pre-written caption) without repeating anything already
posted. Reads/writes content_data/content_log.csv.
"""

import csv
import json
import os
import random
from datetime import datetime

import config


def _load_bank():
    with open(config.HOOKS_JSON, "r") as f:
        return json.load(f)


def _load_log():
    if not os.path.exists(config.LOG_CSV):
        return []
    with open(config.LOG_CSV, "r") as f:
        return [row["content_id"] for row in csv.DictReader(f)]


def _append_log(content_id, content_type):
    is_new = not os.path.exists(config.LOG_CSV)
    with open(config.LOG_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp", "content_id", "content_type"])
        writer.writerow([datetime.utcnow().isoformat(), content_id, content_type])


def _pick(pool_name):
    bank = _load_bank()
    used = set(_load_log())
    pool = bank[pool_name]
    unused = [p for p in pool if p["id"] not in used]
    return random.choice(unused) if unused else random.choice(pool)


def next_reel():
    """Reels pull from their own content pool ("reel_hooks"), never the
    same lines used in posts/carousels. Reels get pushed by the algorithm
    to people who don't follow the account yet, so they're written as
    punchier, standalone hooks rather than the more reflective aphorisms
    used for posts — different crowd, different angle, same underlying
    ideas."""
    hook = _pick("reel_hooks")
    _append_log(hook["id"], "reel")
    caption = f"{hook['caption']}\n\n{config.HASHTAGS}"
    return {
        "type": "reel",
        "headline": hook["quote"],
        "trigger_word": hook["emphasis"][0] if hook.get("emphasis") else None,
        "caption": caption,
    }


def next_static_post():
    """Static posts pull from the "posts" pool — quieter, more reflective
    aphorisms aimed at people already on the profile."""
    post = _pick("posts")
    _append_log(post["id"], "static_post")
    return {
        "type": "static_post",
        "headline": post["quote"],
        "trigger_word": post["emphasis"][0] if post.get("emphasis") else None,
        "kicker": post.get("kicker"),
        "caption": post["caption"],
    }


def next_carousel():
    bank = _load_bank()
    used = set(_load_log())
    topics = bank["carousel_topics"]
    unused = [t for t in topics if t["title"] not in used]
    topic = random.choice(unused) if unused else random.choice(topics)
    _append_log(topic["title"], "carousel")
    return {
        "type": "carousel",
        "title": topic["title"],
        "kicker": topic.get("kicker"),
        "slides": topic["slides"],
        "caption": topic["caption"],
    }


if __name__ == "__main__":
    print(next_reel())
    print(next_carousel())
