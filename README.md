# Closer Code Engine

Fully free, code-level content automation for `@built_by_pruthvi`. Produces one
consistent format — a static black-background/white-text quote reel — and posts
it automatically every 2 hours via Instagram's official Graph API.

Tested and confirmed working in this build: quote rendering, audio generation +
muxing, and the full render→publish pipeline (dry-run).

## Visual style — single format, no exceptions

Black background, white serif text (Lora), italics for emphasis instead of color
or bold. No kicker label, no handle watermark, no CTA text baked into the image,
no illustrated character — nothing but the words. Font size scales up
automatically for short quotes so they read as prominent, poster-like statements.

Completely static — held with zero motion for the whole clip, no zoom, no reveal,
no fade. A procedurally generated ambient audio bed is muxed in automatically
(see "About the audio" below).

This single video format is what gets published as a Reel, which Instagram also
surfaces on the profile grid — so it covers both "reel" and "post" placement with
one pipeline. (The older white-background/black-text template and the carousel
renderer are still in `compose_post.py` if you ever want them back — they're
just not used by default anymore.)

## About the audio — read this before expecting "trending sounds"

You asked for it to auto-select one of Instagram's trending songs. That's not
something the official posting API supports — Instagram's trending-audio catalog
only exists inside the Instagram app itself, there's no endpoint to browse or
attach it from code. The only way to do that programmatically is with unofficial,
reverse-engineered tools that impersonate the mobile app, which violate
Instagram's Terms of Service and can get an account flagged or banned. I'm not
going to wire that up quietly.

What's actually running: `scripts/audio.py` synthesizes a soft ambient pad
directly in Python (sine waves, no samples, no downloads) and `compose_reel.py`
muxes it into every video automatically before it's queued for upload. Zero
copyright risk, zero external dependency, fully free, fully hands-off. If you
want a specific trending sound on a given reel for extra reach, that's a manual
step in the Instagram app after it's posted — the one part of this that can't be
automated without the ToS risk above.

## About your credentials — I don't hold them

Nothing in this project stores or transmits your Instagram password, and I don't
have access to your account. The Graph API uses OAuth: you generate a long-lived
access token once (via Meta's own tools, see setup below), and store it as a
**GitHub repo secret** — encrypted, visible only to your own GitHub Actions runs.
From then on, GitHub's infrastructure (not your laptop, not me) runs the posting
script every 2 hours using that token. You can revoke the token from your Meta
account at any time to shut it off completely.

## How it works

1. **`content_data/hooks_bank.json` → `"reel_hooks"`** — ~12 punchy, standalone
   hook lines written for cold/algorithm-discovery audiences, each with the words
   to italicize and a full caption (with a follow/link-in-bio nudge).
2. **`scripts/caption_engine.py`** — picks the next unused hook each run, logs it
   to `content_data/content_log.csv` so nothing repeats, and appends the
   hashtag block from `config.HASHTAGS` to the caption automatically.
3. **`scripts/audio.py`** — generates the ambient background bed.
4. **`scripts/compose_reel.py`** — renders the quote as a static video and muxes
   in the audio bed via ffmpeg. Pure PIL + moviepy/ffmpeg, CPU only.
5. **`scripts/ig_poster.py`** — publishes via Instagram's official Graph API
   (free). Runs in `DRY_RUN` mode until you've completed Meta's approval process
   below.
6. **`scripts/main.py`** — orchestrates all of the above. `render` step generates
   the reel; `publish` step (run after a git push) posts it.
7. **`.github/workflows/post_every_2h.yml`** — GitHub Actions cron job that runs
   the whole pipeline every 2 hours, for free, forever — doesn't depend on your
   laptop being on.

12 posts/day (every 2h) stays comfortably under Instagram's 25-posts/24h Graph API
limit.

## Quick start (local, in VS Code)

```bash
cd closer-code-engine
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python scripts/main.py render            # generates one reel, DRY_RUN
open assets/renders/                     # review the output
```

With `DRY_RUN=true` (the default), nothing is actually posted — it just shows you
what it would post. Use this to review quality before going live.

## Going live: the real setup path

This is the part that takes real time and isn't a code problem — it's Meta's
approval process. Free, but not instant.

1. **Convert your Instagram to a Professional account** (Settings → Account type
   → Switch to Professional → Creator or Business). Free, instant.
2. **Create/link a Facebook Page** to that Instagram account (Meta requires this
   even for Instagram-only posting). Free.
3. **Create a Meta developer app** at developers.facebook.com → add the
   "Instagram Graph API" product.
4. **Request the `instagram_content_publish` permission** — for personal/small
   accounts you can usually stay in Development Mode and just add yourself as a
   Test User, which skips the multi-week App Review. Full App Review (needed if
   you want it working for accounts other than your own) can take 1–2 weeks.
5. **Get your long-lived access token + IG Business Account ID** via the Graph
   API Explorer (developers.facebook.com/tools/explorer) — Meta's docs walk
   through this: search "Instagram Graph API get started."
6. **Public media hosting** — the Graph API needs a public HTTPS URL for each
   video (it fetches, doesn't accept uploads). This project uses **jsDelivr**,
   which mirrors any public GitHub repo instantly for free:
   `https://cdn.jsdelivr.net/gh/<user>/<repo>@main/assets/renders/<file>`
   No setup needed beyond having a public GitHub repo — just push this project
   there.

## Deploying the automation (GitHub Actions — free, runs 24/7, no involvement after setup)

1. Push this folder to a new **public** GitHub repo (jsDelivr only mirrors
   public repos on the free tier).
2. In the repo, go to Settings → Secrets and variables → Actions, add:
   - `IG_USER_ID` — your Instagram Business Account ID
   - `IG_ACCESS_TOKEN` — your long-lived access token
   - `PUBLIC_BASE_URL` — `https://cdn.jsdelivr.net/gh/<you>/<repo>@main/assets/renders`
   - `DRY_RUN` — leave as `true` while testing; set to `false` when ready to go live
3. That's it — `.github/workflows/post_every_2h.yml` runs automatically every
   2 hours: renders a reel, commits it (which makes it public via jsDelivr),
   waits 90s for the CDN to catch up, then publishes. No manual step after this.
4. You can trigger a run manually anytime from the repo's Actions tab
   ("Run workflow") to test without waiting for the cron.

## Customizing content

- **Add more hooks**: edit `content_data/hooks_bank.json -> "reel_hooks"` — no
  code changes needed. Each entry needs `id`, `quote`, `emphasis` (list of
  words/phrases to italicize), and `caption`.
- **Change hashtags**: `HASHTAGS` in `scripts/config.py`.
- **Change audio character**: `CHORDS_HZ` in `scripts/audio.py` (different chord
  voicings) or `AUDIO_ENABLED = False` in `config.py` to post silent instead.
- **Swap fonts**: replace `assets/fonts/Serif-Regular.ttf` /
  `Serif-Italic.ttf` with any other serif pair (e.g. EB Garamond, Playfair
  Display from Google Fonts).
- **Adjust colors**: `REEL_BG` / `REEL_INK` at the top of `scripts/compose_reel.py`.

## On "not getting caught as spam"

You don't need to disguise anything — posting via the official Graph API at
12/day is within Instagram's own published limits, so there's no detection risk
from the automation itself. The actual lever for reach is content variety: the
anti-repeat logging in `caption_engine.py` already prevents duplicate hooks, but
you should periodically add fresh entries to `hooks_bank.json` (the built-in bank
will start repeating after ~12 reel hooks) and watch engagement — declining reach
on a specific hook type is Instagram's normal algorithm response to repetitive
content, not a penalty.

## On social proof / dollar-amount claims (per earlier discussion)

Once the account has real activity, use real screenshots — actual call outcomes,
actual buyer results if you have any. Fabricated earnings claims are both an FTC
compliance risk and something that erodes trust once people find out.

## Next step

Once this is live and posting, the next phase (per your plan) is the actual
offer: the sales page, the digital product itself, and the payment link. Say the
word and we'll build that next — Gumroad is the fastest free option for
hosting/selling a digital download with zero code.
