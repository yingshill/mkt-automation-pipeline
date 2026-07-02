"""Fetch TechEquity session data from public sources — no API keys.

Video listing: YouTube's public RSS feed (works for channel_id or
playlist_id, no auth). Transcripts: youtube-transcript-api (public
scrape of YouTube's own transcript endpoint). Speaker enrichment:
individual TechEquity speaker pages, found by guessing a slug from
the speaker's name (the index page is client-rendered and can't be
listed reliably without a browser — see plan grounding notes).
"""
import logging
import re
# Using defusedxml (not stdlib xml.etree.ElementTree) because this feed is
# fetched over the network and must be treated as untrusted input —
# stdlib ElementTree is vulnerable to XXE/billion-laughs on untrusted XML.
import defusedxml.ElementTree as ET

import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

logger = logging.getLogger(__name__)

YOUTUBE_RSS_URL = "https://www.youtube.com/feeds/videos.xml"
SPEAKER_PAGE_URL = "https://techequity-ai.org/speaker/{slug}/"
_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


def resolve_channel_id(handle: str) -> str:
    resp = requests.get(f"https://www.youtube.com/@{handle}", timeout=10)
    resp.raise_for_status()
    # Grounding note: the brief's original regex targeted a `"channelId":"UC..."`
    # key in embedded JSON. That key is no longer present on the live page
    # (verified against https://www.youtube.com/@TechEquityAi during this task) —
    # YouTube now exposes the channel ID via the canonical <link> tag, a
    # `<meta itemprop="identifier">` tag, and an `"externalId"` key in embedded
    # JSON instead. Try each, most-stable first.
    match = (
        re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"', resp.text)
        or re.search(r'<meta itemprop="identifier" content="(UC[\w-]{22})"', resp.text)
        or re.search(r'"externalId":"(UC[\w-]{22})"', resp.text)
    )
    if not match:
        raise ValueError(f"Could not resolve channel ID for handle @{handle}")
    return match.group(1)


def fetch_channel_videos(channel_id: str) -> list[dict]:
    resp = requests.get(YOUTUBE_RSS_URL, params={"channel_id": channel_id}, timeout=10)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    videos = []
    for entry in root.findall("atom:entry", _ATOM_NS):
        video_id = entry.find("yt:videoId", _ATOM_NS).text
        title = entry.find("atom:title", _ATOM_NS).text
        published = entry.find("atom:published", _ATOM_NS).text
        media_group = entry.find("{http://search.yahoo.com/mrss/}group")
        description = ""
        if media_group is not None:
            desc_el = media_group.find("{http://search.yahoo.com/mrss/}description")
            if desc_el is not None and desc_el.text:
                description = desc_el.text
        videos.append({
            "video_id": video_id,
            "title": title,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "description": description,
            "published_at": published,
        })
    return videos


def fetch_transcript(video_id: str) -> str | None:
    try:
        segments = YouTubeTranscriptApi.get_transcript(video_id)
    except (TranscriptsDisabled, NoTranscriptFound, Exception) as exc:
        logger.warning(
            "fetch_transcript: no transcript available for video_id=%s (%s: %s); falling back to None",
            video_id, type(exc).__name__, exc,
        )
        return None
    return " ".join(seg["text"] for seg in segments)


def slugify_name(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def fetch_speaker_profile(speaker_name: str) -> dict | None:
    slug = slugify_name(speaker_name)
    resp = requests.get(SPEAKER_PAGE_URL.format(slug=slug), timeout=10)
    if resp.status_code == 404:
        logger.warning(
            "fetch_speaker_profile: no speaker page found for speaker_name=%r (slug=%r, url=%s returned 404); "
            "falling back to None",
            speaker_name, slug, SPEAKER_PAGE_URL.format(slug=slug),
        )
        return None
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    # Grounding note: verified against the live page-builder markup at
    # https://techequity-ai.org/speaker/george-ekas/ during this task. The
    # page is built with Elementor, which emits a purely decorative
    # `<h2> &gt; </h2>` breadcrumb-style heading *before* the real
    # title/company h2 — both share the same CSS class, so `soup.find("h2")`
    # (the brief's original selector) silently grabbed the decorative ">"
    # instead of the title. Skip heading text that's only punctuation/symbols.
    title_el = next(
        (h2 for h2 in soup.find_all("h2") if re.search(r"\w", h2.get_text(strip=True))),
        None,
    )
    bio_el = soup.find("p")
    return {
        "title_company": title_el.get_text(strip=True) if title_el else "",
        "bio": bio_el.get_text(strip=True) if bio_el else "",
    }


def build_session_record(video: dict) -> dict:
    transcript = fetch_transcript(video["video_id"])
    return {
        "video_id": video["video_id"],
        "title": video["title"],
        "url": video["url"],
        "description": video.get("description", ""),
        "transcript": transcript,
        "transcript_available": transcript is not None,
        "speaker_name": None,
        "speaker_bio": None,
    }
