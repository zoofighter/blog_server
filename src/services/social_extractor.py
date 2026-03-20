"""소셜 포스트(Twitter/Threads) URL에서 메타데이터를 추출하는 서비스."""

import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TWITTER_OEMBED_URL = "https://publish.twitter.com/oembed"


def detect_platform(url: str) -> Optional[str]:
    """URL에서 플랫폼을 판별한다."""
    lower = url.lower()
    if "twitter.com" in lower or "x.com" in lower:
        return "twitter"
    if "threads.net" in lower or "threads.com" in lower:
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
        m = re.search(r"threads\.(?:net|com)/(@?[\w.]+)", url)
        if m:
            handle = m.group(1)
            return handle if handle.startswith("@") else f"@{handle}"
    return ""


def _base_metadata(url: str) -> dict:
    """URL에서 파싱 가능한 최소 메타데이터를 반환한다."""
    platform = detect_platform(url) or ""
    handle = _extract_handle_from_url(url, platform) if platform else ""
    return {
        "platform": platform,
        "original_url": url,
        "author_handle": handle,
        "author_name": "",
        "content": "",
        "image_url": "",
        "embed_html": "",
        "posted_date": "",
    }


async def extract_social_metadata(url: str) -> dict:
    """소셜 포스트 URL에서 메타데이터를 추출한다.

    - Twitter: oEmbed API로 본문·작성자 추출
    - Threads: URL에서 핸들만 추출 (Meta가 비인증 접근 차단)
    추출 실패 시에도 URL 기반 최소 정보를 반환한다.
    """
    platform = detect_platform(url)
    if not platform:
        raise ValueError("지원하지 않는 플랫폼입니다. (Twitter/Threads만 지원)")

    handle = _extract_handle_from_url(url, platform)

    try:
        if platform == "twitter":
            return await _extract_twitter(url, handle)
        else:
            # Threads는 비인증 메타데이터 추출 불가 — URL 기반 정보만 반환
            return _base_metadata(url)
    except Exception as e:
        logger.warning("메타데이터 추출 실패 [%s]: %s — 기본 정보로 등록", url, e)
        return _base_metadata(url)


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


def _strip_html(html: str) -> str:
    """HTML에서 텍스트만 추출한다."""
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(separator=" ", strip=True)
