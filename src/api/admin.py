"""관리자 페이지 라우트 - 로그인, 대시보드, 포스트/블로그 CRUD."""

import asyncio
import csv
import io
import logging
import math
import os
from functools import wraps

from fastapi import APIRouter, Request, Form, Query, UploadFile, File
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse

from src.services.extractor import extract_metadata
from src.services.social_extractor import extract_social_metadata
from src.services.summarizer import summarize
from src.services.classifier import classify_category, extract_tags
from src.services.crawler import crawl_blog, crawl_all_blogs
from src.services.feed_finder import find_feed_url
from src.services.social_crawler import (
    crawl_social_account, crawl_all_social_accounts, build_nitter_rss_url,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_admin_password(config: dict) -> str:
    return os.environ.get("ADMIN_PASSWORD") or config.get("admin", {}).get("password", "admin")


def _is_authenticated(request: Request) -> bool:
    return request.session.get("authenticated") is True


# --- 인증 ---

@router.get("/login")
async def login_page(request: Request):
    if _is_authenticated(request):
        return RedirectResponse("/admin/", status_code=302)
    templates = request.app.state.templates
    return templates.TemplateResponse("admin/login.html", {"request": request})


@router.post("/login")
async def login(request: Request, password: str = Form(...)):
    config = request.app.state.config
    if password == _get_admin_password(config):
        request.session["authenticated"] = True
        return RedirectResponse("/admin/", status_code=302)
    templates = request.app.state.templates
    return templates.TemplateResponse("admin/login.html", {
        "request": request,
        "error": "비밀번호가 올바르지 않습니다.",
    })


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)


def require_auth(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not _is_authenticated(request):
            return RedirectResponse("/admin/login", status_code=302)
        return await func(request, *args, **kwargs)
    return wrapper


# --- 대시보드 ---

@router.get("/")
@require_auth
async def dashboard(request: Request):
    repo = request.app.state.repo
    templates = request.app.state.templates
    stats = repo.get_stats()
    crawl_stats = repo.get_crawl_stats()
    recent_logs = repo.get_crawl_logs(limit=10)
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "stats": stats,
        "crawl_stats": crawl_stats,
        "recent_logs": recent_logs,
    })


# --- 포스트 관리 ---

@router.get("/posts")
@require_auth
async def post_list(request: Request, page: int = Query(1, ge=1)):
    repo = request.app.state.repo
    templates = request.app.state.templates
    per_page = 20
    posts, total = repo.get_posts(page=page, per_page=per_page)
    for post in posts:
        post["tags"] = repo.get_post_tags(post["id"])

    total_pages = math.ceil(total / per_page) if total > 0 else 1
    return templates.TemplateResponse("admin/posts.html", {
        "request": request,
        "posts": posts,
        "total": total,
        "page": page,
        "total_pages": total_pages,
    })


@router.get("/posts/new")
@require_auth
async def post_form_new(request: Request):
    repo = request.app.state.repo
    templates = request.app.state.templates
    blogs = repo.get_all_blogs(active_only=True)
    categories = request.app.state.config.get("categories", [])
    return templates.TemplateResponse("admin/post_form.html", {
        "request": request,
        "post": None,
        "blogs": blogs,
        "categories": categories,
    })


@router.post("/posts/extract")
@require_auth
async def extract_url(request: Request):
    """URL에서 메타데이터를 추출한다 (AJAX)."""
    body = await request.json()
    url = body.get("url", "").strip()
    if not url:
        return JSONResponse({"error": "URL을 입력하세요."}, status_code=400)

    try:
        metadata = await extract_metadata(url)
        return JSONResponse(metadata)
    except Exception as e:
        logger.error("메타데이터 추출 실패: %s", e)
        return JSONResponse({"error": f"추출 실패: {e}"}, status_code=400)


@router.post("/posts/summarize")
@require_auth
async def summarize_content(request: Request):
    """본문을 AI로 요약한다 (AJAX)."""
    body = await request.json()
    title = body.get("title", "")
    content = body.get("content", "")
    if not content:
        return JSONResponse({"error": "본문이 없습니다."}, status_code=400)

    config = request.app.state.config
    summary = await summarize(title, content, config)
    return JSONResponse({"summary": summary})


@router.post("/posts")
@require_auth
async def create_post(
    request: Request,
    blog_id: int = Form(...),
    title: str = Form(...),
    original_url: str = Form(...),
    summary: str = Form(""),
    full_content: str = Form(""),
    author: str = Form(""),
    published_date: str = Form(""),
    image_url: str = Form(""),
    category: str = Form("other"),
    tags: str = Form(""),
):
    repo = request.app.state.repo

    if repo.post_exists_url(original_url):
        templates = request.app.state.templates
        blogs = repo.get_all_blogs(active_only=True)
        categories = request.app.state.config.get("categories", [])
        return templates.TemplateResponse("admin/post_form.html", {
            "request": request,
            "post": None,
            "blogs": blogs,
            "categories": categories,
            "error": "이미 등록된 URL입니다.",
        })

    summary_status = "completed" if summary else "pending"
    post_id = repo.create_post(
        blog_id=blog_id,
        title=title,
        original_url=original_url,
        summary=summary or None,
        full_content=full_content or None,
        author=author or None,
        published_date=published_date or None,
        image_url=image_url or None,
        category=category,
        summary_status=summary_status,
    )

    if tags.strip():
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        repo.set_post_tags(post_id, tag_list)

    return RedirectResponse("/admin/posts", status_code=302)


@router.get("/posts/{post_id}/edit")
@require_auth
async def post_form_edit(request: Request, post_id: int):
    repo = request.app.state.repo
    templates = request.app.state.templates
    post = repo.get_post(post_id)
    if not post:
        return RedirectResponse("/admin/posts", status_code=302)

    post["tags"] = repo.get_post_tags(post_id)
    blogs = repo.get_all_blogs(active_only=True)
    categories = request.app.state.config.get("categories", [])
    return templates.TemplateResponse("admin/post_form.html", {
        "request": request,
        "post": post,
        "blogs": blogs,
        "categories": categories,
    })


@router.post("/posts/{post_id}")
@require_auth
async def update_post(
    request: Request,
    post_id: int,
    blog_id: int = Form(...),
    title: str = Form(...),
    original_url: str = Form(...),
    summary: str = Form(""),
    full_content: str = Form(""),
    author: str = Form(""),
    published_date: str = Form(""),
    image_url: str = Form(""),
    category: str = Form("other"),
    tags: str = Form(""),
):
    repo = request.app.state.repo

    summary_status = "completed" if summary else "pending"
    repo.update_post(
        post_id,
        blog_id=blog_id,
        title=title,
        original_url=original_url,
        summary=summary or None,
        full_content=full_content or None,
        author=author or None,
        published_date=published_date or None,
        image_url=image_url or None,
        category=category,
        summary_status=summary_status,
    )

    if tags.strip():
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    else:
        tag_list = []
    repo.set_post_tags(post_id, tag_list)

    return RedirectResponse("/admin/posts", status_code=302)


@router.post("/posts/{post_id}/delete")
@require_auth
async def delete_post(request: Request, post_id: int):
    repo = request.app.state.repo
    repo.delete_post(post_id)
    return RedirectResponse("/admin/posts", status_code=302)


# --- 블로그 소스 관리 ---

@router.get("/blogs")
@require_auth
async def blog_list(request: Request):
    repo = request.app.state.repo
    templates = request.app.state.templates
    blogs = repo.get_all_blogs()
    post_counts = repo.get_blog_post_counts()
    for blog in blogs:
        blog["post_count"] = post_counts.get(blog["id"], 0)
    categories = request.app.state.config.get("categories", [])
    return templates.TemplateResponse("admin/blogs.html", {
        "request": request,
        "blogs": blogs,
        "categories": categories,
    })


@router.post("/blogs")
@require_auth
async def create_blog(
    request: Request,
    name: str = Form(...),
    url: str = Form(...),
    feed_url: str = Form(""),
    category: str = Form("other"),
    description: str = Form(""),
):
    repo = request.app.state.repo
    repo.create_blog(
        name=name,
        url=url,
        feed_url=feed_url or None,
        category=category,
        description=description or None,
    )
    return RedirectResponse("/admin/blogs", status_code=302)


@router.post("/blogs/{blog_id}/delete")
@require_auth
async def delete_blog(request: Request, blog_id: int):
    repo = request.app.state.repo
    repo.delete_blog(blog_id)
    return RedirectResponse("/admin/blogs", status_code=302)


@router.get("/blogs/export")
@require_auth
async def export_blogs(request: Request):
    """블로그 목록을 CSV로 내보내기."""
    repo = request.app.state.repo
    blogs = repo.get_all_blogs()

    output = io.StringIO()
    output.write("\ufeff")  # Excel UTF-8 BOM
    writer = csv.DictWriter(
        output,
        fieldnames=["name", "url", "feed_url", "category", "description"],
        extrasaction="ignore",
    )
    writer.writeheader()
    for blog in blogs:
        writer.writerow(blog)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=blogs.csv"},
    )


@router.post("/blogs/import")
@require_auth
async def import_blogs(request: Request, file: UploadFile = File(...)):
    """CSV 파일에서 블로그 목록을 가져오기."""
    repo = request.app.state.repo

    content = await file.read()
    text = content.decode("utf-8-sig")  # BOM 처리
    reader = csv.DictReader(io.StringIO(text))

    blogs = []
    for row in reader:
        name = row.get("name", "").strip()
        url = row.get("url", "").strip()
        if not name or not url:
            continue
        blogs.append({
            "name": name,
            "url": url,
            "feed_url": row.get("feed_url", "").strip(),
            "category": row.get("category", "").strip() or "other",
            "description": row.get("description", "").strip(),
        })

    count = repo.bulk_create_blogs(blogs)
    return RedirectResponse(
        f"/admin/blogs?imported={count}&skipped={len(blogs) - count}",
        status_code=302,
    )


@router.get("/blogs/template")
@require_auth
async def download_template(request: Request):
    """빈 CSV 템플릿 다운로드."""
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(["name", "url", "feed_url", "category", "description"])
    writer.writerow(["Example Blog", "https://blog.example.com", "https://blog.example.com/rss", "tech", "기술 블로그"])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=blogs_template.csv"},
    )


@router.post("/blogs/{blog_id}/toggle")
@require_auth
async def toggle_blog(request: Request, blog_id: int):
    repo = request.app.state.repo
    blog = repo.get_blog(blog_id)
    if blog:
        repo.update_blog(blog_id, active=0 if blog["active"] else 1)
    return RedirectResponse("/admin/blogs", status_code=302)


# --- 크롤링 관리 ---

@router.get("/crawl")
@require_auth
async def crawl_page(request: Request):
    """크롤링 관리 페이지."""
    repo = request.app.state.repo
    templates = request.app.state.templates
    blogs = repo.get_blogs_with_feed(active_only=False)
    post_counts = repo.get_blog_post_counts()
    for blog in blogs:
        blog["post_count"] = post_counts.get(blog["id"], 0)
    crawl_stats = repo.get_crawl_stats()
    recent_logs = repo.get_crawl_logs(limit=30)

    from src.scheduler import get_scheduler
    scheduler = get_scheduler()
    scheduler_running = scheduler is not None and scheduler.running if scheduler else False

    return templates.TemplateResponse("admin/crawl.html", {
        "request": request,
        "blogs": blogs,
        "crawl_stats": crawl_stats,
        "recent_logs": recent_logs,
        "scheduler_running": scheduler_running,
    })


@router.post("/crawl/all")
@require_auth
async def crawl_all(request: Request):
    """모든 활성 블로그를 즉시 크롤링한다."""
    repo = request.app.state.repo
    config = request.app.state.config
    result = await crawl_all_blogs(repo, config)
    return RedirectResponse(
        f"/admin/crawl?crawled={result['total_added']}&errors={result['errors']}",
        status_code=302,
    )


@router.post("/crawl/{blog_id}")
@require_auth
async def crawl_single(request: Request, blog_id: int):
    """단일 블로그를 즉시 크롤링한다."""
    repo = request.app.state.repo
    config = request.app.state.config
    blog = repo.get_blog(blog_id)
    if not blog:
        return RedirectResponse("/admin/crawl", status_code=302)

    result = await crawl_blog(blog, repo, config)

    status = "success" if result["error"] is None else "failed"
    repo.create_crawl_log(
        blog_id=blog_id,
        status=status,
        posts_found=result["posts_found"],
        posts_added=result["posts_added"],
        error_message=result["error"],
    )
    repo.update_blog_crawl_status(blog_id, error=result["error"])

    return RedirectResponse(
        f"/admin/crawl?crawled={result['posts_added']}&blog={blog['name']}",
        status_code=302,
    )


@router.post("/blogs/{blog_id}/find-feed")
@require_auth
async def find_blog_feed(request: Request, blog_id: int):
    """블로그의 RSS 피드 URL을 자동 탐색한다."""
    repo = request.app.state.repo
    blog = repo.get_blog(blog_id)
    if not blog:
        return JSONResponse({"error": "블로그를 찾을 수 없습니다."}, status_code=404)

    feed_url = await find_feed_url(blog["url"])
    if feed_url:
        repo.update_blog(blog_id, feed_url=feed_url)
        return JSONResponse({"feed_url": feed_url})
    else:
        return JSONResponse({"error": "피드 URL을 찾을 수 없습니다."}, status_code=404)


@router.post("/blogs/find-all-feeds")
@require_auth
async def find_all_feeds(request: Request):
    """피드 URL이 없는 모든 블로그의 피드를 탐색한다."""
    repo = request.app.state.repo
    blogs = repo.get_all_blogs(active_only=True)

    found = 0
    for blog in blogs:
        if blog.get("feed_url"):
            continue
        feed_url = await find_feed_url(blog["url"])
        if feed_url:
            repo.update_blog(blog["id"], feed_url=feed_url)
            found += 1

    return RedirectResponse(f"/admin/crawl?feeds_found={found}", status_code=302)


# --- 소셜 포스트 관리 ---

@router.get("/social")
@require_auth
async def social_post_list(request: Request, page: int = Query(1, ge=1)):
    repo = request.app.state.repo
    templates = request.app.state.templates
    per_page = 30
    posts, total = repo.get_social_posts(page=page, per_page=per_page)
    total_pages = math.ceil(total / per_page) if total > 0 else 1
    return templates.TemplateResponse("admin/social.html", {
        "request": request,
        "posts": posts,
        "total": total,
        "page": page,
        "total_pages": total_pages,
    })


@router.get("/social/new")
@require_auth
async def social_form_new(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse("admin/social_form.html", {
        "request": request,
    })


@router.post("/social/extract")
@require_auth
async def extract_social_url(request: Request):
    """소셜 포스트 URL에서 메타데이터를 추출한다 (AJAX)."""
    body = await request.json()
    url = body.get("url", "").strip()
    if not url:
        return JSONResponse({"error": "URL을 입력하세요."}, status_code=400)

    try:
        metadata = await extract_social_metadata(url)
        return JSONResponse(metadata)
    except Exception as e:
        logger.error("소셜 메타데이터 추출 실패: %s", e)
        return JSONResponse({"error": f"추출 실패: {e}"}, status_code=400)


@router.post("/social")
@require_auth
async def create_social_post(
    request: Request,
    platform: str = Form(...),
    original_url: str = Form(...),
    author_handle: str = Form(""),
    author_name: str = Form(""),
    content: str = Form(""),
    image_url: str = Form(""),
    embed_html: str = Form(""),
    posted_date: str = Form(""),
):
    repo = request.app.state.repo

    if repo.social_post_exists_url(original_url):
        templates = request.app.state.templates
        return templates.TemplateResponse("admin/social_form.html", {
            "request": request,
            "error": "이미 등록된 URL입니다.",
        })

    repo.create_social_post(
        platform=platform,
        original_url=original_url,
        author_handle=author_handle or None,
        author_name=author_name or None,
        content=content or None,
        image_url=image_url or None,
        embed_html=embed_html or None,
        posted_date=posted_date or None,
    )

    return RedirectResponse("/admin/social", status_code=302)


@router.post("/social/{post_id}/delete")
@require_auth
async def delete_social_post(request: Request, post_id: int):
    repo = request.app.state.repo
    repo.delete_social_post(post_id)
    return RedirectResponse("/admin/social", status_code=302)


@router.get("/social/export")
@require_auth
async def export_social_posts(request: Request):
    """소셜 포스트를 CSV로 내보내기."""
    repo = request.app.state.repo
    posts = repo.get_all_social_posts()

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.DictWriter(
        output,
        fieldnames=["platform", "original_url", "author_handle", "author_name",
                     "content", "image_url", "posted_date"],
        extrasaction="ignore",
    )
    writer.writeheader()
    for post in posts:
        writer.writerow(post)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=social_posts.csv"},
    )


@router.post("/social/import")
@require_auth
async def import_social_posts(request: Request, file: UploadFile = File(...)):
    """CSV 파일에서 소셜 포스트를 가져오기."""
    repo = request.app.state.repo

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    posts = []
    for row in reader:
        url = row.get("original_url", "").strip()
        platform = row.get("platform", "").strip()
        if not url or platform not in ("twitter", "threads"):
            continue
        posts.append({
            "platform": platform,
            "original_url": url,
            "author_handle": row.get("author_handle", "").strip(),
            "author_name": row.get("author_name", "").strip(),
            "content": row.get("content", "").strip(),
            "image_url": row.get("image_url", "").strip(),
            "posted_date": row.get("posted_date", "").strip(),
        })

    count = repo.bulk_create_social_posts(posts)
    return RedirectResponse(
        f"/admin/social?imported={count}&skipped={len(posts) - count}",
        status_code=302,
    )


@router.get("/social/template")
@require_auth
async def download_social_template(request: Request):
    """빈 소셜 포스트 CSV 템플릿 다운로드."""
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(["platform", "original_url", "author_handle", "author_name",
                      "content", "image_url", "posted_date"])
    writer.writerow(["twitter", "https://x.com/username/status/123456",
                      "@username", "Display Name", "트윗 내용", "", "2025-03-15"])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=social_posts_template.csv"},
    )


@router.post("/social/crawl")
@require_auth
async def crawl_social_urls(request: Request, urls: str = Form(...)):
    """URL 목록에서 메타데이터를 추출하여 일괄 등록한다."""
    repo = request.app.state.repo

    url_list = [u.strip() for u in urls.strip().splitlines() if u.strip()]
    added = 0
    errors = 0

    for url in url_list:
        if repo.social_post_exists_url(url):
            continue
        try:
            metadata = await extract_social_metadata(url)
            repo.create_social_post(
                platform=metadata["platform"],
                original_url=metadata["original_url"],
                author_handle=metadata.get("author_handle") or None,
                author_name=metadata.get("author_name") or None,
                content=metadata.get("content") or None,
                image_url=metadata.get("image_url") or None,
                embed_html=metadata.get("embed_html") or None,
                posted_date=metadata.get("posted_date") or None,
            )
            added += 1
        except Exception as e:
            logger.warning("소셜 크롤링 실패 [%s]: %s", url, e)
            errors += 1
        await asyncio.sleep(1)

    return RedirectResponse(
        f"/admin/social?crawled={added}&errors={errors}",
        status_code=302,
    )


# --- 소셜 계정 관리 ---

@router.get("/social-accounts")
@require_auth
async def social_account_list(request: Request):
    """소셜 계정 관리 + 크롤링 페이지."""
    repo = request.app.state.repo
    templates = request.app.state.templates
    accounts = repo.get_all_social_accounts()
    post_counts = repo.get_social_account_post_counts()
    for account in accounts:
        account["post_count"] = post_counts.get(account["id"], 0)
    crawl_stats = repo.get_social_crawl_stats()
    recent_logs = repo.get_social_crawl_logs(limit=30)
    return templates.TemplateResponse("admin/social_accounts.html", {
        "request": request,
        "accounts": accounts,
        "crawl_stats": crawl_stats,
        "recent_logs": recent_logs,
    })


@router.post("/social-accounts")
@require_auth
async def create_social_account_route(
    request: Request,
    platform: str = Form(...),
    handle: str = Form(...),
    display_name: str = Form(""),
    description: str = Form(""),
):
    """소셜 계정 등록."""
    repo = request.app.state.repo

    handle = handle.strip()
    if not handle.startswith("@"):
        handle = f"@{handle}"

    clean = handle.lstrip("@")
    if platform == "twitter":
        profile_url = f"https://x.com/{clean}"
        feed_url = build_nitter_rss_url(handle)
    else:
        profile_url = f"https://www.threads.net/@{clean}"
        feed_url = None

    if repo.social_account_exists(handle, platform):
        return RedirectResponse(
            "/admin/social-accounts?error=duplicate", status_code=302
        )

    repo.create_social_account(
        platform=platform,
        handle=handle,
        display_name=display_name or None,
        profile_url=profile_url,
        feed_url=feed_url,
        description=description or None,
    )
    return RedirectResponse("/admin/social-accounts", status_code=302)


@router.post("/social-accounts/{account_id}/toggle")
@require_auth
async def toggle_social_account(request: Request, account_id: int):
    repo = request.app.state.repo
    account = repo.get_social_account(account_id)
    if account:
        repo.update_social_account(
            account_id, active=0 if account["active"] else 1
        )
    return RedirectResponse("/admin/social-accounts", status_code=302)


@router.post("/social-accounts/{account_id}/delete")
@require_auth
async def delete_social_account_route(request: Request, account_id: int):
    repo = request.app.state.repo
    repo.delete_social_account(account_id)
    return RedirectResponse("/admin/social-accounts", status_code=302)


@router.post("/social-accounts/crawl/all")
@require_auth
async def crawl_all_social(request: Request):
    """모든 활성 소셜 계정을 즉시 크롤링한다."""
    repo = request.app.state.repo
    config = request.app.state.config
    result = await crawl_all_social_accounts(repo, config)
    return RedirectResponse(
        f"/admin/social-accounts?crawled={result['total_added']}"
        f"&errors={result['errors']}",
        status_code=302,
    )


@router.post("/social-accounts/{account_id}/crawl")
@require_auth
async def crawl_single_social(request: Request, account_id: int):
    """단일 소셜 계정을 즉시 크롤링한다."""
    repo = request.app.state.repo
    config = request.app.state.config
    account = repo.get_social_account(account_id)
    if not account:
        return RedirectResponse("/admin/social-accounts", status_code=302)

    result = await crawl_social_account(account, repo, config)

    status = "success" if result["error"] is None else "failed"
    repo.create_social_crawl_log(
        account_id=account_id,
        status=status,
        posts_found=result["posts_found"],
        posts_added=result["posts_added"],
        error_message=result["error"],
    )
    repo.update_social_account_crawl_status(account_id, error=result["error"])

    return RedirectResponse(
        f"/admin/social-accounts?crawled={result['posts_added']}"
        f"&account={account['handle']}",
        status_code=302,
    )


@router.get("/social-accounts/export")
@require_auth
async def export_social_accounts(request: Request):
    """소셜 계정을 CSV로 내보내기."""
    repo = request.app.state.repo
    accounts = repo.get_all_social_accounts()

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.DictWriter(
        output,
        fieldnames=["platform", "handle", "display_name", "description"],
        extrasaction="ignore",
    )
    writer.writeheader()
    for a in accounts:
        writer.writerow(a)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=social_accounts.csv"
        },
    )


@router.post("/social-accounts/import")
@require_auth
async def import_social_accounts(request: Request, file: UploadFile = File(...)):
    """CSV 파일에서 소셜 계정을 가져오기."""
    repo = request.app.state.repo

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    accounts = []
    for row in reader:
        handle = row.get("handle", "").strip()
        platform = row.get("platform", "").strip()
        if not handle or platform not in ("twitter", "threads"):
            continue
        if not handle.startswith("@"):
            handle = f"@{handle}"
        clean = handle.lstrip("@")
        if platform == "twitter":
            profile_url = f"https://x.com/{clean}"
            feed_url = f"https://nitter.net/{clean}/rss"
        else:
            profile_url = f"https://www.threads.net/@{clean}"
            feed_url = None
        accounts.append({
            "platform": platform,
            "handle": handle,
            "display_name": row.get("display_name", "").strip(),
            "profile_url": profile_url,
            "feed_url": feed_url,
            "description": row.get("description", "").strip(),
        })

    count = repo.bulk_create_social_accounts(accounts)
    return RedirectResponse(
        f"/admin/social-accounts?imported={count}&skipped={len(accounts) - count}",
        status_code=302,
    )


@router.get("/social-accounts/template")
@require_auth
async def download_social_accounts_template(request: Request):
    """빈 소셜 계정 CSV 템플릿 다운로드."""
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(["platform", "handle", "display_name", "description"])
    writer.writerow(["twitter", "@example", "Example User", "기술 트윗"])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=social_accounts_template.csv"
        },
    )
