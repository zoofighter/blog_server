"""소셜 포스트(Twitter/Threads) URL에서 메타데이터를 추출하는 서비스."""

import logging
import re
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

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

    추출 실패 시에도 URL 기반 최소 정보를 반환한다 (exception 없음).
    """
    platform = detect_platform(url)
    if not platform:
        raise ValueError("지원하지 않는 플랫폼입니다. (Twitter/Threads만 지원)")

    handle = _extract_handle_from_url(url, platform)

    try:
        if platform == "twitter":
            return await _extract_twitter(url, handle)
        else:
            return await _extract_threads(url, handle)
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


async def _extract_threads(url: str, handle: str) -> dict:
    """Playwright 헤드리스 브라우저로 Threads 포스트 메타데이터를 추출한다."""
    content = ""
    author_name = ""
    image_url = ""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/131.0.0.0 Safari/537.36",
        )
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # --- 본문 텍스트 (렌더링된 DOM에서 직접 추출) ---
            text_el = await page.query_selector(
                '[data-pressable-container] div[dir="auto"]'
            )
            if text_el:
                content = (await text_el.text_content() or "").strip()

            # --- 작성자 이름 (핸들 기반 프로필 링크에서) ---
            clean_handle = handle.lstrip("@")
            name_el = await page.query_selector(
                f'a[href*="/@{clean_handle}"] span'
            )
            if name_el:
                author_name = (await name_el.text_content() or "").strip()

            # --- 포스트 이미지 (프로필 사진 제외) ---
            imgs = await page.query_selector_all("img")
            for img in imgs:
                src = await img.get_attribute("src") or ""
                alt = await img.get_attribute("alt") or ""
                if (
                    "cdninstagram.com" in src
                    and "rsrc.php" not in src
                    and "s150x150" not in src
                    and "profile" not in alt.lower()
                ):
                    image_url = src
                    break
        finally:
            await browser.close()

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
