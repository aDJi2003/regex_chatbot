import os
import re
import logging
import aiohttp

logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    raise RuntimeError("YOUTUBE_API_KEY belum diset di environment.")

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

YOUTUBE_VIDEO_REGEX = re.compile(
    r'(?:https?://)?(?:www\.)?(?:'
    r'youtube\.com/watch\?v=|youtube\.com/watch\?.*?&v=|youtu\.be/|youtube\.com/shorts/)'
    r'([A-Za-z0-9_-]{11})'
)

CHANNEL_ID_REGEX = re.compile(r'youtube\.com/channel/([A-Za-z0-9_-]+)', re.I)
CHANNEL_USER_REGEX = re.compile(r'youtube\.com/user/([^/?&]+)', re.I)
CHANNEL_CUSTOM_REGEX = re.compile(r'youtube\.com/(?:c|@)([^/?&]+)', re.I)

TIMESTAMP_REGEX = re.compile(r'\b(?:\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2})\b')

MAX_COMMENT_PAGES = 5
MAX_COMMENTS_TO_SCAN = 500

async def fetch_youtube_video_info(session: aiohttp.ClientSession, video_id: str):
    url = f"{YOUTUBE_API_BASE}/videos"
    params = {"part": "snippet,statistics,contentDetails", "id": video_id, "key": YOUTUBE_API_KEY}
    async with session.get(url, params=params) as resp:
        if resp.status != 200:
            logger.error("videos API error %s: %s", resp.status, await resp.text())
            return None
        data = await resp.json()
        items = data.get("items", [])
        return items[0] if items else None

async def fetch_channel_by_id(session: aiohttp.ClientSession, channel_id: str):
    url = f"{YOUTUBE_API_BASE}/channels"
    params = {"part": "snippet,statistics", "id": channel_id, "key": YOUTUBE_API_KEY}
    async with session.get(url, params=params) as resp:
        if resp.status != 200:
            logger.error("channels API returned status %s", resp.status)
            return None
        data = await resp.json()
        items = data.get("items", [])
        return items[0] if items else None

async def fetch_channel_by_username(session: aiohttp.ClientSession, username: str):
    url = f"{YOUTUBE_API_BASE}/channels"
    params = {"part": "snippet,statistics", "forUsername": username, "key": YOUTUBE_API_KEY}
    async with session.get(url, params=params) as resp:
        if resp.status != 200:
            logger.error("channels(forUsername) API returned status %s", resp.status)
            return None
        data = await resp.json()
        items = data.get("items", [])
        return items[0] if items else None
    
async def search_channel(session: aiohttp.ClientSession, query: str):
    url = f"{YOUTUBE_API_BASE}/search"
    params = {"part": "snippet", "q": query, "type": "channel", "maxResults": 1, "key": YOUTUBE_API_KEY}
    async with session.get(url, params=params) as resp:
        if resp.status != 200:
            logger.error("search channel API returned status %s", resp.status)
            return None
        data = await resp.json()
        items = data.get("items", [])
        return items[0] if items else None

async def fetch_search_videos(session: aiohttp.ClientSession, query: str, max_results: int = 5):
    url = f"{YOUTUBE_API_BASE}/search"
    params = {"part": "snippet", "q": query, "type": "video", "maxResults": max_results, "key": YOUTUBE_API_KEY}
    async with session.get(url, params=params) as resp:
        if resp.status != 200:
            logger.error("search videos API returned status %s", resp.status)
            return None
        data = await resp.json()
        return data.get("items", [])

async def fetch_comment_threads(session: aiohttp.ClientSession, video_id: str, max_pages: int = MAX_COMMENT_PAGES):
    items = []
    url = f"{YOUTUBE_API_BASE}/commentThreads"
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": 100,
        "textFormat": "plainText",
        "key": YOUTUBE_API_KEY
    }
    next_token = None
    pages = 0
    while pages < max_pages:
        if next_token:
            params["pageToken"] = next_token
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                logger.error("commentThreads API returned %s: %s", resp.status, await resp.text())
                break
            data = await resp.json()
        page_items = data.get("items", [])
        items.extend(page_items)
        pages += 1
        next_token = data.get("nextPageToken")
        if not next_token:
            break
        if len(items) >= MAX_COMMENTS_TO_SCAN:
            break
    return items[:MAX_COMMENTS_TO_SCAN]
