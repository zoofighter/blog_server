"""소셜 포스트(Twitter/Threads) URL에서 메타데이터를 추출하는 서비스."""

import logging
import re
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TWITTER_OEMBED_URL = "https://publish.twitter.com/oembed"


def detect_platform(url: str) -> Optional[str]:
    """URL에서 플랫폼을 판별한다."""
    lower = url.lower()
    if "twitter.com" in lower or "x.com" in lower:
        return "twitter"
    if "threads.net" in lower:
        return "threads"
    return None


def _extract_handle_from_url(url: str, platform: str) -> str:
    """URL에서 @핸들을 추출한다."""
    if platform == "twitter":
        m = re.search(r"(?:twitter\.com|x\.com)/(@?\w+)", url)
        if m:
            handle = m.group(1)
            return handle if handle.startswith("@") else f"@{handle}"
    elif platform == "threads":
        m = re.search(r"threads\.net/(@?\w+)", url)
        if m:
            handle = m.group(1)
            return handle if handle.startswith("@") else f"@{handle}"
    return ""


async def extract_social_metadata(url: str) -> dict:
    """소셜 포스트 URL에서 메타데이터를 추출한다."""
    platform = detect_platform(url)
    if not platform:
        raise ValueError("지원하지 않는 플랫폼입니다. (Twitter/Threads만 지원)")

    handle = _extract_handle_from_url(url, platform)

    if platform == "twitter":
        return await _extract_twitter(url, handle)
    else:
        return await _extract_threads(url, handle)


async def _extract_twitter(url: str, handle: str) -> dict:
    """Twitter oEmbed API로 메타데이터를 추출한다."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BlogAggregator/1.0)"}

    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        resp = await client.get(
            TWITTER_OEMBED_URL,
            params={"url": url, "omit_script": "true"},
            headers=headers,
        )
        resp.raise_for_status()

    data = resp.json()
    return {
        "platform": "twitter",
        "original_url": url,
        "author_handle": handle,
        "author_name": data.get("author_name", ""),
        "content": _strip_html(data.get("html", "")),
        "image_url": "",
        "embed_html": data.get("html", ""),
        "posted_date": "",
    }


async def _extract_threads(url: str, handle: str) -> dict:
    """Threads 페이지를 fetch하여 OG 태그로 메타데이터를 추출한다."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BlogAggregator/1.0)"}

    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    og_desc = soup.find("meta", property="og:description")
    content = og_desc["content"].strip() if og_desc and og_desc.get("content") else ""

    og_image = soup.find("meta", property="og:image")
    image_url = ""
    if og_image and og_image.get("content"):
        img = og_image["content"].strip()
        if img.startswith("//"):
            image_url = "https:" + img
        elif img.startswith("/"):
            image_url = urljoin(url, img)
        else:
            image_url = img

    og_title = soup.find("meta", property="og:title")
    author_name = ""
    if og_title and og_title.get("content"):
        # "Username (@handle) on Threads" 형태에서 이름 추출
        title = og_title["content"].strip()
        m = re.match(r"^(.+?)\s*\(", title)
        if m:
            author_name = m.group(1).strip()
        else:
            author_name = title

    return {
        "platform": "threads",
        "original_url": url,
        "author_handle": handle,
        "author_name": author_name,
        "content": content,
        "image_url": image_url,
        "embed_html": "",
        "posted_date": "",
    }


def _strip_html(html: str) -> str:
    """HTML에서 텍스트만 추출한다."""
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(separator=" ", strip=True)
