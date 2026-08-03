"""SQLite persistence for entry-time trade diagnostic snapshots."""

from __future__ import annotations

import sqlite3
import threading
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.config.accessor import get_env_or

_DEFAULT_DB_PATH = Path.home() / ".vibe-trading" / "diagnostics.db"
_SCHEMA_VERSION = 14


@dataclass(frozen=True, slots=True)
class DiagnosticUser:
    """Typed representation of one persisted diagnostics account."""

    id: str
    email: str
    name: str
    password_hash: str
    role: str
    timezone: str
    trading_focus: str
    bio: str
    created_at: str
    updated_at: str
    last_active_at: str


@dataclass(frozen=True, slots=True)
class DiagnosticDataSource:
    """Typed metadata for one user's diagnostic evidence source."""

    id: str
    user_id: str
    name: str
    source_type: str
    description: str
    status: str
    last_sync_at: str | None
    imported_trades: int
    coverage_json: str
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class DiagnosticNotification:
    """Typed in-app diagnostic notification for one user."""

    id: str
    user_id: str
    notification_type: str
    title: str
    detail: str
    href: str
    is_read: bool
    read_at: str | None
    created_at: str
    updated_at: str


class EncryptedApiCredentialExistsError(RuntimeError):
    """Raised when creating a credential that already exists."""


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
                    version = 3
            if version < 4:
                with self._conn:
                    self._conn.executescript(
                        """
                        CREATE TABLE pola_kekalahan (
                            id TEXT PRIMARY KEY,
                            user_id TEXT NOT NULL,
                            name TEXT NOT NULL,
                            category TEXT NOT NULL
                                CHECK(category IN ('TREND', 'REGIME', 'SESSION', 'MOMENTUM')),
                            description TEXT NOT NULL,
                            loss_count INTEGER NOT NULL CHECK(loss_count >= 0),
                            loss_percentage REAL NOT NULL
                                CHECK(loss_percentage >= 0 AND loss_percentage <= 100),
                            confidence REAL NOT NULL
                                CHECK(confidence >= 0 AND confidence <= 100),
                            severity TEXT NOT NULL CHECK(severity IN ('HIGH', 'MEDIUM', 'LOW')),
                            evidence_trade_ids_json TEXT NOT NULL DEFAULT '[]'
                                CHECK(json_valid(evidence_trade_ids_json)
                                    AND json_type(evidence_trade_ids_json) = 'array'),
                            trend_delta REAL NOT NULL DEFAULT 0,
                            period_start TEXT NOT NULL,
                            period_end TEXT NOT NULL,
                            generated_at TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            CHECK(period_start <= period_end),
                            UNIQUE(user_id, name, period_start, period_end)
                        );

                        CREATE INDEX idx_pola_kekalahan_user_period
                            ON pola_kekalahan(user_id, period_end DESC, period_start DESC);
                        CREATE INDEX idx_pola_kekalahan_user_severity
                            ON pola_kekalahan(user_id, severity, loss_percentage DESC);
                        """
                    )
                    self._conn.execute("PRAGMA user_version=4")
                    version = 4
            if version < 5:
                with self._conn:
                    self._conn.executescript(
                        """
                        CREATE TABLE diagnostic_recommendation_statuses (
                            user_id TEXT NOT NULL,
                            recommendation_id TEXT NOT NULL,
                            status TEXT NOT NULL CHECK(status = 'APPLIED'),
                            applied_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            PRIMARY KEY(user_id, recommendation_id)
                        );

                        CREATE INDEX idx_recommendation_statuses_user_updated
                            ON diagnostic_recommendation_statuses(user_id, updated_at DESC);
                        """
                    )
                    self._conn.execute("PRAGMA user_version=5")
                    version = 5
            if version < 6:
                with self._conn:
                    self._conn.executescript(
                        """
                        CREATE TABLE diagnostic_recommendations (
                            id TEXT PRIMARY KEY,
                            user_id TEXT NOT NULL,
                            title TEXT NOT NULL,
                            summary TEXT NOT NULL,
                            action TEXT NOT NULL,
                            pattern_id TEXT NOT NULL,
                            pattern_name TEXT NOT NULL,
                            priority TEXT NOT NULL
                                CHECK(priority IN ('CRITICAL', 'HIGH', 'MEDIUM')),
                            status TEXT NOT NULL
                                CHECK(status IN ('READY', 'REVIEW', 'APPLIED')),
                            expected_impact REAL NOT NULL
                                CHECK(expected_impact >= 0 AND expected_impact <= 50),
                            evidence_losses INTEGER NOT NULL CHECK(evidence_losses >= 0),
                            confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 100),
                            effort TEXT NOT NULL CHECK(effort IN ('LOW', 'MEDIUM', 'HIGH')),
                            steps_json TEXT NOT NULL DEFAULT '[]'
                                CHECK(json_valid(steps_json) AND json_type(steps_json) = 'array'),
                            validation_target TEXT NOT NULL,
                            guardrail TEXT NOT NULL,
                            generated_at TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            UNIQUE(user_id, id)
                        );

                        CREATE INDEX idx_recommendations_user_priority
                            ON diagnostic_recommendations(user_id, priority, expected_impact DESC);
                        CREATE INDEX idx_recommendations_user_status
                            ON diagnostic_recommendations(user_id, status, updated_at DESC);
                        """
                    )
                    self._conn.execute("PRAGMA user_version=6")
                    version = 6
            if version < 7:
                with self._conn:
                    self._conn.executescript(
                        """
                        CREATE TABLE improvement_logs (
                            id TEXT PRIMARY KEY,
                            user_id TEXT NOT NULL,
                            recommendation_id TEXT NOT NULL,
                            title TEXT NOT NULL,
                            change_description TEXT NOT NULL,
                            status TEXT NOT NULL CHECK(status IN (
                                'PLANNED', 'APPLIED', 'MONITORING', 'VALIDATED'
                            )),
                            baseline_loss_rate REAL NOT NULL
                                CHECK(baseline_loss_rate >= 0 AND baseline_loss_rate <= 100),
                            target_loss_rate REAL NOT NULL
                                CHECK(target_loss_rate >= 0 AND target_loss_rate <= 100),
                            current_loss_rate REAL
                                CHECK(current_loss_rate IS NULL OR (
                                    current_loss_rate >= 0 AND current_loss_rate <= 100
                                )),
                            validation_start TEXT,
                            validation_end TEXT,
                            applied_at TEXT,
                            owner TEXT NOT NULL,
                            notes TEXT,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            CHECK(validation_start IS NULL OR validation_end IS NULL
                                OR validation_start <= validation_end),
                            UNIQUE(user_id, id)
                        );

                        CREATE INDEX idx_improvement_logs_user_status
                            ON improvement_logs(user_id, status, updated_at DESC);
                        CREATE INDEX idx_improvement_logs_user_applied
                            ON improvement_logs(user_id, applied_at DESC, created_at DESC);
                        CREATE INDEX idx_improvement_logs_user_recommendation
                            ON improvement_logs(user_id, recommendation_id, updated_at DESC);
                        """
                    )
                    self._conn.execute("PRAGMA user_version=7")
                    version = 7
            if version < 8:
                with self._conn:
                    self._conn.executescript(
                        """
                        CREATE TABLE users (
                            id TEXT PRIMARY KEY CHECK(length(trim(id)) BETWEEN 1 AND 128),
                            email TEXT NOT NULL COLLATE NOCASE UNIQUE
                                CHECK(length(trim(email)) BETWEEN 3 AND 254
                                    AND instr(email, '@') > 1),
                            name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 2 AND 120),
                            password_hash TEXT NOT NULL CHECK(length(password_hash) BETWEEN 32 AND 512),
                            role TEXT NOT NULL DEFAULT '' CHECK(length(role) <= 120),
                            timezone TEXT NOT NULL DEFAULT 'UTC'
                                CHECK(length(trim(timezone)) BETWEEN 1 AND 64),
                            trading_focus TEXT NOT NULL DEFAULT '' CHECK(length(trading_focus) <= 120),
                            bio TEXT NOT NULL DEFAULT '' CHECK(length(bio) <= 240),
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            last_active_at TEXT NOT NULL
                        );

                        CREATE INDEX idx_users_updated_at
                            ON users(updated_at DESC, id);
                        """
                    )
                    self._conn.execute("PRAGMA user_version=8")
                    version = 8
            if version < 9:
                with self._conn:
                    self._conn.executescript(
                        """
                        CREATE TABLE data_sources (
                            id TEXT NOT NULL CHECK(length(trim(id)) BETWEEN 1 AND 128),
                            user_id TEXT NOT NULL,
                            name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 120),
                            source_type TEXT NOT NULL
                                CHECK(length(trim(source_type)) BETWEEN 1 AND 80),
                            description TEXT NOT NULL DEFAULT '' CHECK(length(description) <= 500),
                            status TEXT NOT NULL CHECK(status IN (
                                'CONNECTED', 'AVAILABLE', 'ATTENTION'
                            )),
                            last_sync_at TEXT,
                            imported_trades INTEGER NOT NULL DEFAULT 0
                                CHECK(imported_trades >= 0),
                            coverage_json TEXT NOT NULL DEFAULT '[]'
                                CHECK(json_valid(coverage_json)
                                    AND json_type(coverage_json) = 'array'),
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            PRIMARY KEY(user_id, id),
                            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                        );

                        CREATE INDEX idx_data_sources_user_status
                            ON data_sources(user_id, status, updated_at DESC);
                        CREATE INDEX idx_data_sources_user_sync
                            ON data_sources(user_id, last_sync_at DESC);
                        """
                    )
                    self._conn.execute("PRAGMA user_version=9")
                    version = 9
            if version < 10:
                with self._conn:
                    self._conn.executescript(
                        """
                        CREATE TABLE notifications (
                            id TEXT NOT NULL CHECK(length(trim(id)) BETWEEN 1 AND 128),
                            user_id TEXT NOT NULL,
                            notification_type TEXT NOT NULL CHECK(notification_type IN (
                                'PATTERN', 'RECOMMENDATION', 'VALIDATION'
                            )),
                            title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 160),
                            detail TEXT NOT NULL CHECK(length(trim(detail)) BETWEEN 1 AND 1000),
                            href TEXT NOT NULL CHECK(
                                length(href) BETWEEN 1 AND 500
                                AND substr(href, 1, 1) = '/'
                                AND substr(href, 1, 2) <> '//'
                            ),
                            is_read INTEGER NOT NULL DEFAULT 0 CHECK(is_read IN (0, 1)),
                            read_at TEXT,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            PRIMARY KEY(user_id, id),
                            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                            CHECK((is_read = 0 AND read_at IS NULL)
                                OR (is_read = 1 AND read_at IS NOT NULL))
                        );

                        CREATE INDEX idx_notifications_user_created
                            ON notifications(user_id, created_at DESC, id);
                        CREATE INDEX idx_notifications_user_unread
                            ON notifications(user_id, is_read, created_at DESC);
                        """
                    )
                    self._conn.execute("PRAGMA user_version=10")
                    version = 10
            if version < 11:
                with self._conn:
                    self._conn.executescript(
                        """
                        CREATE TABLE notification_preferences (
                            user_id TEXT PRIMARY KEY,
                            in_app INTEGER NOT NULL DEFAULT 1 CHECK(in_app IN (0, 1)),
                            email INTEGER NOT NULL DEFAULT 1 CHECK(email IN (0, 1)),
                            mobile INTEGER NOT NULL DEFAULT 0 CHECK(mobile IN (0, 1)),
                            critical_patterns INTEGER NOT NULL DEFAULT 1 CHECK(critical_patterns IN (0, 1)),
                            recommendations INTEGER NOT NULL DEFAULT 1 CHECK(recommendations IN (0, 1)),
                            validation_results INTEGER NOT NULL DEFAULT 1 CHECK(validation_results IN (0, 1)),
                            source_health INTEGER NOT NULL DEFAULT 1 CHECK(source_health IN (0, 1)),
                            weekly_digest INTEGER NOT NULL DEFAULT 0 CHECK(weekly_digest IN (0, 1)),
                            quiet_hours INTEGER NOT NULL DEFAULT 1 CHECK(quiet_hours IN (0, 1)),
                            quiet_start TEXT NOT NULL DEFAULT '22:00'
                                CHECK(quiet_start GLOB '[0-2][0-9]:[0-5][0-9]'
                                    AND CAST(substr(quiet_start, 1, 2) AS INTEGER) <= 23),
                            quiet_end TEXT NOT NULL DEFAULT '07:00'
                                CHECK(quiet_end GLOB '[0-2][0-9]:[0-5][0-9]'
                                    AND CAST(substr(quiet_end, 1, 2) AS INTEGER) <= 23),
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                        );
                        """
                    )
                    self._conn.execute("PRAGMA user_version=11")
                    version = 11
            if version < 12:
                with self._conn:
                    self._conn.executescript(
                        """
                        CREATE TABLE encrypted_api_credentials (
                            user_id TEXT NOT NULL,
                            provider TEXT NOT NULL
                                CHECK(length(trim(provider)) BETWEEN 1 AND 64),
                            ciphertext BLOB NOT NULL CHECK(length(ciphertext) >= 16),
                            nonce BLOB NOT NULL CHECK(length(nonce) >= 12),
                            key_version INTEGER NOT NULL DEFAULT 1 CHECK(key_version > 0),
                            last_four TEXT NOT NULL
                                CHECK(length(last_four) = 4 AND last_four NOT GLOB '*[^A-Za-z0-9]*'),
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            PRIMARY KEY(user_id, provider),
                            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                        );

                        CREATE INDEX idx_encrypted_api_credentials_user_updated
                            ON encrypted_api_credentials(user_id, updated_at DESC);
                        """
                    )
                    self._conn.execute("PRAGMA user_version=12")
                    version = 12
            if version < 13:
                with self._conn:
                    self._conn.executescript(
                        """
                        CREATE TABLE auto_trade_execution_logs (
                            id TEXT NOT NULL CHECK(length(trim(id)) BETWEEN 1 AND 128),
                            user_id TEXT NOT NULL,
                            level TEXT NOT NULL CHECK(level IN ('INFO', 'SIGNAL', 'RISK', 'ERROR')),
                            status TEXT NOT NULL CHECK(status IN (
                                'MONITORING', 'PENDING', 'EXECUTED', 'REJECTED', 'CLOSED', 'FAILED'
                            )),
                            message TEXT NOT NULL CHECK(length(trim(message)) BETWEEN 1 AND 1000),
                            symbol TEXT CHECK(symbol IS NULL OR length(trim(symbol)) BETWEEN 1 AND 32),
                            direction TEXT CHECK(direction IS NULL OR direction IN ('BUY', 'SELL')),
                            strategy_id TEXT,
                            lot_size REAL CHECK(lot_size IS NULL OR lot_size > 0),
                            entry_price REAL CHECK(entry_price IS NULL OR entry_price > 0),
                            stop_loss REAL CHECK(stop_loss IS NULL OR stop_loss > 0),
                            take_profit REAL CHECK(take_profit IS NULL OR take_profit > 0),
                            broker_order_id TEXT,
                            error_code TEXT,
                            metadata_json TEXT NOT NULL DEFAULT '{}'
                                CHECK(json_valid(metadata_json) AND json_type(metadata_json) = 'object'),
                            occurred_at TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            PRIMARY KEY(user_id, id),
                            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                        );

                        CREATE INDEX idx_auto_trade_execution_logs_user_time
                            ON auto_trade_execution_logs(user_id, occurred_at DESC, id);
                        CREATE INDEX idx_auto_trade_execution_logs_user_status
                            ON auto_trade_execution_logs(user_id, status, occurred_at DESC);
                        """
                    )
                    self._conn.execute("PRAGMA user_version=13")
                    version = 13
            if version < 14:
                with self._conn:
                    self._conn.executescript(
                        """
                        CREATE TABLE auto_trade_configurations (
                            id TEXT NOT NULL CHECK(length(trim(id)) BETWEEN 1 AND 128),
                            user_id TEXT NOT NULL,
                            symbol TEXT NOT NULL
                                CHECK(length(trim(symbol)) BETWEEN 1 AND 32),
                            timeframe TEXT NOT NULL
                                CHECK(length(trim(timeframe)) BETWEEN 1 AND 16),
                            strategy TEXT NOT NULL
                                CHECK(length(trim(strategy)) BETWEEN 1 AND 160),
                            risk_per_trade REAL NOT NULL
                                CHECK(risk_per_trade >= 0.01 AND risk_per_trade <= 5),
                            daily_loss_limit REAL NOT NULL
                                CHECK(daily_loss_limit >= 0.1 AND daily_loss_limit <= 20),
                            paper_mode INTEGER NOT NULL CHECK(paper_mode IN (0, 1)),
                            robot_enabled INTEGER NOT NULL CHECK(robot_enabled IN (0, 1)),
                            lot_size REAL NOT NULL CHECK(lot_size >= 0.01 AND lot_size <= 1),
                            stop_loss_pips REAL NOT NULL
                                CHECK(stop_loss_pips >= 5 AND stop_loss_pips <= 250),
                            take_profit_pips REAL NOT NULL
                                CHECK(take_profit_pips >= 10 AND take_profit_pips <= 500),
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            PRIMARY KEY(user_id, id),
                            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                        );

                        CREATE INDEX idx_auto_trade_configurations_user_updated
                            ON auto_trade_configurations(user_id, updated_at DESC, id);
                        """
                    )
                    self._conn.execute("PRAGMA user_version=14")

    @property
    def schema_version(self) -> int:
        with self._lock:
            return int(self._conn.execute("PRAGMA user_version").fetchone()[0])

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @staticmethod
    def _auto_trade_configuration(row: sqlite3.Row) -> dict[str, object]:
        return {
            "id": str(row["id"]),
            "userId": str(row["user_id"]),
            "symbol": str(row["symbol"]),
            "timeframe": str(row["timeframe"]),
            "strategy": str(row["strategy"]),
            "riskPerTrade": float(row["risk_per_trade"]),
            "dailyLossLimit": float(row["daily_loss_limit"]),
            "paperMode": bool(row["paper_mode"]),
            "robotControls": {
                "enabled": bool(row["robot_enabled"]),
                "lotSize": float(row["lot_size"]),
                "stopLossPips": float(row["stop_loss_pips"]),
                "takeProfitPips": float(row["take_profit_pips"]),
            },
            "createdAt": str(row["created_at"]),
            "updatedAt": str(row["updated_at"]),
        }

    def create_auto_trade_configuration(
        self, user_id: str, values: dict[str, object],
    ) -> dict[str, object] | None:
        """Create a durable auto-trade configuration for an existing user."""
        config_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        controls = values["robotControls"]
        assert isinstance(controls, dict)
        with self._lock, self._conn:
            if self._conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
                return None
            self._conn.execute(
                """INSERT INTO auto_trade_configurations (
                    id, user_id, symbol, timeframe, strategy, risk_per_trade,
                    daily_loss_limit, paper_mode, robot_enabled, lot_size,
                    stop_loss_pips, take_profit_pips, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    config_id, user_id, values["symbol"], values["timeframe"],
                    values["strategy"], values["riskPerTrade"], values["dailyLossLimit"],
                    int(bool(values["paperMode"])), int(bool(controls["enabled"])),
                    controls["lotSize"], controls["stopLossPips"],
                    controls["takeProfitPips"], now, now,
                ),
            )
            row = self._conn.execute(
                "SELECT * FROM auto_trade_configurations WHERE user_id = ? AND id = ?",
                (user_id, config_id),
            ).fetchone()
        return self._auto_trade_configuration(row)

    def list_auto_trade_configurations(self, user_id: str) -> list[dict[str, object]]:
        """List configurations owned by one user, newest first."""
        with self._lock:
            rows = self._conn.execute(
                """SELECT * FROM auto_trade_configurations WHERE user_id = ?
                    ORDER BY updated_at DESC, id ASC""",
                (user_id,),
            ).fetchall()
        return [self._auto_trade_configuration(row) for row in rows]

    def get_auto_trade_configuration(
        self, user_id: str, config_id: str,
    ) -> dict[str, object] | None:
        """Return a configuration only when it belongs to the user."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM auto_trade_configurations WHERE user_id = ? AND id = ?",
                (user_id, config_id),
            ).fetchone()
        return self._auto_trade_configuration(row) if row else None

    def update_auto_trade_configuration(
        self, user_id: str, config_id: str, values: dict[str, object],
    ) -> dict[str, object] | None:
        """Replace a user-owned configuration, preserving its creation timestamp."""
        controls = values["robotControls"]
        assert isinstance(controls, dict)
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """UPDATE auto_trade_configurations SET
                    symbol = ?, timeframe = ?, strategy = ?, risk_per_trade = ?,
                    daily_loss_limit = ?, paper_mode = ?, robot_enabled = ?, lot_size = ?,
                    stop_loss_pips = ?, take_profit_pips = ?, updated_at = ?
                    WHERE user_id = ? AND id = ?""",
                (
                    values["symbol"], values["timeframe"], values["strategy"],
                    values["riskPerTrade"], values["dailyLossLimit"],
                    int(bool(values["paperMode"])), int(bool(controls["enabled"])),
                    controls["lotSize"], controls["stopLossPips"],
                    controls["takeProfitPips"], now, user_id, config_id,
                ),
            )
            if cursor.rowcount == 0:
                return None
            row = self._conn.execute(
                "SELECT * FROM auto_trade_configurations WHERE user_id = ? AND id = ?",
                (user_id, config_id),
            ).fetchone()
        return self._auto_trade_configuration(row)

    def delete_auto_trade_configuration(self, user_id: str, config_id: str) -> bool:
        """Delete a configuration only when it belongs to the user."""
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "DELETE FROM auto_trade_configurations WHERE user_id = ? AND id = ?",
                (user_id, config_id),
            )
        return cursor.rowcount > 0

    @staticmethod
    def _encrypted_api_credential_metadata(row: sqlite3.Row) -> dict[str, object]:
        return {
            "provider": str(row["provider"]),
            "lastFour": str(row["last_four"]),
            "keyVersion": int(row["key_version"]),
            "createdAt": str(row["created_at"]),
            "updatedAt": str(row["updated_at"]),
        }

    def create_encrypted_api_credential(
        self,
        user_id: str,
        provider: str,
        ciphertext: bytes,
        nonce: bytes,
        last_four: str,
    ) -> dict[str, object] | None:
        """Create encrypted credential metadata for an existing user."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self._lock, self._conn:
            if self._conn.execute(
                "SELECT 1 FROM users WHERE id = ?", (user_id,)
            ).fetchone() is None:
                return None
            try:
                self._conn.execute(
                    """INSERT INTO encrypted_api_credentials (
                        user_id, provider, ciphertext, nonce, key_version, last_four,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 1, ?, ?, ?)""",
                    (user_id, provider, ciphertext, nonce, last_four, now, now),
                )
            except sqlite3.IntegrityError as exc:
                if self._conn.execute(
                    """SELECT 1 FROM encrypted_api_credentials
                        WHERE user_id = ? AND provider = ?""",
                    (user_id, provider),
                ).fetchone() is not None:
                    raise EncryptedApiCredentialExistsError(provider) from exc
                raise
            row = self._conn.execute(
                """SELECT provider, last_four, key_version, created_at, updated_at
                    FROM encrypted_api_credentials WHERE user_id = ? AND provider = ?""",
                (user_id, provider),
            ).fetchone()
        return self._encrypted_api_credential_metadata(row)

    def update_encrypted_api_credential(
        self,
        user_id: str,
        provider: str,
        ciphertext: bytes,
        nonce: bytes,
        last_four: str,
    ) -> dict[str, object] | None:
        """Replace encrypted material while preserving its key version."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """UPDATE encrypted_api_credentials
                    SET ciphertext = ?, nonce = ?, last_four = ?, updated_at = ?
                    WHERE user_id = ? AND provider = ?""",
                (ciphertext, nonce, last_four, now, user_id, provider),
            )
            if cursor.rowcount == 0:
                return None
            row = self._conn.execute(
                """SELECT provider, last_four, key_version, created_at, updated_at
                    FROM encrypted_api_credentials WHERE user_id = ? AND provider = ?""",
                (user_id, provider),
            ).fetchone()
        return self._encrypted_api_credential_metadata(row)

    def rotate_encrypted_api_credential(
        self,
        user_id: str,
        provider: str,
        ciphertext: bytes,
        nonce: bytes,
        last_four: str,
    ) -> dict[str, object] | None:
        """Atomically replace encrypted material and increment its key version."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """UPDATE encrypted_api_credentials
                    SET ciphertext = ?, nonce = ?, last_four = ?,
                        key_version = key_version + 1, updated_at = ?
                    WHERE user_id = ? AND provider = ?""",
                (ciphertext, nonce, last_four, now, user_id, provider),
            )
            if cursor.rowcount == 0:
                return None
            row = self._conn.execute(
                """SELECT provider, last_four, key_version, created_at, updated_at
                    FROM encrypted_api_credentials WHERE user_id = ? AND provider = ?""",
                (user_id, provider),
            ).fetchone()
        return self._encrypted_api_credential_metadata(row)

    def get_encrypted_api_credential(
        self, user_id: str, provider: str,
    ) -> dict[str, object] | None:
        """Return encrypted credential material for internal broker services only."""
        with self._lock:
            row = self._conn.execute(
                """SELECT provider, ciphertext, nonce, key_version, last_four
                    FROM encrypted_api_credentials WHERE user_id = ? AND provider = ?""",
                (user_id, provider),
            ).fetchone()
        if row is None:
            return None
        return {
            "provider": str(row["provider"]),
            "ciphertext": bytes(row["ciphertext"]),
            "nonce": bytes(row["nonce"]),
            "keyVersion": int(row["key_version"]),
            "lastFour": str(row["last_four"]),
        }

    def append_auto_trade_execution_log(
        self, user_id: str, values: dict[str, object],
    ) -> dict[str, object] | None:
        """Append one immutable execution event for an existing user."""
        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self._lock, self._conn:
            if self._conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
                return None
            self._conn.execute(
                """INSERT INTO auto_trade_execution_logs (
                    id, user_id, level, status, message, symbol, direction,
                    strategy_id, lot_size, entry_price, stop_loss, take_profit,
                    broker_order_id, error_code, occurred_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    values["id"], user_id, values["level"], values["status"],
                    values["message"], values.get("symbol"), values.get("direction"),
                    values.get("strategyId"), values.get("lotSize"), values.get("price"),
                    values.get("stopLoss"), values.get("takeProfit"),
                    values.get("brokerOrderId"), values.get("errorCode"),
                    values["timestamp"], created_at,
                ),
            )
        return {**values, "userId": user_id, "createdAt": created_at}

    def auto_trade_execution_logs(
        self,
        user_id: str,
        *,
        status: str | None = None,
        level: str | None = None,
        symbol: str | None = None,
        direction: str | None = None,
        start: str | None = None,
        end: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        """Return filtered execution audit events for one user."""
        clauses = ["user_id = ?"]
        parameters: list[object] = [user_id]
        for column, value in (
            ("status", status), ("level", level), ("symbol", symbol), ("direction", direction),
        ):
            if value is not None:
                clauses.append(f"{column} = ?")
                parameters.append(value)
        if start is not None:
            clauses.append("occurred_at >= ?")
            parameters.append(start)
        if end is not None:
            clauses.append("occurred_at <= ?")
            parameters.append(end)
        parameters.append(limit)
        with self._lock:
            rows = self._conn.execute(
                f"""SELECT * FROM auto_trade_execution_logs
                    WHERE {' AND '.join(clauses)}
                    ORDER BY occurred_at DESC, id ASC LIMIT ?""",
                parameters,
            ).fetchall()
        return [
            {
                "id": str(row["id"]), "level": str(row["level"]),
                "status": str(row["status"]), "message": str(row["message"]),
                "symbol": row["symbol"], "direction": row["direction"],
                "strategyId": row["strategy_id"], "lotSize": row["lot_size"],
                "price": row["entry_price"], "stopLoss": row["stop_loss"],
                "takeProfit": row["take_profit"], "brokerOrderId": row["broker_order_id"],
                "errorCode": row["error_code"], "timestamp": str(row["occurred_at"]),
            }
            for row in rows
        ]

    def notification_preferences(self, user_id: str) -> dict[str, object] | None:
        """Return persisted preferences or frontend-compatible defaults for an existing user."""
        defaults: dict[str, object] = {
            "inApp": True, "email": True, "mobile": False,
            "criticalPatterns": True, "recommendations": True,
            "validationResults": True, "sourceHealth": True,
            "weeklyDigest": False, "quietHours": True,
            "quietStart": "22:00", "quietEnd": "07:00",
        }
        with self._lock:
            if self._conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
                return None
            row = self._conn.execute(
                "SELECT * FROM notification_preferences WHERE user_id = ?", (user_id,)
            ).fetchone()
        if row is None:
            return defaults
        return {
            "inApp": bool(row["in_app"]), "email": bool(row["email"]),
            "mobile": bool(row["mobile"]), "criticalPatterns": bool(row["critical_patterns"]),
            "recommendations": bool(row["recommendations"]),
            "validationResults": bool(row["validation_results"]),
            "sourceHealth": bool(row["source_health"]),
            "weeklyDigest": bool(row["weekly_digest"]), "quietHours": bool(row["quiet_hours"]),
            "quietStart": str(row["quiet_start"]), "quietEnd": str(row["quiet_end"]),
        }

    def save_notification_preferences(self, user_id: str, values: dict[str, object]) -> dict[str, object] | None:
        """Upsert one user's complete notification preference document."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self._lock, self._conn:
            if self._conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
                return None
            self._conn.execute(
                """INSERT INTO notification_preferences (
                    user_id, in_app, email, mobile, critical_patterns, recommendations,
                    validation_results, source_health, weekly_digest, quiet_hours,
                    quiet_start, quiet_end, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    in_app=excluded.in_app, email=excluded.email, mobile=excluded.mobile,
                    critical_patterns=excluded.critical_patterns,
                    recommendations=excluded.recommendations,
                    validation_results=excluded.validation_results,
                    source_health=excluded.source_health, weekly_digest=excluded.weekly_digest,
                    quiet_hours=excluded.quiet_hours, quiet_start=excluded.quiet_start,
                    quiet_end=excluded.quiet_end, updated_at=excluded.updated_at""",
                (
                    user_id, int(bool(values["inApp"])), int(bool(values["email"])),
                    int(bool(values["mobile"])), int(bool(values["criticalPatterns"])),
                    int(bool(values["recommendations"])), int(bool(values["validationResults"])),
                    int(bool(values["sourceHealth"])), int(bool(values["weeklyDigest"])),
                    int(bool(values["quietHours"])), values["quietStart"], values["quietEnd"], now, now,
                ),
            )
        return self.notification_preferences(user_id)

    def notifications(
        self,
        user_id: str,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[dict[str, object]] | None:
        """Return newest notifications for one existing user."""
        with self._lock:
            if self._conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
                return None
            where = "user_id = ?" + (" AND is_read = 0" if unread_only else "")
            rows = self._conn.execute(
                f"""SELECT id, notification_type, title, detail, href, is_read, created_at
                    FROM notifications WHERE {where}
                    ORDER BY created_at DESC, id ASC LIMIT ?""",
                (user_id, limit),
            ).fetchall()
        return [
            {
                "id": str(row["id"]),
                "type": str(row["notification_type"]),
                "title": str(row["title"]),
                "detail": str(row["detail"]),
                "createdAt": str(row["created_at"]),
                "href": str(row["href"]),
                "read": bool(row["is_read"]),
            }
            for row in rows
        ]

    def connect_data_source(
        self,
        *,
        user_id: str,
        source_id: str,
        name: str,
        source_type: str,
        description: str,
        coverage: list[str],
    ) -> dict[str, object] | None:
        """Create or reconnect source metadata without storing connector credentials."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        coverage_json = json.dumps(coverage, separators=(",", ":"))
        with self._lock, self._conn:
            user_exists = self._conn.execute(
                "SELECT 1 FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if user_exists is None:
                return None
            self._conn.execute(
                """INSERT INTO data_sources (
                    id, user_id, name, source_type, description, status,
                    last_sync_at, imported_trades, coverage_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'CONNECTED', NULL, 0, ?, ?, ?)
                ON CONFLICT(user_id, id) DO UPDATE SET
                    name = excluded.name,
                    source_type = excluded.source_type,
                    description = excluded.description,
                    status = 'CONNECTED',
                    coverage_json = excluded.coverage_json,
                    updated_at = excluded.updated_at""",
                (
                    source_id, user_id, name, source_type, description,
                    coverage_json, now, now,
                ),
            )
            row = self._conn.execute(
                """SELECT id, user_id, name, source_type, description, status,
                    last_sync_at, imported_trades, coverage_json, created_at, updated_at
                FROM data_sources WHERE user_id = ? AND id = ?""",
                (user_id, source_id),
            ).fetchone()
        if row is None:  # pragma: no cover - INSERT/SELECT are atomic under the lock
            return None
        return {
            "id": str(row["id"]),
            "userId": str(row["user_id"]),
            "name": str(row["name"]),
            "type": str(row["source_type"]),
            "description": str(row["description"]),
            "status": str(row["status"]),
            "lastSyncAt": row["last_sync_at"],
            "importedTrades": int(row["imported_trades"]),
            "coverage": json.loads(str(row["coverage_json"])),
            "createdAt": str(row["created_at"]),
            "updatedAt": str(row["updated_at"]),
        }

    def import_csv_trades(
        self,
        user_id: str,
        trades: list[dict[str, object]],
    ) -> dict[str, int] | None:
        """Atomically import validated CSV trades and update CSV-source metrics."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        imported = 0
        with self._lock, self._conn:
            if self._conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
                return None
            for trade in trades:
                cursor = self._conn.execute(
                    """INSERT OR IGNORE INTO diagnostic_trades (
                        id, user_id, ticket_id, pair, direction, trend_status,
                        ema_alignment, rsi_value, atr_value, volume_status,
                        market_regime, trading_session, result, suspected_reason,
                        profit_loss, entry_time, entry_price, exit_price, exit_time,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(uuid.uuid4()), user_id, trade["ticket_id"], trade["pair"],
                        trade["direction"], trade["trend_status"], trade["ema_alignment"],
                        trade["rsi_value"], trade["atr_value"], trade["volume_status"],
                        trade["market_regime"], trade["trading_session"], trade["result"],
                        trade["suspected_reason"], trade["profit_loss"], trade["entry_time"],
                        trade["entry_price"], trade["exit_price"], trade["exit_time"], now, now,
                    ),
                )
                imported += max(0, cursor.rowcount)
            self._conn.execute(
                """INSERT INTO data_sources (
                    id, user_id, name, source_type, description, status, last_sync_at,
                    imported_trades, coverage_json, created_at, updated_at
                ) VALUES (
                    'csv', ?, 'CSV trade import', 'File upload',
                    'Imported diagnostic trade history', 'CONNECTED', ?, ?,
                    '["Historical trades","Entry snapshots","Suspected reason"]', ?, ?
                )
                ON CONFLICT(user_id, id) DO UPDATE SET
                    status = 'CONNECTED',
                    last_sync_at = excluded.last_sync_at,
                    imported_trades = data_sources.imported_trades + excluded.imported_trades,
                    updated_at = excluded.updated_at""",
                (user_id, now, imported, now, now),
            )
        return {"imported": imported, "skipped": len(trades) - imported}

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

    def recommendation_statuses(self, user_id: str) -> dict[str, str]:
        """Return persisted status overrides for one user's recommendations."""
        with self._lock:
            rows = self._conn.execute(
                """SELECT recommendation_id, status
                FROM diagnostic_recommendation_statuses WHERE user_id = ?""",
                (user_id,),
            ).fetchall()
        return {str(row["recommendation_id"]): str(row["status"]) for row in rows}

    def improvement_timeline(
        self, user_id: str, *, limit: int = 50,
    ) -> list[dict[str, object]]:
        """Return one user's improvement lifecycle, newest evidence first."""
        safe_limit = max(1, min(limit, 200))
        with self._lock:
            rows = self._conn.execute(
                """SELECT id, recommendation_id, title, change_description, status,
                    COALESCE(applied_at, updated_at) AS occurred_at, owner, notes
                FROM improvement_logs
                WHERE user_id = ?
                ORDER BY occurred_at DESC, updated_at DESC, id DESC
                LIMIT ?""",
                (user_id, safe_limit),
            ).fetchall()
        return [
            {
                "id": str(row["id"]),
                "recommendationId": str(row["recommendation_id"]),
                "title": str(row["title"]),
                "description": str(row["change_description"]),
                "status": str(row["status"]),
                "occurredAt": str(row["occurred_at"]),
                "owner": str(row["owner"]),
                "evidenceNote": str(row["notes"]) if row["notes"] is not None else None,
            }
            for row in rows
        ]

    def improvement_loss_reduction(self, user_id: str) -> list[dict[str, object]]:
        """Return baseline and measured loss-rate points for one user."""
        with self._lock:
            rows = self._conn.execute(
                """SELECT id, baseline_loss_rate, current_loss_rate,
                    validation_start, validation_end, applied_at, updated_at
                FROM improvement_logs
                WHERE user_id = ?
                ORDER BY COALESCE(applied_at, updated_at) ASC, id ASC""",
                (user_id,),
            ).fetchall()
            if not rows:
                return []
            points: list[dict[str, object]] = [{
                "label": "Baseline",
                "lossRate": float(rows[0]["baseline_loss_rate"]),
                "tradeCount": 0,
            }]
            measured_index = 0
            for row in rows:
                if row["current_loss_rate"] is None:
                    continue
                measured_index += 1
                start = row["validation_start"]
                end = row["validation_end"]
                trade_count = 0
                if start is not None and end is not None:
                    trade_count = int(self._conn.execute(
                        """SELECT COUNT(*) FROM diagnostic_trades
                        WHERE user_id = ? AND entry_time >= ? AND entry_time <= ?""",
                        (user_id, start, end),
                    ).fetchone()[0])
                points.append({
                    "label": f"Change {measured_index}",
                    "lossRate": float(row["current_loss_rate"]),
                    "tradeCount": trade_count,
                })
        return points

    def improvement_success_metrics(self, user_id: str) -> list[dict[str, object]]:
        """Return deterministic target metrics for one user's improvements."""
        with self._lock:
            rows = self._conn.execute(
                """SELECT id, title, baseline_loss_rate, target_loss_rate,
                    current_loss_rate, status, validation_end
                FROM improvement_logs
                WHERE user_id = ?
                ORDER BY COALESCE(validation_end, updated_at) DESC, id ASC""",
                (user_id,),
            ).fetchall()
        metrics: list[dict[str, object]] = []
        for row in rows:
            baseline = float(row["baseline_loss_rate"])
            target = float(row["target_loss_rate"])
            current_value = row["current_loss_rate"]
            current = float(current_value) if current_value is not None else None
            if current is None:
                progress = 0.0
                metric_status = "AT_RISK"
                detail = "No measured result is available for the validation window."
                current_label = "Not measured"
            else:
                denominator = baseline - target
                progress = round(max(0.0, min(100.0, (baseline - current) / denominator * 100)), 2) if denominator > 0 else 100.0 if current <= target else 0.0
                metric_status = "ACHIEVED" if current <= target else "ON_TRACK" if current < baseline else "AT_RISK"
                detail = "Target reached in the latest validation measurement." if metric_status == "ACHIEVED" else "Loss rate is improving toward the target." if metric_status == "ON_TRACK" else "Loss rate has not improved against the baseline."
                current_label = f"{current:g}%"
            metrics.append({
                "id": f"metric_{row['id']}",
                "label": str(row["title"]),
                "current": current_label,
                "target": f"< {target:g}%",
                "progress": progress,
                "status": metric_status,
                "detail": detail,
            })
        return metrics

    def improvement_activity_log(
        self, user_id: str, *, limit: int = 50,
    ) -> list[dict[str, object]]:
        """Return latest user-scoped improvement audit activity."""
        safe_limit = max(1, min(limit, 200))
        with self._lock:
            rows = self._conn.execute(
                """SELECT id, recommendation_id, title, status, current_loss_rate,
                    notes, owner, updated_at
                FROM improvement_logs
                WHERE user_id = ?
                ORDER BY updated_at DESC, id DESC
                LIMIT ?""",
                (user_id, safe_limit),
            ).fetchall()
        activities: list[dict[str, object]] = []
        for row in rows:
            if row["current_loss_rate"] is not None:
                activity_type = "EVIDENCE"
                message = (
                    f"Recorded {float(row['current_loss_rate']):g}% current loss rate "
                    f"for {row['title']}."
                )
            elif row["notes"] is not None:
                activity_type = "NOTE"
                message = str(row["notes"])
            else:
                activity_type = "STATUS_CHANGE"
                message = f"Updated {row['title']} status to {row['status']}."
            activities.append({
                "id": f"activity_{row['id']}",
                "type": activity_type,
                "message": message,
                "actor": str(row["owner"]),
                "occurredAt": str(row["updated_at"]),
                "recommendationId": str(row["recommendation_id"]),
            })
        return activities

    def set_recommendation_applied(
        self, user_id: str, recommendation_id: str, applied: bool,
    ) -> None:
        """Persist or clear one user-scoped APPLIED recommendation override."""
        with self._lock, self._conn:
            if not applied:
                self._conn.execute(
                    """DELETE FROM diagnostic_recommendation_statuses
                    WHERE user_id = ? AND recommendation_id = ?""",
                    (user_id, recommendation_id),
                )
                return
            now = datetime.now(timezone.utc).isoformat()
            self._conn.execute(
                """INSERT INTO diagnostic_recommendation_statuses
                    (user_id, recommendation_id, status, applied_at, updated_at)
                VALUES (?, ?, 'APPLIED', ?, ?)
                ON CONFLICT(user_id, recommendation_id) DO UPDATE SET
                    status='APPLIED', updated_at=excluded.updated_at""",
                (user_id, recommendation_id, now, now),
            )

    def replace_recommendations(
        self,
        user_id: str,
        generated_at: str,
        recommendations: list[dict[str, object]],
    ) -> None:
        """Atomically replace one user's generated recommendation snapshot."""
        with self._lock, self._conn:
            existing_created = {
                str(row["id"]): str(row["created_at"])
                for row in self._conn.execute(
                    "SELECT id, created_at FROM diagnostic_recommendations WHERE user_id = ?",
                    (user_id,),
                ).fetchall()
            }
            self._conn.execute(
                "DELETE FROM diagnostic_recommendations WHERE user_id = ?",
                (user_id,),
            )
            self._conn.executemany(
                """INSERT INTO diagnostic_recommendations (
                    id, user_id, title, summary, action, pattern_id, pattern_name,
                    priority, status, expected_impact, evidence_losses, confidence,
                    effort, steps_json, validation_target, guardrail, generated_at,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        recommendation["id"], user_id, recommendation["title"],
                        recommendation["summary"], recommendation["action"],
                        recommendation["patternId"], recommendation["patternName"],
                        recommendation["priority"], recommendation["status"],
                        recommendation["expectedImpact"], recommendation["evidenceLosses"],
                        recommendation["confidence"], recommendation["effort"],
                        json.dumps(recommendation["steps"], ensure_ascii=False),
                        recommendation["validationTarget"], recommendation["guardrail"],
                        generated_at,
                        existing_created.get(str(recommendation["id"]), generated_at),
                        generated_at,
                    )
                    for recommendation in recommendations
                ],
            )

    def persisted_recommendations(self, user_id: str) -> list[dict[str, object]]:
        """Return persisted recommendations in deterministic priority order."""
        with self._lock:
            rows = self._conn.execute(
                """SELECT * FROM diagnostic_recommendations
                WHERE user_id = ?
                ORDER BY CASE priority
                    WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 ELSE 2 END,
                    expected_impact DESC, confidence DESC, title ASC""",
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def loss_pattern_analysis(self, user_id: str) -> dict[str, object]:
        """Return the latest persisted loss-pattern snapshot for one user."""
        with self._lock:
            latest_period = self._conn.execute(
                """SELECT period_start, period_end, MAX(generated_at) AS generated_at
                FROM pola_kekalahan
                WHERE user_id = ?
                GROUP BY period_start, period_end
                ORDER BY period_end DESC, period_start DESC, generated_at DESC
                LIMIT 1""",
                (user_id,),
            ).fetchone()
            if latest_period is None:
                return {
                    "summary": {
                        "totalLosses": 0,
                        "classifiedLosses": 0,
                        "lossesClassifiedPct": 0.0,
                    },
                    "patterns": [],
                    "insight": {
                        "title": "No patterns detected",
                        "detail": "No persisted loss-pattern analysis is available for this period.",
                    },
                    "generatedAt": datetime.now(timezone.utc).isoformat(),
                }

            period_start = str(latest_period["period_start"])
            period_end = str(latest_period["period_end"])
            rows = self._conn.execute(
                """SELECT id, name, category, description, loss_count,
                    loss_percentage, confidence, severity, evidence_trade_ids_json,
                    trend_delta, generated_at
                FROM pola_kekalahan
                WHERE user_id = ? AND period_start = ? AND period_end = ?
                ORDER BY loss_percentage DESC, confidence DESC, name ASC""",
                (user_id, period_start, period_end),
            ).fetchall()
            total_row = self._conn.execute(
                """SELECT COUNT(*) AS total
                FROM diagnostic_trades
                WHERE user_id = ? AND result = 'SL'
                    AND entry_time >= ? AND entry_time <= ?""",
                (user_id, period_start, period_end),
            ).fetchone()

        total_losses = int(total_row["total"] or 0)
        classified_losses = min(sum(int(row["loss_count"]) for row in rows), total_losses)
        patterns = [
            {
                "id": str(row["id"]),
                "name": str(row["name"]),
                "category": str(row["category"]),
                "description": str(row["description"]),
                "lossCount": int(row["loss_count"]),
                "lossPercentage": float(row["loss_percentage"]),
                "confidence": float(row["confidence"]),
                "severity": str(row["severity"]),
                "evidenceTradeIds": json.loads(str(row["evidence_trade_ids_json"])),
                "trendDelta": float(row["trend_delta"]),
            }
            for row in rows
        ]
        dominant = patterns[0]
        return {
            "summary": {
                "totalLosses": total_losses,
                "classifiedLosses": classified_losses,
                "lossesClassifiedPct": round(classified_losses / total_losses * 100, 2)
                if total_losses else 0.0,
            },
            "patterns": patterns,
            "insight": {
                "title": "Primary evidence",
                "detail": (
                    f"{dominant['name']} is the dominant persisted pattern, accounting for "
                    f"{dominant['lossPercentage']:g}% of losses in the latest analysis period."
                ),
            },
            "generatedAt": max(str(row["generated_at"]) for row in rows),
        }

    def loss_snapshots(
        self, user_id: str, period_start: str, period_end: str,
    ) -> list[dict[str, object]]:
        """Return loss snapshots used as evidence for one analysis period."""
        with self._lock:
            rows = self._conn.execute(
                """SELECT id, direction, trend_status, ema_alignment, rsi_value,
                    volume_status, market_regime, trading_session
                FROM diagnostic_trades
                WHERE user_id = ? AND result = 'SL'
                    AND entry_time >= ? AND entry_time <= ?
                ORDER BY entry_time ASC, id ASC""",
                (user_id, period_start, period_end),
            ).fetchall()
        return [dict(row) for row in rows]

    def loss_user_ids(self, period_start: str, period_end: str) -> list[str]:
        """Return users with losses in a period, ordered for deterministic jobs."""
        with self._lock:
            rows = self._conn.execute(
                """SELECT DISTINCT user_id
                FROM diagnostic_trades
                WHERE result = 'SL' AND entry_time >= ? AND entry_time <= ?
                ORDER BY user_id ASC""",
                (period_start, period_end),
            ).fetchall()
        return [str(row["user_id"]) for row in rows]

    def replace_loss_patterns(
        self,
        user_id: str,
        period_start: str,
        period_end: str,
        generated_at: str,
        patterns: list[dict[str, object]],
    ) -> None:
        """Atomically replace one user's persisted pattern snapshot for a period."""
        with self._lock, self._conn:
            self._conn.execute(
                """DELETE FROM pola_kekalahan
                WHERE user_id = ? AND period_start = ? AND period_end = ?""",
                (user_id, period_start, period_end),
            )
            self._conn.executemany(
                """INSERT INTO pola_kekalahan (
                    id, user_id, name, category, description, loss_count,
                    loss_percentage, confidence, severity, evidence_trade_ids_json,
                    trend_delta, period_start, period_end, generated_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        pattern["id"], user_id, pattern["name"], pattern["category"],
                        pattern["description"], pattern["loss_count"],
                        pattern["loss_percentage"], pattern["confidence"],
                        pattern["severity"], json.dumps(pattern["evidence_trade_ids"]),
                        pattern["trend_delta"], period_start, period_end, generated_at,
                        generated_at, generated_at,
                    )
                    for pattern in patterns
                ],
            )

    def compare_loss_pattern_periods(
        self,
        user_id: str,
        current_start: str,
        current_end: str,
        baseline_start: str,
        baseline_end: str,
    ) -> dict[str, object]:
        """Compare persisted pattern shares across two explicit user-scoped periods."""
        with self._lock:
            rows = self._conn.execute(
                """SELECT id, name, category, description, loss_count, loss_percentage,
                    confidence, severity, evidence_trade_ids_json, period_start, period_end
                FROM pola_kekalahan
                WHERE user_id = ? AND (
                    (period_start = ? AND period_end = ?)
                    OR (period_start = ? AND period_end = ?)
                )""",
                (user_id, current_start, current_end, baseline_start, baseline_end),
            ).fetchall()

        current = {
            str(row["name"]): row
            for row in rows
            if row["period_start"] == current_start and row["period_end"] == current_end
        }
        baseline = {
            str(row["name"]): row
            for row in rows
            if row["period_start"] == baseline_start and row["period_end"] == baseline_end
        }
        patterns: list[dict[str, object]] = []
        counts = {"improving": 0, "worsening": 0, "stable": 0}
        for name in sorted(set(current) | set(baseline)):
            current_row = current.get(name)
            baseline_row = baseline.get(name)
            source = current_row or baseline_row
            current_share = float(current_row["loss_percentage"]) if current_row else 0.0
            baseline_share = float(baseline_row["loss_percentage"]) if baseline_row else 0.0
            delta = round(current_share - baseline_share, 2)
            status = "worsening" if delta > 0 else "improving" if delta < 0 else "stable"
            counts[status] += 1
            patterns.append({
                "id": str(source["id"]),
                "name": name,
                "category": str(source["category"]),
                "description": str(source["description"]),
                "currentLossCount": int(current_row["loss_count"]) if current_row else 0,
                "currentShare": current_share,
                "baselineLossCount": int(baseline_row["loss_count"]) if baseline_row else 0,
                "baselineShare": baseline_share,
                "deltaPercentagePoints": delta,
                "status": status,
                "confidence": float(source["confidence"]),
                "severity": str(source["severity"]),
                "evidenceTradeIds": json.loads(str(source["evidence_trade_ids_json"])),
            })
        patterns.sort(key=lambda item: (-abs(float(item["deltaPercentagePoints"])), str(item["name"])))
        return {
            "currentPeriod": {"start": current_start, "end": current_end},
            "baselinePeriod": {"start": baseline_start, "end": baseline_end},
            "summary": counts,
            "patterns": patterns,
        }

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
