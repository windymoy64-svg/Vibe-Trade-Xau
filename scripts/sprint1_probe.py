from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))

from src.trading.forex_features import RuntimeFeatureBuilder, WarmupStatus
from src.trading.forex_risk import AccountSnapshot, RiskConfiguration, RuntimeForexRiskManager, SymbolSpecification
from src.trading.forex_signals import RuntimeSignalEngine, SignalType
from src.trading.forex_decisions import (
    PendingOrdersState,
    PositionState,
    PositionStateSnapshot,
    QuoteSnapshot,
    RuntimeDecisionEngine,
    StrategyRuntimeState,
)
from src.trading.replay.candle_feed import CandleFeed
from src.trading.replay.replay_engine import ReplayEngine
from src.trading.runtime_config import RuntimeConfig


def main() -> int:
    data = ROOT / ".cache" / "optimization" / "XAUUSD_H1_sprint1.csv"
    config = RuntimeConfig(RISK_PERCENT=1.0, STOP_DISTANCE=8.0, RR=2.0)
    clock = lambda: datetime(2030, 1, 1, tzinfo=timezone.utc)
    broad = timedelta(days=365000)
    features = RuntimeFeatureBuilder(runtime_config=config, clock=clock, stale_after=broad)
    signals = RuntimeSignalEngine(runtime_config=config, clock=clock, stale_after=broad)
    decisions = RuntimeDecisionEngine(runtime_config=config, clock=clock, stale_after=broad)
    risk = RuntimeForexRiskManager(runtime_config=config, clock=clock, stale_after=broad)
    risk_cfg = RiskConfiguration(
        risk_percent=1.0,
        stop_loss_distance=8.0,
        reward_ratio=2.0,
        max_spread=1000.0,
        min_free_margin=0.0,
        min_margin_level=0.0,
        max_daily_loss=1_000_000.0,
        max_drawdown_percent=100.0,
        max_trades_per_day=100,
        max_consecutive_losses=100,
        max_symbol_exposure=1_000_000.0,
        max_correlated_exposure=1_000_000.0,
        max_slippage=20.0,
        expiration_seconds=30 * 86400,
    )
    spec = SymbolSpecification(
        symbol="XAUUSD",
        tick_size=0.01,
        tick_value_per_lot=1,
        contract_size=100,
        lot_step=0.01,
        min_lot=0.01,
        max_lot=100,
        stop_level_distance=0,
        freeze_level_distance=0,
    )
    counts = Counter()
    approved = 0
    feed = CandleFeed.from_csv(data, symbol="XAUUSD", timeframe="1h")
    candle = feed.next()
    while candle is not None:
        feature = features.build(candle)
        if feature.warmup_status is WarmupStatus.READY:
            signal = signals.generate(feature)
            counts[signal.signal_type.value] += 1
            if signal.signal_type in {SignalType.LONG, SignalType.SHORT}:
                quote = QuoteSnapshot(
                    symbol=candle.symbol,
                    timeframe=candle.timeframe,
                    broker_timestamp=candle.timestamp,
                    bid=candle.close,
                    ask=candle.close,
                    spread=0,
                )
                decision = decisions.decide(
                    signal,
                    PositionStateSnapshot(symbol=candle.symbol, state=PositionState.FLAT),
                    PendingOrdersState(symbol=candle.symbol),
                    quote,
                    StrategyRuntimeState(),
                )
                account = AccountSnapshot(
                    broker_timestamp=candle.timestamp,
                    equity=10000,
                    free_margin=10000,
                    margin_level=1000,
                    leverage=100,
                    daily_loss=0,
                    drawdown_percent=0,
                    trades_today=0,
                    consecutive_losses=0,
                    symbol_exposure=0,
                    correlated_exposure=0,
                )
                plan = risk.assess(decision, account, quote, spec, risk_cfg, None)
                if plan.approval_status.value == "APPROVED":
                    approved += 1
        candle = feed.next()
    engine = ReplayEngine(progress_interval=0, runtime_config=config)
    session = engine.run_csv(data, symbol="XAUUSD", timeframe="1h")
    print({"signals": dict(counts), "approved": approved, "trades": session.trade_count, "closed": len(session.closed_trades)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
