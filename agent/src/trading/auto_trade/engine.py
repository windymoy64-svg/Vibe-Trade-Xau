"""Background Auto Trade bot for MT5 demo accounts.

The engine wraps the production deterministic forex runtime pipeline
(features -> signal -> decision -> risk -> executor). It runs as a daemon
thread, evaluates only CLOSED candles, and refuses to trade outside the
``paper`` MT5 profile. STOP halts new cycles; it never silently closes
positions (closing stays explicit and auditable).
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class AutoTradeBotEngine:
    """Daemon loop that runs one pipeline evaluation per new closed candle."""

    def __init__(
        self,
        *,
        symbol: str = "XAUUSD",
        timeframe: str = "M5",
        poll_interval_seconds: float = 5.0,
        max_spread: float = 40.0,
        bars_to_load: int = 260,
        runtime_root: str | Path | None = None,
    ) -> None:
        self.symbol = symbol.strip().upper()
        self.timeframe = timeframe.strip().upper()
        self.poll_interval_seconds = poll_interval_seconds
        self.max_spread = max_spread
        self.bars_to_load = bars_to_load
        root = Path(runtime_root or (Path.home() / ".vibe-trading"))
        self.event_log_path = root / "auto_trade_runtime" / f"{self.symbol}-{self.timeframe}.jsonl"
        self.event_log_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_cycle_at: str | None = None
        self._last_candle_id: str | None = None
        self._last_outcome: str | None = None
        self._last_message: str = "idle"
        self._cycles_processed = 0
        self._orders_placed = 0
        self._blocked_reason: str | None = None