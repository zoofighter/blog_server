"""RSS/Atom 피드 기반 블로그 크롤러.

등록된 블로그의 피드를 파싱하여 신규 포스트를 자동으로 수집·요약·분류한다.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

import feedparser
import httpx

from src.database.repository import Repository
from src.services.classifier import classify_category, extract_tags
from src.services.summarizer import summarize

logger = logging.getLogger(__name__)


async def crawl_blog(blog: dict, repo: Repository, config: dict) -> dict:
    """단일 블로그의 RSS 피드를 크롤링한다.

    Returns:
        {"posts_found": int, "posts_added": int, "error": str|None}
    """
    feed_url = blog.get("feed_url", "")
    blog_id = blog["id"]
    blog_name = blog.get("name", "")

    if not feed_url:
        return {"posts_found": 0, "posts_added": 0, "error": "피드 URL 없음"}

    try:
        feed_text = await _fetch_feed(feed_url)
        feed = feedparser.parse(feed_text)
    except Exception as e:
        error_msg = f"피드 가져오기 실패: {e}"
        logger.error("[%s] %s", blog_name, error_msg)
        return {"posts_found": 0, "posts_added": 0, "error": error_msg}

    if feed.bozo and not feed.entries:
        error_msg = f"피드 파싱 오류: {feed.bozo_exception}"
        logger.warning("[%s] %s", blog_name, error_msg)
        return {"posts_found": 0, "posts_added": 0, "error": error_msg}

    posts_found = len(feed.entries)
    posts_added = 0

    for entry in feed.entries:
        try:
            added = await _process_entry(entry, blog, repo, config)
            if added:
                posts_added += 1
        except Exception as e:
            logger.warning("[%s] 엔트리 처리 실패: %s", blog_name, e)
            continue

    logger.info("[%s] 크롤링 완료: %d건 발견, %d건 추가", blog_name, posts_found, posts_added)
    return {"posts_found": posts_found, "posts_added": posts_added, "error": None}


async def crawl_all_blogs(repo: Repository, config: dict) -> dict:
    """피드 URL이 있는 모든 활성 블로그를 크롤링한다.

    Returns:
        {"total_blogs": int, "total_found": int, "total_added": int, "errors": int}
    """
    blogs = repo.get_blogs_with_feed(active_only=True)
    logger.info("크롤링 시작: %d개 블로그", len(blogs))

    total_found = 0
    total_added = 0
    errors = 0

    for blog in blogs:
        result = await crawl_blog(blog, repo, config)

        # 크롤링 로그 기록
        status = "success" if result["error"] is None else "failed"
        repo.create_crawl_log(
            blog_id=blog["id"],
            status=status,
            posts_found=result["posts_found"],
            posts_added=result["posts_added"],
            error_message=result["error"],
        )
        repo.update_blog_crawl_status(blog["id"], error=result["error"])

        total_found += result["posts_found"]
        total_added += result["posts_added"]
        if result["error"]:
            errors += 1

        # 서버 부담 방지를 위한 딜레이
        await asyncio.sleep(1)

    logger.info(
        "크롤링 완료: %d개 블로그, %d건 발견, %d건 추가, %d건 오류",
        len(blogs), total_found, total_added, errors,
    )
    return {
        "total_blogs": len(blogs),
        "total_found": total_found,
        "total_added": total_added,
        "errors": errors,
    }


async def _fetch_feed(feed_url: str) -> str:
    """피드 URL의 내용을 가져온다."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BlogAggregator/1.0)"}
    async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
        resp = await client.get(feed_url, headers=headers)
        resp.raise_for_status()
        return resp.text


async def _process_entry(entry, blog: dict, repo: Repository, config: dict) -> bool:
    """피드 엔트리 하나를 처리하여 DB에 저장한다. 신규 저장 시 True 반환."""
    url = entry.get("link", "").strip()
    if not url:
        return False

    # 중복 확인
    if repo.post_exists_url(url):
        return False

    title = entry.get("title", "").strip()
    if not title:
        return False

    # 본문 추출
    content = ""
    if entry.get("content"):
        content = entry.content[0].get("value", "")
    elif entry.get("summary"):
        content = entry.summary
    elif entry.get("description"):
        content = entry.description

    # HTML 태그 제거 (간단히)
    from bs4 import BeautifulSoup
    if "<" in content:
        content = BeautifulSoup(content, "lxml").get_text(separator="\n", strip=True)

    # 발행일
    published_date = _parse_date(entry)

    # 이미지
    image_url = _extract_entry_image(entry)

    # 작성자
    author = ""
    if entry.get("author"):
        author = entry.author
    elif entry.get("authors"):
        author = entry.authors[0].get("name", "")

    # 카테고리 분류 + 태그 추출
    category = classify_category(title, content) if content else (blog.get("category") or "other")
    tags = extract_tags(title, content) if content else []

    # AI 요약 생성
    summary = ""
    summary_status = "pending"
    if content:
        try:
            summary = await summarize(title, content, config)
            summary_status = "completed" if summary else "failed"
        except Exception as e:
            logger.debug("요약 생성 실패 (%s): %s", title[:30], e)
            summary_status = "failed"

    # DB 저장
    post_id = repo.create_post(
        blog_id=blog["id"],
        title=title,
        original_url=url,
        summary=summary or None,
        full_content=content[:10000] if content else None,
        author=author or None,
        published_date=published_date,
        image_url=image_url or None,
        category=category,
        summary_status=summary_status,
        registered_by="auto",
    )

    if tags:
        repo.set_post_tags(post_id, tags)

    return True


def _parse_date(entry) -> Optional[str]:
    """피드 엔트리에서 발행일을 추출한다."""
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


def _extract_entry_image(entry) -> str:
    """피드 엔트리에서 대표 이미지를 추출한다."""
    # media:thumbnail
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url", "")

    # media:content
    if hasattr(entry, "media_content") and entry.media_content:
        for media in entry.media_content:
            if "image" in media.get("type", ""):
                return media.get("url", "")

    # enclosure
    if entry.get("enclosures"):
        for enc in entry.enclosures:
            if "image" in enc.get("type", ""):
                return enc.get("href", "")

    # 본문에서 첫 img 태그
    content = ""
    if entry.get("content"):
        content = entry.content[0].get("value", "")
    elif entry.get("summary"):
        content = entry.summary

    if content and "<img" in content:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, "lxml")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]

    return ""
