"""소셜 계정 기반 크롤러.

등록된 Twitter/Threads 계정의 포스트를 자동으로 수집한다.
Twitter: Nitter RSS 피드 (feedparser) + HTML 스크래핑 폴백
Threads: 프로필 페이지 OG 태그 스크래핑
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Optional

import feedparser
import httpx
from bs4 import BeautifulSoup

from src.database.repository import Repository

logger = logging.getLogger(__name__)

NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def _get_nitter_instances(config: dict) -> list:
    """config에서 Nitter 인스턴스 목록을 가져온다. 없으면 기본값 사용."""
    instances = config.get("nitter", {}).get("instances")
    if instances and isinstance(instances, list):
        return instances
    return NITTER_INSTANCES


def build_nitter_rss_url(handle: str, instance: str = None) -> str:
    clean = handle.lstrip("@")
    base = instance or NITTER_INSTANCES[0]
    return f"{base}/{clean}/rss"


async def crawl_all_social_accounts(repo: Repository, config: dict) -> dict:
    """모든 활성 소셜 계정을 크롤링한다."""
    accounts = repo.get_active_social_accounts()
    logger.info("소셜 크롤링 시작: %d개 계정", len(accounts))

    total_found = 0
    total_added = 0
    errors = 0

    for account in accounts:
        result = await crawl_social_account(account, repo, config)

        status = "success" if result["error"] is None else "failed"
        repo.create_social_crawl_log(
            account_id=account["id"],
            status=status,
            posts_found=result["posts_found"],
            posts_added=result["posts_added"],
            error_message=result["error"],
        )
        repo.update_social_account_crawl_status(
            account["id"], error=result["error"]
        )

        total_found += result["posts_found"]
        total_added += result["posts_added"]
        if result["error"]:
            errors += 1

        await asyncio.sleep(2)

    logger.info(
        "소셜 크롤링 완료: %d개 계정, %d건 발견, %d건 추가, %d건 오류",
        len(accounts), total_found, total_added, errors,
    )
    return {
        "total_accounts": len(accounts),
        "total_found": total_found,
        "total_added": total_added,
        "errors": errors,
    }


async def crawl_social_account(account: dict, repo: Repository,
                               config: dict) -> dict:
    """단일 소셜 계정의 포스트를 크롤링한다."""
    platform = account["platform"]

    if platform == "twitter":
        return await _crawl_twitter_account(account, repo, config)
    elif platform == "threads":
        return await _crawl_threads_account(account, repo, config)
    else:
        return {"posts_found": 0, "posts_added": 0,
                "error": f"미지원 플랫폼: {platform}"}


# --- Twitter (Nitter) ---

async def _crawl_twitter_account(account: dict, repo: Repository,
                                 config: dict) -> dict:
    """Twitter 계정 크롤링: Nitter RSS → HTML 스크래핑 순서로 시도."""
    handle = account["handle"]
    instances = _get_nitter_instances(config)

    # Strategy 1: Nitter RSS
    for instance in instances:
        rss_url = build_nitter_rss_url(handle, instance)
        try:
            result = await _crawl_twitter_via_rss(rss_url, account, repo)
            if result["posts_found"] > 0 or result["error"] is None:
                if not account.get("feed_url"):
                    repo.update_social_account(account["id"], feed_url=rss_url)
                return result
        except Exception as e:
            logger.debug("[%s] Nitter RSS %s 실패: %s", handle, instance, e)
            continue

    # Strategy 2: Nitter HTML 스크래핑
    for instance in instances:
        try:
            result = await _crawl_twitter_via_html(instance, account, repo)
            if result["posts_found"] > 0 or result["error"] is None:
                return result
        except Exception as e:
            logger.debug("[%s] Nitter HTML %s 실패: %s", handle, instance, e)
            continue

    return {"posts_found": 0, "posts_added": 0,
            "error": "모든 Nitter 인스턴스 접속 실패"}


async def _crawl_twitter_via_rss(rss_url: str, account: dict,
                                 repo: Repository) -> dict:
    """Nitter RSS 피드를 feedparser로 파싱하여 트윗을 수집한다."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
        resp = await client.get(rss_url, headers=HEADERS)
        resp.raise_for_status()

    feed = feedparser.parse(resp.text)
    if feed.bozo and not feed.entries:
        return {"posts_found": 0, "posts_added": 0,
                "error": f"RSS 파싱 오류: {feed.bozo_exception}"}

    posts_found = len(feed.entries)
    posts_added = 0

    for entry in feed.entries:
        url = entry.get("link", "").strip()
        if not url:
            continue

        url = _nitter_to_twitter_url(url)

        if repo.social_post_exists_url(url):
            continue

        content = ""
        if entry.get("summary"):
            content = BeautifulSoup(
                entry.summary, "lxml"
            ).get_text(separator=" ", strip=True)
        elif entry.get("title"):
            content = entry.title

        posted_date = _parse_feed_date(entry)
        image_url = _extract_feed_image(entry)

        repo.create_social_post(
            platform="twitter",
            original_url=url,
            author_handle=account["handle"],
            author_name=account.get("display_name") or "",
            content=content[:2000] if content else None,
            image_url=image_url or None,
            embed_html=None,
            posted_date=posted_date,
            account_id=account["id"],
        )
        posts_added += 1

    return {"posts_found": posts_found, "posts_added": posts_added, "error": None}


async def _crawl_twitter_via_html(instance: str, account: dict,
                                  repo: Repository) -> dict:
    """Nitter HTML 프로필 페이지를 스크래핑하여 트윗을 수집한다."""
    clean_handle = account["handle"].lstrip("@")
    profile_url = f"{instance}/{clean_handle}"

    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        resp = await client.get(profile_url, headers=HEADERS)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    tweets = soup.select(".timeline-item")

    posts_found = len(tweets)
    posts_added = 0

    for tweet in tweets:
        content_el = tweet.select_one(".tweet-content")
        if not content_el:
            continue
        content = content_el.get_text(strip=True)

        date_el = tweet.select_one(".tweet-date a")
        tweet_url = ""
        posted_date = ""
        if date_el:
            posted_date = date_el.get("title", "")
            href = date_el.get("href", "")
            tweet_url = f"https://x.com{href}" if href else ""

        if not tweet_url:
            continue

        if repo.social_post_exists_url(tweet_url):
            continue

        image_url = ""
        img_el = tweet.select_one(
            ".tweet-body .still-image img, .tweet-body .attachment img"
        )
        if img_el:
            image_url = img_el.get("src", "")
            if image_url and not image_url.startswith("http"):
                image_url = f"{instance}{image_url}"

        repo.create_social_post(
            platform="twitter",
            original_url=tweet_url,
            author_handle=account["handle"],
            author_name=account.get("display_name") or "",
            content=content[:2000] if content else None,
            image_url=image_url or None,
            embed_html=None,
            posted_date=posted_date[:10] if posted_date else None,
            account_id=account["id"],
        )
        posts_added += 1

    return {"posts_found": posts_found, "posts_added": posts_added, "error": None}


# --- Threads ---

async def _crawl_threads_account(account: dict, repo: Repository,
                                 config: dict) -> dict:
    """Threads 계정은 자동 크롤링 미지원 — JS 렌더링 제한."""
    return {
        "posts_found": 0,
        "posts_added": 0,
        "error": "Threads는 자동 크롤링을 지원하지 않습니다. "
                 "소셜 포스트 > 일괄 URL 크롤링으로 개별 포스트 URL을 등록해주세요.",
    }


# --- Helpers ---

def _nitter_to_twitter_url(nitter_url: str) -> str:
    """Nitter URL을 Twitter/X URL로 변환한다."""
    for instance in NITTER_INSTANCES:
        domain = instance.replace("https://", "").replace("http://", "")
        if domain in nitter_url:
            return nitter_url.replace(domain, "x.com")
    return re.sub(r'https?://[^/]*nitter[^/]*', 'https://x.com', nitter_url)


def _parse_feed_date(entry) -> Optional[str]:
    """feedparser 엔트리에서 날짜를 추출한다."""
    for attr in ["published_parsed", "updated_parsed"]:
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                dt = datetime(*parsed[:6])
                return dt.strftime("%Y-%m-%d")
            except Exception:
                pass
    for attr in ["published", "updated"]:
        raw = entry.get(attr, "")
        if raw:
            return raw[:10]
    return None


def _extract_feed_image(entry) -> str:
    """feedparser 엔트리에서 이미지 URL을 추출한다."""
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url", "")
    if hasattr(entry, "media_content") and entry.media_content:
        for media in entry.media_content:
            if "image" in media.get("type", ""):
                return media.get("url", "")
    if entry.get("enclosures"):
        for enc in entry.enclosures:
            if "image" in enc.get("type", ""):
                return enc.get("href", "")
    content = entry.get("summary", "")
    if content and "<img" in content:
        soup = BeautifulSoup(content, "lxml")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]
    return ""
