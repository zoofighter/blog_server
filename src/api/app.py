"""FastAPI 앱 생성 및 설정."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from src.database.models import get_db_path, init_db
from src.database.repository import Repository

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def create_app(config: dict) -> FastAPI:
    db_path = get_db_path(config)
    init_db(db_path)
    repo = Repository(db_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("블로그 애그리게이션 서버 시작")
        # 스케줄러 시작
        from src.scheduler import start_scheduler, stop_scheduler
        start_scheduler(repo, config)
        yield
        stop_scheduler()
        logger.info("서버 종료")

    app = FastAPI(
        title="Blog Aggregator",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    secret_key = os.environ.get("SECRET_KEY", "blog-aggregator-secret-key-change-me")
    app.add_middleware(SessionMiddleware, secret_key=secret_key)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    app.state.config = config
    app.state.repo = repo
    app.state.templates = templates

    from src.api.public import router as public_router
    from src.api.admin import router as admin_router

    app.include_router(public_router)
    app.include_router(admin_router, prefix="/admin")

    return app
