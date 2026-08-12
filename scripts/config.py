"""
Central config for the content engine.
Edit BRAND_NAME, HANDLE, and the character wardrobe prompts here.
Everything else reads from this file so you only configure once.
"""

import os

# ---- Brand ----
BRAND_NAME = "The Closer Code"
HANDLE = "@the_closer_code"          # your IG handle (posting target)
NICHE = "cold calling / sales closing"
LINK_IN_BIO_CTA = "Link in bio \U0001F447"   # 👇 (used in real IG captions, which render emoji natively)
LINK_IN_BIO_CTA_IMAGE_SAFE = "LINK IN BIO >>"  # used when drawing text ONTO images (PIL fonts can't render emoji)

# Appended to the end of every reel caption automatically.
HASHTAGS = "#coldcalling #salestips #closer #objectionhandling #salesmotivation #b2bsales"

# ---- Character (the "static host") ----
# Keep this description IDENTICAL every time you regenerate the wardrobe.
# Only the OUTFIT/POSE lines in WARDROBE below should change.
CHARACTER_BASE = (
    "flat 2D vector illustration sticker, bold thick black outlines, "
    "minimalist cartoon mascot character, simple shading, young male "
    "salesman, confident expression, consistent facial design, "
    "full upper body visible from waist up, shoulders and both arms "
    "in frame, wide shot not a close-up headshot, centered, plain solid "
    "color background, no text, no watermark, procreate sticker art style"
)

# Same seed = same face/proportions across generations (Pollinations honors
# seed deterministically for a given prompt+size). We vary only outfit/pose
# text, not the seed, so the face stays recognizable.
CHARACTER_SEED = 774411

# Wardrobe = the finite set of "outfits" the character cycles through.
# This mirrors what pages like the_closer_code actually do: a SMALL set of
# pre-rendered variants reused constantly, not a new AI image every post.
WARDROBE = [
    {"id": "suit_phone", "prompt": "wearing a navy business suit, holding a phone to his ear, arm raised"},
    {"id": "hoodie_laptop", "prompt": "wearing a black hoodie, sitting, laptop open in front of him, typing"},
    {"id": "headset_desk", "prompt": "wearing a casual shirt, wearing a call center headset, one hand up explaining"},
    {"id": "suit_thumbsup", "prompt": "wearing a navy business suit, giving a thumbs up, big confident smile"},
    {"id": "hoodie_pointing", "prompt": "wearing a black hoodie, pointing forward at the viewer, serious focused face"},
    {"id": "headset_money", "prompt": "wearing a casual shirt, call center headset, holding stacks of cash, excited face"},
    {"id": "suit_shrug", "prompt": "wearing a navy business suit, shrugging with palms up, unimpressed expression"},
    {"id": "hoodie_thinking", "prompt": "wearing a black hoodie, hand on chin, thinking pose, one eyebrow raised"},
]

# ---- Paths ----
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARACTER_DIR = os.path.join(ROOT, "assets", "character")
RENDER_DIR = os.path.join(ROOT, "assets", "renders")
CONTENT_DATA_DIR = os.path.join(ROOT, "content_data")
LOG_CSV = os.path.join(CONTENT_DATA_DIR, "content_log.csv")
HOOKS_JSON = os.path.join(CONTENT_DATA_DIR, "hooks_bank.json")

# ---- Posting cadence ----
# 12 posts/day (every 2h) stays well under Instagram's 25 posts/24h Graph API cap.
POST_INTERVAL_HOURS = 2
# Single format only, per decision to drop the white static-post/carousel
# templates: every post is the black-bg/white-text static reel, published
# as a Reel (which also shows on the profile grid, covering "posts" too).
# static_post/carousel code remains in compose_post.py if you want it back
# later, just not used by the default rotation.
POST_TYPE_ROTATION = ["reel"]

# ---- Background audio (muxed into every reel automatically) ----
# Instagram's own "trending sounds" catalog is only accessible from inside
# the Instagram app itself -- there is no official API to browse/attach it
# programmatically. Auto-generating a free, copyright-safe ambient bed and
# muxing it in keeps posting fully hands-off without relying on unofficial
# private-API tools that risk the account being flagged. See README.
AUDIO_ENABLED = True
AUDIO_DURATION_PAD = 0.5  # seconds of extra bed rendered beyond video length, trimmed to match

# ---- Instagram Graph API (fill via environment variables / GitHub secrets) ----
IG_USER_ID = os.environ.get("IG_USER_ID", "")          # Instagram Business Account ID
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")  # long-lived Page access token
GRAPH_API_VERSION = "v23.0"  # bumped from v21.0 -- Meta retires old API versions on a rolling ~2yr cycle, keep this reasonably current

# If True, scripts generate content but skip the actual publish call
# (use this until your Meta app is approved / tokens are set).
DRY_RUN = os.environ.get("DRY_RUN", "true").lower() == "true"
