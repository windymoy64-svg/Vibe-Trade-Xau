"""SQLite persistence for entry-time trade diagnostic snapshots."""

from __future__ import annotations

import sqlite3
import threading
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.config.accessor import get_env_or

_DEFAULT_DB_PATH = Path.home() / ".vibe-trading" / "diagnostics.db"
_SCHEMA_VERSION = 3


def _default_db_path() -> Path:
    configured = get_env_or("VIBE_TRADING_DIAGNOSTICS_DB_PATH", "").strip()
    return Path(configured).expanduser() if configured else _DEFAULT_DB_PATH


class DiagnosticsStore:
    """Own the diagnostics SQLite connection and its forward-only migrations."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else _default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._lock = threading.RLock()
        self._migrate()

    def _migrate(self) -> None:
        """Apply all pending schema migrations atomically and idempotently."""
        with self._lock:
            version = int(self._conn.execute("PRAGMA user_version").fetchone()[0])
            if version > _SCHEMA_VERSION:
                raise RuntimeError(
                    f"Diagnostics database schema {version} is newer than supported {_SCHEMA_VERSION}"
                )
            if version < 1:
                with self._conn:
                    self._conn.executescript(
                        """
                        CREATE TABLE diagnostic_trades (
                            id TEXT PRIMARY KEY,
                            user_id TEXT NOT NULL,
                            ticket_id TEXT NOT NULL,
                            pair TEXT NOT NULL DEFAULT 'XAUUSD',
                            direction TEXT NOT NULL CHECK(direction IN ('BUY', 'SELL')),
                            trend_status TEXT NOT NULL CHECK(trend_status IN ('BULLISH', 'BEARISH', 'FLAT')),
                            ema_alignment TEXT NOT NULL CHECK(ema_alignment IN ('BULLISH', 'BEARISH', 'MIXED')),
                            rsi_value REAL NOT NULL CHECK(rsi_value >= 0 AND rsi_value <= 100),
                            atr_value REAL NOT NULL CHECK(atr_value >= 0),
                            volume_status TEXT NOT NULL CHECK(volume_status IN ('NORMAL', 'HIGH', 'LOW')),
                            market_regime TEXT NOT NULL CHECK(market_regime IN ('TRENDING', 'RANGING', 'BREAKOUT')),
                            trading_session TEXT NOT NULL CHECK(trading_session IN ('ASIA', 'LONDON', 'NEW_YORK')),
                            result TEXT NOT NULL CHECK(result IN ('TP', 'SL')),
                            suspected_reason TEXT,
                            profit_loss REAL,
                            entry_time TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            UNIQUE(user_id, ticket_id)
                        );

                        CREATE INDEX idx_diagnostic_trades_user_entry
                            ON diagnostic_trades(user_id, entry_time DESC);
                        CREATE INDEX idx_diagnostic_trades_user_result
                            ON diagnostic_trades(user_id, result);
                        CREATE INDEX idx_diagnostic_trades_user_regime
                            ON diagnostic_trades(user_id, market_regime);
                        CREATE INDEX idx_diagnostic_trades_user_session
                            ON diagnostic_trades(user_id, trading_session);
                        CREATE INDEX idx_diagnostic_trades_user_reason
                            ON diagnostic_trades(user_id, suspected_reason)
                            WHERE suspected_reason IS NOT NULL;
                        """
                    )
                    self._conn.execute("PRAGMA user_version=1")
                    version = 1
            if version < 2:
                with self._conn:
                    self._conn.executescript(
                        """
                        ALTER TABLE diagnostic_trades ADD COLUMN entry_price REAL;
                        ALTER TABLE diagnostic_trades ADD COLUMN exit_price REAL;
                        ALTER TABLE diagnostic_trades ADD COLUMN exit_time TEXT;
                        ALTER TABLE diagnostic_trades ADD COLUMN updated_at TEXT;

                        CREATE INDEX idx_diagnostic_trades_user_pair_entry
                            ON diagnostic_trades(user_id, pair, entry_time DESC);
                        """
                    )
                    self._conn.execute(
                        "UPDATE diagnostic_trades SET updated_at = created_at WHERE updated_at IS NULL"
                    )
                    self._conn.execute("PRAGMA user_version=2")
                    version = 2
            if version < 3:
                with self._conn:
                    self._conn.executescript(
                        """
                        CREATE TABLE diagnostic_filter_presets (
                            id TEXT PRIMARY KEY,
                            user_id TEXT NOT NULL,
                            name TEXT NOT NULL,
                            criteria_json TEXT NOT NULL CHECK(json_valid(criteria_json)),
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            UNIQUE(user_id, name)
                        );
                        CREATE INDEX idx_diagnostic_filter_presets_user
                            ON diagnostic_filter_presets(user_id, updated_at DESC);
                        """
                    )
                    self._conn.execute("PRAGMA user_version=3")

    @property
    def schema_version(self) -> int:
        with self._lock:
            return int(self._conn.execute("PRAGMA user_version").fetchone()[0])

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def performance_summary(self, user_id: str) -> dict[str, int | float]:
        """Return the basic win/loss aggregate for one user."""
        with self._lock:
            row = self._conn.execute(
                """SELECT
                    COUNT(*) AS total_trades,
                    SUM(CASE WHEN result = 'TP' THEN 1 ELSE 0 END) AS winning_trades,
                    SUM(CASE WHEN result = 'SL' THEN 1 ELSE 0 END) AS losing_trades
                FROM diagnostic_trades
                WHERE user_id = ?""",
                (user_id,),
            ).fetchone()
        total = int(row["total_trades"] or 0)
        wins = int(row["winning_trades"] or 0)
        losses = int(row["losing_trades"] or 0)
        return {
            "totalTrades": total,
            "winningTrades": wins,
            "losingTrades": losses,
            "lossRate": round((losses / total) * 100, 2) if total else 0.0,
        }

    def cause_statistics(self, user_id: str) -> list[dict[str, int | float | str]]:
        """Return suspected loss causes ordered by frequency."""
        with self._lock:
            rows = self._conn.execute(
                """SELECT suspected_reason AS label, COUNT(*) AS loss_count
                FROM diagnostic_trades
                WHERE user_id = ? AND result = 'SL' AND suspected_reason IS NOT NULL
                    AND TRIM(suspected_reason) <> ''
                GROUP BY suspected_reason
                ORDER BY loss_count DESC, suspected_reason ASC""",
                (user_id,),
            ).fetchall()
            total_row = self._conn.execute(
                "SELECT COUNT(*) AS total FROM diagnostic_trades WHERE user_id = ? AND result = 'SL'",
                (user_id,),
            ).fetchone()
        total_losses = int(total_row["total"] or 0)
        return [
            {
                "label": str(row["label"]),
                "count": int(row["loss_count"]),
                "percentage": round((int(row["loss_count"]) / total_losses) * 100, 2)
                if total_losses else 0.0,
            }
            for row in rows
        ]

    def recent_trades(self, user_id: str, limit: int = 10) -> list[dict[str, object]]:
        """Return the most recent diagnostic snapshots for one user."""
        safe_limit = max(1, min(limit, 100))
        with self._lock:
            rows = self._conn.execute(
                """SELECT id, ticket_id, pair, direction, result, suspected_reason,
                    profit_loss, entry_time
                FROM diagnostic_trades
                WHERE user_id = ?
                ORDER BY entry_time DESC, id DESC
                LIMIT ?""",
                (user_id, safe_limit),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "ticketId": row["ticket_id"],
                "pair": row["pair"],
                "direction": row["direction"],
                "result": row["result"],
                "suspectedReason": row["suspected_reason"],
                "profitLoss": row["profit_loss"],
                "entryTime": row["entry_time"],
            }
            for row in rows
        ]

    def list_trades(
        self, user_id: str, *, search: str | None = None, pair: str | None = None,
        result: str | None = None, from_date: str | None = None,
        to_date: str | None = None, market_regime: str | None = None,
        trading_session: str | None = None, ema_alignment: str | None = None,
        min_rsi: float | None = None, max_rsi: float | None = None,
        min_atr: float | None = None, limit: int = 50, offset: int = 0,
    ) -> dict[str, object]:
        """List one user's trades with parameterized search filters and pagination."""
        clauses = ["user_id = ?"]
        params: list[object] = [user_id]
        if search:
            clauses.append("(ticket_id LIKE ? ESCAPE '\\' OR pair LIKE ? ESCAPE '\\' OR suspected_reason LIKE ? ESCAPE '\\')")
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            params.extend([f"%{escaped}%"] * 3)
        if pair:
            clauses.append("pair = ?")
            params.append(pair)
        if result:
            clauses.append("result = ?")
            params.append(result)
        if from_date:
            clauses.append("entry_time >= ?")
            params.append(from_date)
        if to_date:
            clauses.append("entry_time <= ?")
            params.append(to_date)
        for column, value in (("market_regime", market_regime), ("trading_session", trading_session), ("ema_alignment", ema_alignment)):
            if value:
                clauses.append(f"{column} = ?")
                params.append(value)
        if min_rsi is not None:
            clauses.append("rsi_value >= ?")
            params.append(min_rsi)
        if max_rsi is not None:
            clauses.append("rsi_value <= ?")
            params.append(max_rsi)
        if min_atr is not None:
            clauses.append("atr_value >= ?")
            params.append(min_atr)
        where = " AND ".join(clauses)
        safe_limit, safe_offset = max(1, min(limit, 200)), max(0, offset)
        with self._lock:
            total = int(self._conn.execute(
                f"SELECT COUNT(*) FROM diagnostic_trades WHERE {where}", params
            ).fetchone()[0])
            rows = self._conn.execute(
                f"""SELECT id, ticket_id, pair, entry_time, direction, result,
                    trend_status, ema_alignment, rsi_value, atr_value,
                    volume_status, market_regime, trading_session,
                    suspected_reason, profit_loss, entry_price, exit_price, exit_time
                FROM diagnostic_trades WHERE {where}
                ORDER BY entry_time DESC, id DESC LIMIT ? OFFSET ?""",
                [*params, safe_limit, safe_offset],
            ).fetchall()
        return {"items": [dict(row) for row in rows], "total": total, "limit": safe_limit, "offset": safe_offset}

    def get_trade(self, user_id: str, trade_id: str) -> dict[str, object] | None:
        """Return one trade only when it belongs to the requested user."""
        with self._lock:
            row = self._conn.execute(
                """SELECT id, user_id, ticket_id, pair, direction, trend_status,
                    ema_alignment, rsi_value, atr_value, volume_status,
                    market_regime, trading_session, result, suspected_reason,
                    profit_loss, entry_time, entry_price, exit_price, exit_time,
                    created_at, updated_at
                FROM diagnostic_trades WHERE id = ? AND user_id = ?""",
                (trade_id, user_id),
            ).fetchone()
        return dict(row) if row else None

    def get_trades_by_ids(self, user_id: str, trade_ids: list[str]) -> list[dict[str, object]]:
        """Return selected trades in request order while enforcing user ownership."""
        if not trade_ids:
            return []
        unique_ids = list(dict.fromkeys(trade_ids))[:100]
        placeholders = ",".join("?" for _ in unique_ids)
        with self._lock:
            rows = self._conn.execute(
                f"SELECT * FROM diagnostic_trades WHERE user_id = ? AND id IN ({placeholders})",
                [user_id, *unique_ids],
            ).fetchall()
        by_id = {str(row["id"]): dict(row) for row in rows}
        return [by_id[trade_id] for trade_id in unique_ids if trade_id in by_id]

    def save_filter_preset(self, user_id: str, name: str, criteria: dict[str, object]) -> dict[str, object]:
        """Create or replace a named filter preset for one user."""
        now = datetime.now(timezone.utc).isoformat()
        preset_id = f"filter_{uuid.uuid4().hex[:12]}"
        criteria_json = json.dumps(criteria, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT INTO diagnostic_filter_presets
                    (id, user_id, name, criteria_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, name) DO UPDATE SET
                    criteria_json=excluded.criteria_json, updated_at=excluded.updated_at""",
                (preset_id, user_id, name, criteria_json, now, now),
            )
            row = self._conn.execute(
                "SELECT * FROM diagnostic_filter_presets WHERE user_id=? AND name=?",
                (user_id, name),
            ).fetchone()
        payload = dict(row)
        payload["criteria"] = json.loads(str(payload.pop("criteria_json")))
        return payload

    def list_filter_presets(self, user_id: str) -> list[dict[str, object]]:
        """Return one user's saved presets, newest update first."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM diagnostic_filter_presets WHERE user_id=? ORDER BY updated_at DESC, name ASC",
                (user_id,),
            ).fetchall()
        presets: list[dict[str, object]] = []
        for row in rows:
            payload = dict(row)
            payload["criteria"] = json.loads(str(payload.pop("criteria_json")))
            presets.append(payload)
        return presets

    def delete_filter_preset(self, user_id: str, preset_id: str) -> bool:
        """Delete one preset only when it belongs to the requesting user."""
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "DELETE FROM diagnostic_filter_presets WHERE id=? AND user_id=?",
                (preset_id, user_id),
            )
        return cursor.rowcount == 1

    def quick_insight(self, user_id: str) -> dict[str, str | int | float] | None:
        """Return a deterministic insight from the dominant diagnosed loss."""
        causes = self.cause_statistics(user_id)
        if not causes:
            return None
        top = causes[0]
        return {
            "cause": str(top["label"]),
            "percentage": top["percentage"],
            "recommendation": (
                "Review the matching market-context filter before changing indicator parameters."
            ),
        }

    def __enter__(self) -> "DiagnosticsStore":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()