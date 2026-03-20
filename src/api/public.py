"""공개 페이지 라우트 - 포스트 목록, 상세, 검색, RSS 피드."""

import math
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Query
from fastapi.responses import Response
from feedgen.feed import FeedGenerator

router = APIRouter()


@router.get("/")
async def index(
    request: Request,
    category: str = None,
    tag: str = None,
    search: str = None,
    page: int = Query(1, ge=1),
):
    repo = request.app.state.repo
    templates = request.app.state.templates
    per_page = 12

    posts, total = repo.get_posts(
        category=category, tag=tag, search=search, page=page, per_page=per_page
    )

    # 각 포스트에 태그 첨부
    for post in posts:
        post["tags"] = repo.get_post_tags(post["id"])

    total_pages = math.ceil(total / per_page) if total > 0 else 1
    categories = request.app.state.config.get("categories", [])

    return templates.TemplateResponse("index.html", {
        "request": request,
        "posts": posts,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "category": category,
        "tag": tag,
        "search": search or "",
        "categories": categories,
    })


@router.get("/social")
async def social_page(
    request: Request,
    platform: str = None,
    account_id: int = None,
    page: int = Query(1, ge=1),
):
    repo = request.app.state.repo
    templates = request.app.state.templates
    per_page = 30

    posts, total = repo.get_social_posts(
        platform=platform, account_id=account_id, page=page, per_page=per_page
    )
    total_pages = math.ceil(total / per_page) if total > 0 else 1
    accounts = repo.get_all_social_accounts(active_only=True)

    return templates.TemplateResponse("social.html", {
        "request": request,
        "posts": posts,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "platform": platform,
        "account_id": account_id,
        "accounts": accounts,
    })


@router.get("/post/{post_id}")
async def post_detail(request: Request, post_id: int):
    repo = request.app.state.repo
    templates = request.app.state.templates

    post = repo.get_post(post_id)
    if not post:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "posts": [],
            "total": 0,
            "page": 1,
            "total_pages": 1,
            "category": None,
            "tag": None,
            "search": "",
            "categories": [],
            "error": "포스트를 찾을 수 없습니다.",
        })

    post["tags"] = repo.get_post_tags(post_id)
    related = repo.get_related_posts(post_id, post.get("category", "other"))

    return templates.TemplateResponse("post_detail.html", {
        "request": request,
        "post": post,
        "related": related,
    })


def _parse_dt(date_str: str) -> datetime:
    """날짜 문자열을 timezone-aware datetime으로 변환."""
    if not date_str:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc)


@router.get("/feed")
async def rss_feed(request: Request, category: str = None):
    """블로그 포스트 RSS 피드 (최신 30건)."""
    repo = request.app.state.repo
    config = request.app.state.config
    site = config.get("site", {})
    base_url = site.get("url", "https://example.com").rstrip("/")

    fg = FeedGenerator()
    fg.title(site.get("title", "BlogAgg"))
    fg.link(href=base_url, rel="alternate")
    fg.link(href=f"{base_url}/feed", rel="self")
    fg.description(site.get("description", "Blog Aggregator"))
    fg.language("ko")

    posts, _ = repo.get_posts(category=category, page=1, per_page=30)
    for post in posts:
        fe = fg.add_entry()
        fe.id(post.get("original_url") or f"{base_url}/post/{post['id']}")
        fe.title(post.get("title", "Untitled"))
        fe.link(href=post.get("original_url") or f"{base_url}/post/{post['id']}")
        fe.published(_parse_dt(post.get("published_date", "")))
        fe.updated(_parse_dt(post.get("published_date", "")))
        if post.get("summary"):
            fe.summary(post["summary"])
        if post.get("author"):
            fe.author({"name": post["author"]})
        if post.get("category"):
            fe.category(term=post["category"])
        if post.get("image_url"):
            fe.enclosure(post["image_url"], 0, "image/jpeg")

    xml = fg.rss_str(pretty=True)
    return Response(content=xml, media_type="application/rss+xml; charset=utf-8")


@router.get("/feed/social")
async def rss_feed_social(request: Request, platform: str = None):
    """소셜 포스트 RSS 피드 (최신 30건)."""
    repo = request.app.state.repo
    config = request.app.state.config
    site = config.get("site", {})
    base_url = site.get("url", "https://example.com").rstrip("/")

    fg = FeedGenerator()
    fg.title(f"{site.get('title', 'BlogAgg')} · Social")
    fg.link(href=f"{base_url}/social", rel="alternate")
    fg.link(href=f"{base_url}/feed/social", rel="self")
    fg.description("Social posts feed")
    fg.language("ko")

    posts, _ = repo.get_social_posts(platform=platform, page=1, per_page=30)
    for post in posts:
        fe = fg.add_entry()
        fe.id(post.get("original_url", ""))
        title = f"{post.get('author_handle', '')} ({post.get('platform', '')})"
        fe.title(title)
        fe.link(href=post.get("original_url", ""))
        fe.published(_parse_dt(post.get("posted_date") or post.get("created_at", "")))
        fe.updated(_parse_dt(post.get("posted_date") or post.get("created_at", "")))
        if post.get("content"):
            fe.description(post["content"])
        if post.get("author_name"):
            fe.author({"name": post["author_name"]})

    xml = fg.rss_str(pretty=True)
    return Response(content=xml, media_type="application/rss+xml; charset=utf-8")
