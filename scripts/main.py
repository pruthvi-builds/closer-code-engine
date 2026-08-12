"""
Orchestrator — one run of this script = one Instagram reel post.
GitHub Actions calls this every 2 hours (see .github/workflows/post_every_2h.yml).

Flow:
  1. Pull the next unused hook from caption_engine (no repeats, reel-only pool)
  2. Render the black-bg/white-text static reel (compose_reel.py), with a
     procedurally generated audio bed muxed in automatically
  3. Compute the public URL for the rendered file (see PUBLIC_BASE_URL below)
  4. Publish via ig_poster (or just log it, while DRY_RUN=true)

Single content format only — static_post/carousel were dropped per
decision to keep everything as one consistent black/white static reel,
which Instagram also surfaces on the profile grid, covering "posts" too.
The old compose_post.render_carousel / render_quote_post functions still
exist in compose_post.py if that format is ever wanted again — they're
just not called from here anymore.
"""

import os
import re
import sys
import json
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import caption_engine
import compose_reel
import ig_poster


def _slug(text: str, max_len=24) -> str:
    """Filesystem/URL-safe slug from arbitrary headline text."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return (slug[:max_len] or "post")


# Public base URL where assets/renders/ is served from once pushed to GitHub.
# jsDelivr mirrors any public GitHub repo, but the @main branch alias does
# NOT guarantee any fixed propagation time after a push — it can take
# anywhere from a few seconds to several minutes. See _wait_until_public().
# Format: https://cdn.jsdelivr.net/gh/<user>/<repo>@main/assets/renders/<file>
PUBLIC_BASE_URL = os.environ.get(
    "PUBLIC_BASE_URL",
    "https://cdn.jsdelivr.net/gh/YOUR_GITHUB_USER/YOUR_REPO@main/assets/renders",
)


def render():
    """Step 1: generate the reel locally and write pending_publish.json
    describing what to publish once the file is pushed + public."""
    os.makedirs(config.RENDER_DIR, exist_ok=True)
    content = caption_engine.next_reel()
    fname = f"reel_{_slug(content['headline'])}_{int(time.time())}.mp4"
    out_path = os.path.join(config.RENDER_DIR, fname)
    compose_reel.render_reel(content["headline"], out_path,
                              trigger_word=content.get("trigger_word"))
    pending = {"type": "reel", "urls": [f"{PUBLIC_BASE_URL}/{os.path.basename(out_path)}"], "caption": content["caption"]}

    pending_path = os.path.join(config.CONTENT_DATA_DIR, "pending_publish.json")
    with open(pending_path, "w") as f:
        json.dump(pending, f, indent=2)
    print("Rendered. Pending publish info written to", pending_path)
    return pending


def _wait_until_public(url: str, max_wait: int = 480, interval: int = 10):
    """Poll a URL until it returns HTTP 200 with real content, instead of
    blindly sleeping a fixed amount of time before handing it to Instagram.

    This replaces a previous `sleep 90` step in the workflow. jsDelivr's
    @main branch alias updates on a *best-effort* schedule after a push —
    usually seconds, but sometimes several minutes — and there is no SLA.
    A fixed 90s wait silently failed on the first real scheduled run
    (Instagram got a 404/stale response and rejected the media with a
    400 error), which is why posts stopped going out. Active polling with
    a generous timeout (8 min, well inside the 2-hour cron gap) fixes this
    at the root instead of guessing a wait time.
    """
    elapsed = 0
    while elapsed < max_wait:
        try:
            r = requests.head(url, timeout=15, allow_redirects=True)
            if r.status_code == 200 and int(r.headers.get("content-length", "1")) > 0:
                print(f"Public URL is live after {elapsed}s: {url}")
                return True
        except requests.RequestException as exc:
            print(f"[{elapsed}s] not reachable yet ({exc.__class__.__name__}), retrying...")
        time.sleep(interval)
        elapsed += interval
    raise TimeoutError(f"Public URL never became reachable after {max_wait}s: {url}")


def publish():
    """Step 2: run AFTER the rendered file has been pushed to GitHub. Waits
    for the file to actually be live at its public CDN URL (see
    _wait_until_public) before calling the Graph API — publishing a URL
    Instagram can't yet fetch is exactly what caused missed posts before.
    Reads pending_publish.json written by render()."""
    pending_path = os.path.join(config.CONTENT_DATA_DIR, "pending_publish.json")
    with open(pending_path) as f:
        pending = json.load(f)

    _wait_until_public(pending["urls"][0])

    result = ig_poster.publish_reel(pending["urls"][0], pending["caption"])

    print("Result:", json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode == "render":
        render()
    elif mode == "publish":
        publish()
    else:
        render()
        publish()
