"""RSS 크롤링 스케줄러.

APScheduler를 사용하여 주기적으로 블로그 피드를 크롤링한다.
"""

import asyncio
import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.database.repository import Repository
from src.services.crawler import crawl_all_blogs
from src.services.social_crawler import crawl_all_social_accounts

logger = logging.getLogger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> Optional[AsyncIOScheduler]:
    return _scheduler


async def _run_crawl(repo: Repository, config: dict):
    """스케줄러에서 호출되는 크롤링 작업."""
    logger.info("스케줄 크롤링 시작")
    try:
        result = await crawl_all_blogs(repo, config)
        logger.info(
            "스케줄 크롤링 완료: %d블로그, +%d포스트, %d오류",
            result["total_blogs"], result["total_added"], result["errors"],
        )
    except Exception as e:
        logger.error("스케줄 크롤링 실패: %s", e)


async def _run_social_crawl(repo: Repository, config: dict):
    """스케줄러에서 호출되는 소셜 계정 크롤링 작업."""
    logger.info("소셜 스케줄 크롤링 시작")
    try:
        result = await crawl_all_social_accounts(repo, config)
        logger.info(
            "소셜 스케줄 크롤링 완료: %d계정, +%d포스트, %d오류",
            result["total_accounts"], result["total_added"], result["errors"],
        )
    except Exception as e:
        logger.error("소셜 스케줄 크롤링 실패: %s", e)


def start_scheduler(repo: Repository, config: dict) -> AsyncIOScheduler:
    """크롤링 스케줄러를 시작한다."""
    global _scheduler

    scheduler_config = config.get("scheduler", {})
    interval_hours = scheduler_config.get("interval_hours", 3)
    social_interval = scheduler_config.get("social_interval_hours", 6)
    enabled = scheduler_config.get("enabled", True)

    if not enabled:
        logger.info("스케줄러 비활성화됨 (config.scheduler.enabled = false)")
        return None

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _run_crawl,
        trigger=IntervalTrigger(hours=interval_hours),
        args=[repo, config],
        id="rss_crawl",
        name="RSS 피드 크롤링",
        max_instances=1,
        replace_existing=True,
    )
    _scheduler.add_job(
        _run_social_crawl,
        trigger=IntervalTrigger(hours=social_interval),
        args=[repo, config],
        id="social_crawl",
        name="소셜 계정 크롤링",
        max_instances=1,
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("크롤링 스케줄러 시작 (RSS: %d시간, 소셜: %d시간)",
                interval_hours, social_interval)
    return _scheduler


def reschedule_jobs(interval_hours: int = None, social_interval_hours: int = None) -> bool:
    """실행 중인 스케줄러의 크롤링 간격을 변경한다."""
    global _scheduler
    if not _scheduler or not _scheduler.running:
        return False

    if interval_hours is not None and interval_hours > 0:
        _scheduler.reschedule_job(
            "rss_crawl",
            trigger=IntervalTrigger(hours=interval_hours),
        )
        logger.info("RSS 크롤링 간격 변경: %d시간", interval_hours)

    if social_interval_hours is not None and social_interval_hours > 0:
        _scheduler.reschedule_job(
            "social_crawl",
            trigger=IntervalTrigger(hours=social_interval_hours),
        )
        logger.info("소셜 크롤링 간격 변경: %d시간", social_interval_hours)

    return True


def stop_scheduler():
    """스케줄러를 중지한다."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("크롤링 스케줄러 중지")
    _scheduler = None
