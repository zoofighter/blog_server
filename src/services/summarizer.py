"""AI 기반 블로그 포스트 요약 서비스.

지원 프로바이더: openai, claude, ollama, none
config.yaml의 llm.provider로 선택한다.
"""

import logging
import os

import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a blog post summarizer. "
    "Summarize the given blog post in 2-3 sentences. "
    "Keep technical terms. Focus on facts, not opinions. "
    "Respond in the same language as the original text."
)


async def summarize(title: str, content: str, config: dict) -> str:
    """블로그 포스트 본문을 2-3문장으로 요약한다."""
    llm_config = config.get("llm", {})
    provider = llm_config.get("provider", "none")

    if provider == "none":
        return _fallback_summary(content)

    truncated = content[:3000]
    user_msg = f"제목: {title}\n\n내용:\n{truncated}"

    try:
        if provider == "openai":
            return await _summarize_openai(user_msg, llm_config.get("openai", {}))
        elif provider == "claude":
            return await _summarize_claude(user_msg, llm_config.get("claude", {}))
        elif provider == "ollama":
            return await _summarize_ollama(user_msg, llm_config.get("ollama", {}))
        else:
            logger.warning("알 수 없는 LLM 프로바이더: %s", provider)
            return _fallback_summary(content)
    except Exception as e:
        logger.error("[%s] 요약 생성 실패: %s", provider, e)
        return _fallback_summary(content)


async def _summarize_openai(user_msg: str, cfg: dict) -> str:
    api_key = os.environ.get("OPENAI_API_KEY") or cfg.get("api_key")
    if not api_key:
        raise ValueError("OpenAI API 키 미설정")

    client = AsyncOpenAI(api_key=api_key)
    resp = await client.chat.completions.create(
        model=cfg.get("model", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=cfg.get("temperature", 0.3),
        max_tokens=cfg.get("max_tokens", 200),
    )
    return resp.choices[0].message.content.strip()


async def _summarize_claude(user_msg: str, cfg: dict) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY") or cfg.get("api_key")
    if not api_key:
        raise ValueError("Anthropic API 키 미설정")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": cfg.get("model", "claude-haiku-4-5-20251001"),
                "max_tokens": cfg.get("max_tokens", 200),
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_msg}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()


async def _summarize_ollama(user_msg: str, cfg: dict) -> str:
    base_url = cfg.get("base_url", "http://localhost:11434")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{base_url}/api/chat",
            json={
                "model": cfg.get("model", "llama3"),
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                "stream": False,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"].strip()


def _fallback_summary(content: str) -> str:
    """본문 첫 200자를 요약으로 사용한다."""
    text = content.strip()
    if len(text) <= 200:
        return text
    return text[:200] + "..."
