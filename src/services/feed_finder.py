"""블로그 URL에서 RSS/Atom 피드 URL을 자동 탐색하는 서비스."""

import logging
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# 플랫폼별 피드 URL 패턴
PLATFORM_PATTERNS = {
    "blog.naver.com": lambda url: _naver_feed(url),
    "brunch.co.kr": lambda url: _brunch_feed(url),
    "tistory.com": lambda url: urljoin(url.rstrip("/") + "/", "rss"),
    "medium.com": lambda url: url.rstrip("/") + "/feed",
    "velog.io": lambda url: url.rstrip("/") + "/rss",
    "wordpress.com": lambda url: url.rstrip("/") + "/feed",
    "github.io": lambda url: url.rstrip("/") + "/feed.xml",
    "substack.com": lambda url: url.rstrip("/") + "/feed",
}

# 일반적으로 시도할 피드 경로
COMMON_FEED_PATHS = [
    "/feed", "/rss", "/rss.xml", "/atom.xml", "/feed.xml",
    "/index.xml", "/feed/", "/rss/", "/feeds/posts/default",
]

FEED_CONTENT_TYPES = [
    "application/rss+xml",
    "application/atom+xml",
    "application/xml",
    "text/xml",
    "application/rdf+xml",
]


def _naver_feed(url: str) -> str:
    """네이버 블로그 RSS URL 생성."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    blog_id = path.split("/")[0] if path else ""
    if blog_id:
        return f"https://rss.blog.naver.com/{blog_id}.xml"
    return ""


def _brunch_feed(url: str) -> str:
    """브런치 RSS URL 생성."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if path.startswith("@"):
        return f"https://brunch.co.kr/rss/@@{path[1:]}"
    return ""


async def find_feed_url(blog_url: str) -> Optional[str]:
    """블로그 URL에서 RSS 피드 URL을 탐색한다.

    탐색 순서:
    1. 플랫폼별 패턴 매칭
    2. HTML <link> 태그에서 피드 URL 추출
    3. 일반 경로 시도
    """
    blog_url = blog_url.rstrip("/")
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BlogAggregator/1.0)"}

    # 1. 플랫폼별 패턴
    parsed = urlparse(blog_url)
    hostname = parsed.hostname or ""
    for domain, pattern_fn in PLATFORM_PATTERNS.items():
        if domain in hostname:
            feed_url = pattern_fn(blog_url)
            if feed_url and await _is_valid_feed(feed_url, headers):
                return feed_url
            break

    # 2. HTML <link> 태그 탐색
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(blog_url, headers=headers)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                for link in soup.find_all("link", rel="alternate"):
                    link_type = (link.get("type") or "").lower()
                    if any(ct in link_type for ct in FEED_CONTENT_TYPES):
                        href = link.get("href", "").strip()
                        if href:
                            feed_url = urljoin(blog_url, href)
                            return feed_url
    except Exception as e:
        logger.debug("HTML 탐색 실패 (%s): %s", blog_url, e)

    # 3. 일반 경로 시도
    for path in COMMON_FEED_PATHS:
        feed_url = blog_url + path
        if await _is_valid_feed(feed_url, headers):
            return feed_url

    return None


async def _is_valid_feed(url: str, headers: dict) -> bool:
    """URL이 유효한 피드인지 확인한다."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            resp = await client.head(url, headers=headers)
            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "").lower()
                if any(ct in content_type for ct in FEED_CONTENT_TYPES + ["text/html"]):
                    return True
                # HEAD만으로 판단 불가 → GET으로 내용 확인
                resp = await client.get(url, headers=headers)
                text = resp.text[:500].lower()
                return "<rss" in text or "<feed" in text or "<rdf" in text
    except Exception:
        pass
    return False
