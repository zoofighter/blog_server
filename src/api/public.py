"""공개 페이지 라우트 - 포스트 목록, 상세, 검색."""

import math

from fastapi import APIRouter, Request, Query

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
