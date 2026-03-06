#!/usr/bin/env python3
"""블로그 애그리게이션 플랫폼 - 진입점"""

import uvicorn
import yaml

from src.api.app import create_app


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


config = load_config()
app = create_app(config)

if __name__ == "__main__":
    server = config.get("server", {})
    uvicorn.run(
        "main:app",
        host=server.get("host", "0.0.0.0"),
        port=server.get("port", 8000),
        reload=True,
    )
