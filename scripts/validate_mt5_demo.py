"""Read-only validation of a real MetaTrader 5 demo environment.

This utility deliberately contains no trading calls.  In particular, it never
calls ``order_check`` or ``order_send``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path.home() / ".vibe-trading" / "mt5.json"
DEMO_TRADE_MODE = 0


def _fields(value: Any, names: tuple[str, ...]) -> dict[str, Any]:
    return {name: getattr(value, name, None) for name in names}


def _error(mt5: Any) -> str:
    try:
        return repr(mt5.last_error())
    except Exception as exc:  # diagnostics must not hide the original failure
        return f"last_error unavailable: {exc}"


def _resolve_symbol(mt5: Any, requested: str, configured_suffix: str = "") -> str | None:
    requested = requested.strip()
    candidates = [requested]
    if configured_suffix and not requested.lower().endswith(configured_suffix.lower()):
        candidates.append(requested + configured_suffix)
    for alias in ("XAUUSD", "GOLD") if requested.upper() in {"XAUUSD", "GOLD"} else ():
        if alias not in candidates:
            candidates.append(alias)
    for name in candidates:
        if mt5.symbol_info(name) is not None:
            return name

    wanted = requested.upper()
    prefixes = ("XAUUSD", "GOLD") if wanted in {"XAUUSD", "GOLD"} else (wanted,)
    symbols = mt5.symbols_get()
    if symbols is None:
        return None
    matches = [
        str(getattr(info, "name", ""))
        for info in symbols
        if any(str(getattr(info, "name", "")).upper().startswith(prefix) for prefix in prefixes)
    ]
    return min((name for name in matches if name), key=lambda name: (len(name), name), default=None)


def validate(
    mt5: Any,
    config: dict[str, Any],
    symbol: str,
    freshness_seconds: int,
    clock_skew_tolerance_seconds: int = 300,
) -> dict[str, Any]:
    host_epoch = time.time()
    host_local_datetime = datetime.fromtimestamp(host_epoch).astimezone()
    host_utc_datetime = datetime.fromtimestamp(host_epoch, tz=timezone.utc)
    checks = {name: {"status": "FAIL"} for name in (
        "MT5 package", "Terminal", "Account", "Trading permission", "Symbol",
        "Live Tick", "Positions API", "Orders API", "History API",
    )}
    report: dict[str, Any] = {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "host_clock": {
            "host_epoch": host_epoch,
            "local_datetime": host_local_datetime.isoformat(),
            "utc_datetime": host_utc_datetime.isoformat(),
        },
        "requested_symbol": symbol,
        "read_only": True,
        "checks": checks,
    }
    package_version = getattr(mt5, "__version__", None)
    try:
        api_version = mt5.version()
        checks["MT5 package"] = {"status": "PASS", "package_version": package_version, "api_version": api_version}
    except Exception as exc:
        checks["MT5 package"]["error"] = str(exc)
        report["overall"] = "FAIL"
        return report

    kwargs = {key: config[key] for key in ("login", "password", "server") if config.get(key)}
    kwargs["timeout"] = int(float(config.get("timeout", 15)) * 1000)
    args = (str(config["terminal_path"]),) if config.get("terminal_path") else ()
    try:
        initialized = bool(mt5.initialize(*args, **kwargs))
    except Exception as exc:
        checks["Terminal"]["error"] = f"initialize raised: {exc}"
        report["overall"] = "FAIL"
        return report
    if not initialized:
        checks["Terminal"]["error"] = f"initialize returned False; last_error={_error(mt5)}"
        report["overall"] = "FAIL"
        return report

    try:
        terminal = mt5.terminal_info()
        terminal_version = mt5.version()
        if terminal is None:
            checks["Terminal"]["error"] = f"terminal_info returned None; last_error={_error(mt5)}"
        else:
            checks["Terminal"] = {"status": "PASS", "terminal_info": terminal._asdict(), "version": terminal_version}

        account = mt5.account_info()
        account_fields = _fields(account, (
            "login", "server", "trade_mode", "leverage", "balance", "equity",
            "margin_free", "trade_allowed",
        )) if account is not None else {}
        required = ("login", "server", "leverage", "balance", "equity", "margin_free")
        account_ok = account is not None and all(account_fields.get(field) is not None for field in required)
        checks["Account"] = {"status": "PASS" if account_ok else "FAIL", "account_info": account_fields}
        if account is None:
            checks["Account"]["error"] = f"account_info returned None; last_error={_error(mt5)}"
        is_demo = account_fields.get("trade_mode") == getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", DEMO_TRADE_MODE)
        trade_allowed = account_fields.get("trade_allowed") is True
        checks["Trading permission"] = {
            "status": "PASS" if account_ok and is_demo and trade_allowed else "FAIL",
            "is_demo": is_demo,
            "trade_allowed": account_fields.get("trade_allowed"),
        }

        resolved = _resolve_symbol(mt5, symbol, str(config.get("symbol_suffix", "")))
        info = mt5.symbol_info(resolved) if resolved else None
        metadata_names = (
            "trade_mode", "filling_mode", "digits", "point", "volume_min",
            "volume_step", "trade_stops_level", "trade_freeze_level",
        )
        metadata = _fields(info, metadata_names) if info is not None else {}
        symbol_ok = info is not None and all(metadata.get(field) is not None for field in metadata_names)
        checks["Symbol"] = {
            "status": "PASS" if symbol_ok else "FAIL", "resolved_symbol": resolved,
            "symbol_info": metadata,
        }
        if not symbol_ok:
            checks["Symbol"]["error"] = "configured symbol unavailable or required metadata missing"

        tick1 = mt5.symbol_info_tick(resolved) if resolved else None
        time.sleep(1)
        tick2 = mt5.symbol_info_tick(resolved) if resolved else None
        tick_time = getattr(tick2, "time", None) if tick2 is not None else None
        tick_time_msc = getattr(tick2, "time_msc", None) if tick2 is not None else None
        now_timestamp = time.time()
        now = datetime.fromtimestamp(now_timestamp, tz=timezone.utc)
        tick_timestamp = float(tick_time) if tick_time is not None else None
        tick_datetime = (
            datetime.fromtimestamp(tick_timestamp, tz=timezone.utc)
            if tick_timestamp is not None
            else None
        )
        tick_msc_timestamp = float(tick_time_msc) / 1000.0 if tick_time_msc is not None else None
        tick_msc_datetime = (
            datetime.fromtimestamp(tick_msc_timestamp, tz=timezone.utc)
            if tick_msc_timestamp is not None
            else None
        )
        age = now_timestamp - tick_timestamp if tick_timestamp is not None else None
        clock_skew_detected = age is not None and age < 0
        clock_skew_seconds = abs(age) if clock_skew_detected else 0.0
        bid = getattr(tick2, "bid", None) if tick2 is not None else None
        ask = getattr(tick2, "ask", None) if tick2 is not None else None
        tick1_time_msc = getattr(tick1, "time_msc", None) if tick1 is not None else None
        tick1_bid = getattr(tick1, "bid", None) if tick1 is not None else None
        tick1_ask = getattr(tick1, "ask", None) if tick1 is not None else None
        update_observed = bool(
            tick1 is not None
            and tick2 is not None
            and (
                tick_time_msc != tick1_time_msc
                or bid != tick1_bid
                or ask != tick1_ask
            )
        )
        point = metadata.get("point")
        spread = (float(ask) - float(bid)) / float(point) if bid is not None and ask is not None and point else None
        prices_valid = bool(bid is not None and ask is not None and bid > 0 and ask > 0)
        tick_ok = bool(tick2 is not None and prices_valid and update_observed)
        checks["Live Tick"] = {
            "status": "PASS" if tick_ok else "FAIL", "bid": bid, "ask": ask,
            "spread_points": spread, "timestamp": tick_time, "time_msc": tick_time_msc,
            "observation_window_seconds": 1,
            "update_observed": update_observed,
            "changed_fields": {
                "time_msc": tick_time_msc != tick1_time_msc,
                "bid": bid != tick1_bid,
                "ask": ask != tick1_ask,
            },
            "tick1": {"time_msc": tick1_time_msc, "bid": tick1_bid, "ask": tick1_ask},
            "tick2": {"time_msc": tick_time_msc, "bid": bid, "ask": ask},
            "tick_utc_datetime": tick_datetime.isoformat() if tick_datetime else None,
            "tick_msc_utc_datetime": tick_msc_datetime.isoformat() if tick_msc_datetime else None,
            "tick_epoch": tick_timestamp,
            "tick_msc_epoch": tick_msc_timestamp,
            "tick_epoch_internal_difference_seconds": (
                tick_msc_timestamp - tick_timestamp
                if tick_msc_timestamp is not None and tick_timestamp is not None
                else None
            ),
            "host_epoch": now_timestamp,
            "difference_seconds": tick_timestamp - now_timestamp if tick_timestamp is not None else None,
            "current_utc_datetime": now.isoformat(), "age_seconds": age,
            "clock_skew_detected": clock_skew_detected,
            "clock_skew_seconds": clock_skew_seconds,
            "freshness_limit_seconds": freshness_seconds,
            "clock_skew_tolerance_seconds": clock_skew_tolerance_seconds,
            "clock_skew_classification": "informational",
        }
        if clock_skew_detected:
            checks["Live Tick"]["clock_skew_note"] = "host and MT5 tick clocks differ"
        if tick2 is None:
            checks["Live Tick"]["error"] = "second tick read returned no data"
        elif not prices_valid:
            checks["Live Tick"]["error"] = "second tick contains invalid bid or ask"
        elif not update_observed:
            checks["Live Tick"]["error"] = "no tick update observed during the observation window"

        start = now - timedelta(days=7)
        for label, call in (
            ("Positions API", mt5.positions_get),
            ("Orders API", mt5.orders_get),
            ("History API", lambda: mt5.history_deals_get(start, now)),
        ):
            try:
                rows = call()
                checks[label] = {"status": "PASS" if rows is not None else "FAIL", "count": len(rows) if rows is not None else None}
                if rows is None:
                    checks[label]["error"] = f"API returned None; last_error={_error(mt5)}"
            except Exception as exc:
                checks[label] = {"status": "FAIL", "error": str(exc)}
    finally:
        mt5.shutdown()

    report["overall"] = "PASS" if all(item["status"] == "PASS" for item in checks.values()) else "FAIL"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a real MT5 demo terminal using read-only APIs.")
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--freshness-seconds", type=int, default=120)
    parser.add_argument("--clock-skew-tolerance-seconds", type=int, default=300)
    args = parser.parse_args()
    config: dict[str, Any] = {}
    if args.config.exists():
        config = json.loads(args.config.read_text(encoding="utf-8"))
    try:
        import MetaTrader5 as mt5  # type: ignore[import-not-found]
        report = validate(
            mt5,
            config,
            args.symbol,
            args.freshness_seconds,
            args.clock_skew_tolerance_seconds,
        )
    except ImportError as exc:
        names = (
            "MT5 package", "Terminal", "Account", "Trading permission", "Symbol",
            "Live Tick", "Positions API", "Orders API", "History API",
        )
        report = {
            "overall": "FAIL", "read_only": True,
            "checks": {
                name: {"status": "FAIL", "error": str(exc) if name == "MT5 package" else "blocked: MT5 package unavailable"}
                for name in names
            },
        }
    print(json.dumps(report, indent=2, default=str))
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())