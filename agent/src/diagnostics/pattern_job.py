"""Low-resource periodic refresh job for persisted loss-pattern classifications."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from src.config.accessor import _parse_bool, get_env_or
from src.diagnostics.pattern_service import LossPatternDetectionService
from src.diagnostics.store import DiagnosticsStore

logger = logging.getLogger(__name__)

_DEFAULT_INTERVAL_SECONDS = 6 * 60 * 60
_task: asyncio.Task[None] | None = None
_stop_event: asyncio.Event | None = None


def _enabled() -> bool:
    raw = get_env_or(
        "VIBE_TRADING_DIAGNOSTICS_PATTERN_JOB_ENABLED", "", "true",
    )
    return _parse_bool(raw)


def _interval_seconds() -> int:
    raw = get_env_or(
        "VIBE_TRADING_DIAGNOSTICS_PATTERN_JOB_INTERVAL_SECONDS", "",
        str(_DEFAULT_INTERVAL_SECONDS),
    )
    try:
        return max(60, int(raw))
    except ValueError:
        logger.warning("Invalid diagnostics pattern job interval %r; using default", raw)
        return _DEFAULT_INTERVAL_SECONDS


def _month_period(now: datetime) -> tuple[str, str]:
    current = now.astimezone(timezone.utc)
    start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    end = next_month - timedelta(microseconds=1)
    return start.isoformat(), end.isoformat()


def run_pattern_refresh_once(*, now: datetime | None = None) -> dict[str, int]:
    """Refresh the current UTC month for every user that has at least one loss."""
    period_start, period_end = _month_period(now or datetime.now(timezone.utc))
    refreshed = 0
    failed = 0
    with DiagnosticsStore() as store:
        for user_id in store.loss_user_ids(period_start, period_end):
            try:
                LossPatternDetectionService(store).detect(user_id, period_start, period_end)
                refreshed += 1
            except Exception:
                failed += 1
                logger.exception("Loss-pattern refresh failed for user %s", user_id)
    return {"refreshed": refreshed, "failed": failed}


async def _run_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        result = await asyncio.to_thread(run_pattern_refresh_once)
        logger.info(
            "Loss-pattern refresh completed: refreshed=%d failed=%d",
            result["refreshed"], result["failed"],
        )
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=_interval_seconds())
        except TimeoutError:
            continue


def start_pattern_refresh_job() -> None:
    """Start the singleton refresh task when enabled."""
    global _task, _stop_event
    if not _enabled() or (_task is not None and not _task.done()):
        return
    _stop_event = asyncio.Event()
    _task = asyncio.create_task(_run_loop(_stop_event), name="diagnostics-pattern-refresh")


async def stop_pattern_refresh_job() -> None:
    """Signal and await the singleton refresh task."""
    global _task, _stop_event
    if _task is None:
        return
    if _stop_event is not None:
        _stop_event.set()
    await _task
    _task = None
    _stop_event = None