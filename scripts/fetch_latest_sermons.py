"""
Fetches the latest videos from a YouTube channel's public RSS feed
and writes them to docs/videos.json for the church website to consume.

No API key required. Uses YouTube's public RSS feed:
https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID
"""

import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

# --- CONFIG ---------------------------------------------------------------
# Set this to the church's YouTube channel ID (starts with "UC...").
# You can hardcode it here, or set it as a GitHub Actions secret/env var
# named CHANNEL_ID instead (recommended so it's not buried in code).
CHANNEL_ID = os.environ.get("CHANNEL_ID", "REPLACE_WITH_CHANNEL_ID")

NUM_VIDEOS = 4  # 1 featured + 3 previous
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "videos.json")

FEED_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"

NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def fetch_feed(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def parse_entries(xml_text: str):
    root = ET.fromstring(xml_text)
    entries = root.findall("atom:entry", NAMESPACES)

    videos = []
    for entry in entries[:NUM_VIDEOS]:
        video_id = entry.find("yt:videoId", NAMESPACES).text
        title = entry.find("atom:title", NAMESPACES).text
        published = entry.find("atom:published", NAMESPACES).text

        # Try to grab the description YouTube includes in the media group
        description = ""
        media_group = entry.find("media:group", NAMESPACES)
        if media_group is not None:
            desc_el = media_group.find("media:description", NAMESPACES)
            if desc_el is not None and desc_el.text:
                description = desc_el.text.strip()

        videos.append({
            "id": video_id,
            "title": title,
            "published": published,
            "description": description,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "embedUrl": f"https://www.youtube.com/embed/{video_id}",
            # hqdefault always exists; maxresdefault sometimes doesn't for older videos
            "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            "thumbnailLarge": f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
        })
    return videos


def main():
    if not re.match(r"^UC[\w-]{22}$", CHANNEL_ID):
        print(f"ERROR: CHANNEL_ID looks invalid: '{CHANNEL_ID}'. "
              f"It should start with 'UC' and be 24 characters long.", file=sys.stderr)
        sys.exit(1)

    xml_text = fetch_feed(FEED_URL)
    videos = parse_entries(xml_text)

    if not videos:
        print("ERROR: No videos found in feed.", file=sys.stderr)
        sys.exit(1)

    output = {
        "updatedAt": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "channelId": CHANNEL_ID,
        "videos": videos,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(videos)} videos to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
