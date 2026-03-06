"""URL에서 블로그 포스트 메타데이터를 추출하는 서비스."""

import logging
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


async def extract_metadata(url: str) -> dict:
    """URL에서 제목, 본문, 이미지, 작성자, 발행일 등을 추출한다."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; BlogAggregator/1.0)"
    }

    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    return {
        "title": _extract_title(soup),
        "content": _extract_content(soup),
        "image_url": _extract_image(soup, url),
        "author": _extract_author(soup),
        "published_date": _extract_date(soup),
        "description": _extract_description(soup),
    }


def _extract_title(soup: BeautifulSoup) -> str:
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        return title_tag.string.strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return ""


def _extract_content(soup: BeautifulSoup) -> str:
    for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    article = soup.find("article")
    if article:
        return article.get_text(separator="\n", strip=True)

    main = soup.find("main")
    if main:
        return main.get_text(separator="\n", strip=True)

    # 가장 긴 텍스트 블록을 본문으로 추정
    candidates = soup.find_all(["div", "section"])
    best = ""
    for c in candidates:
        text = c.get_text(separator="\n", strip=True)
        if len(text) > len(best):
            best = text

    return best if best else soup.get_text(separator="\n", strip=True)


def _extract_image(soup: BeautifulSoup, base_url: str) -> str:
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        img_url = og["content"].strip()
        if img_url.startswith("//"):
            return "https:" + img_url
        if img_url.startswith("/"):
            return urljoin(base_url, img_url)
        return img_url

    twitter = soup.find("meta", attrs={"name": "twitter:image"})
    if twitter and twitter.get("content"):
        return twitter["content"].strip()

    return ""


def _extract_author(soup: BeautifulSoup) -> str:
    meta = soup.find("meta", attrs={"name": "author"})
    if meta and meta.get("content"):
        return meta["content"].strip()

    og = soup.find("meta", property="article:author")
    if og and og.get("content"):
        return og["content"].strip()

    return ""


def _extract_date(soup: BeautifulSoup) -> str:
    for prop in ["article:published_time", "og:article:published_time"]:
        meta = soup.find("meta", property=prop)
        if meta and meta.get("content"):
            return meta["content"].strip()[:10]  # YYYY-MM-DD

    meta = soup.find("meta", attrs={"name": "date"})
    if meta and meta.get("content"):
        return meta["content"].strip()[:10]

    time_tag = soup.find("time", attrs={"datetime": True})
    if time_tag:
        return time_tag["datetime"].strip()[:10]

    return ""


def _extract_description(soup: BeautifulSoup) -> str:
    og = soup.find("meta", property="og:description")
    if og and og.get("content"):
        return og["content"].strip()

    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"].strip()

    return ""
