"""관리자 페이지 라우트 - 로그인, 대시보드, 포스트/블로그 CRUD."""

import csv
import io
import logging
import math
import os
from functools import wraps

from fastapi import APIRouter, Request, Form, Query, UploadFile, File
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse

from src.services.extractor import extract_metadata
from src.services.summarizer import summarize
from src.services.classifier import classify_category, extract_tags

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
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "stats": stats,
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
