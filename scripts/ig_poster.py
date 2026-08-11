"""
Instagram Graph API publishing (free — no paid tier required).

Requires (see README.md for the full setup path):
  - Instagram account converted to Professional (Business/Creator)
  - Linked to a Facebook Page
  - A Meta developer app with instagram_content_publish permission
  - IG_USER_ID + IG_ACCESS_TOKEN set as env vars / GitHub secrets

Media (images/video) must be reachable at a public HTTPS URL for the
Graph API to fetch it — Instagram does not accept raw file uploads. This
project pairs with a free static host (e.g. GitHub Pages on this same
repo, or any free image host) to expose assets/renders/ publicly.
See README.md "Public media hosting" section.

While DRY_RUN=true (default), this module only prints what it WOULD do —
safe to run before your Meta app is approved.
"""

import time
import requests

import config

GRAPH_URL = f"https://graph.facebook.com/{config.GRAPH_API_VERSION}"


def _post(endpoint, payload):
    url = f"{GRAPH_URL}/{endpoint}"
    payload = {**payload, "access_token": config.IG_ACCESS_TOKEN}
    resp = requests.post(url, data=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def _wait_until_ready(container_id, max_wait=120):
    """Poll a media container until status_code == FINISHED (required for video/reels)."""
    elapsed = 0
    while elapsed < max_wait:
        r = requests.get(
            f"{GRAPH_URL}/{container_id}",
            params={"fields": "status_code", "access_token": config.IG_ACCESS_TOKEN},
            timeout=30,
        )
        status = r.json().get("status_code")
        if status == "FINISHED":
            return True
        if status == "ERROR":
            raise RuntimeError(f"Container {container_id} failed processing")
        time.sleep(5)
        elapsed += 5
    raise TimeoutError(f"Container {container_id} not ready after {max_wait}s")


def publish_single_image(image_url: str, caption: str):
    if config.DRY_RUN:
        print(f"[DRY_RUN] would publish IMAGE: {image_url}\ncaption: {caption[:80]}...")
        return {"dry_run": True}
    container = _post(f"{config.IG_USER_ID}/media", {
        "image_url": image_url,
        "caption": caption,
    })
    result = _post(f"{config.IG_USER_ID}/media_publish", {
        "creation_id": container["id"],
    })
    return result


def publish_carousel(image_urls: list, caption: str):
    if config.DRY_RUN:
        print(f"[DRY_RUN] would publish CAROUSEL ({len(image_urls)} slides)\ncaption: {caption[:80]}...")
        return {"dry_run": True}
    child_ids = []
    for url in image_urls:
        child = _post(f"{config.IG_USER_ID}/media", {
            "image_url": url,
            "is_carousel_item": "true",
        })
        child_ids.append(child["id"])
    container = _post(f"{config.IG_USER_ID}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(child_ids),
        "caption": caption,
    })
    result = _post(f"{config.IG_USER_ID}/media_publish", {
        "creation_id": container["id"],
    })
    return result


def publish_reel(video_url: str, caption: str, cover_url: str = None):
    if config.DRY_RUN:
        print(f"[DRY_RUN] would publish REEL: {video_url}\ncaption: {caption[:80]}...")
        return {"dry_run": True}
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
    }
    if cover_url:
        payload["cover_url"] = cover_url
    container = _post(f"{config.IG_USER_ID}/media", payload)
    _wait_until_ready(container["id"])
    result = _post(f"{config.IG_USER_ID}/media_publish", {
        "creation_id": container["id"],
    })
    return result
