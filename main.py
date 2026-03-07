#!/usr/bin/env python3
"""블로그 애그리게이션 플랫폼 - 진입점"""

import uvicorn
import yaml

from src.api.app import create_app


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


config = load_config()
_fastapi_app = create_app(config)


async def app(scope, receive, send):
    """HEAD → GET 변환 래퍼. Nginx 헬스체크 호환."""
    if scope["type"] == "http" and scope["method"] == "HEAD":
        scope["method"] = "GET"
    await _fastapi_app(scope, receive, send)

if __name__ == "__main__":
    server = config.get("server", {})
    uvicorn.run(
        "main:app",
        host=server.get("host", "0.0.0.0"),
        port=server.get("port", 8000),
        reload=True,
    )
