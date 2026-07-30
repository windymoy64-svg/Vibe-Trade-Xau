"""Historical driver over the production feature, signal, decision and risk stages."""

from __future__ import annotations
from datetime import timedelta
from src.trading.forex_decisions import (
    PendingOrdersState,
    PositionState,
    PositionStateSnapshot,
    QuoteSnapshot,
    RuntimeDecisionEngine,
    StrategyRuntimeState,
    ACTION,
)
from src.trading.forex_features import RuntimeFeatureBuilder, WarmupStatus
from src.trading.forex_risk import (
    AccountSnapshot,
    ApprovalStatus,
    RiskConfiguration,
    RiskPositionDirection,
    RiskPositionSnapshot,
    RuntimeForexRiskManager,
    SymbolSpecification,
)
from src.trading.forex_signals import RuntimeSignalEngine
from .candle_feed import CandleFeed
from .paper_executor import PaperExecutor
from .replay_clock import ReplayClock
from .replay_session import ReplaySession
from .trade_journal import TradeJournal
from src.trading.runtime_config import RuntimeConfig


class ReplayEngine:
    def __init__(
        self,
        *,
        initial_balance=10000.0,
        risk_configuration=None,
        specification=None,
        progress_interval=100,
        runtime_config=None,
    ):
        self.runtime_config = runtime_config or RuntimeConfig()
        self.clock = ReplayClock()
        self.session = ReplaySession(initial_balance, initial_balance, initial_balance)
        self.journal = TradeJournal()
        self.executor = PaperExecutor(self.session, self.journal)
        self.progress_interval = progress_interval
        self.risk_configuration = risk_configuration or RiskConfiguration(
            risk_percent=self.runtime_config.risk_percent,
            stop_loss_distance=self.runtime_config.stop_distance,
            reward_ratio=self.runtime_config.rr,
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
        self.specification = specification

    def run_csv(self, path, *, symbol="XAUUSD", timeframe="1h"):
        return self.run(CandleFeed.from_csv(path, symbol=symbol, timeframe=timeframe))

    def run(self, feed):
        first = feed.next()
        if first is None:
            raise ValueError("replay CSV contains no candles")
        self.clock.advance(first.timestamp)
        broad = timedelta(days=365000)
        features = RuntimeFeatureBuilder(
            runtime_config=self.runtime_config, clock=self.clock.current_time, stale_after=broad
        )
        signals = RuntimeSignalEngine(
            runtime_config=self.runtime_config, clock=self.clock.current_time, stale_after=broad
        )
        decisions = RuntimeDecisionEngine(
            runtime_config=self.runtime_config, clock=self.clock.current_time, stale_after=broad
        )
        risk = RuntimeForexRiskManager(
            runtime_config=self.runtime_config, clock=self.clock.current_time, stale_after=broad
        )
        candle = first
        processed = 0
        while candle is not None:
            self.clock.advance(candle.timestamp)
            self.executor.process_candle(candle, processed)
            feature = features.build(candle)
            if feature.warmup_status is WarmupStatus.READY:
                signal = signals.generate(feature)
                position = self.session.open_positions.get(candle.symbol)
                state = (
                    PositionState.FLAT
                    if position is None
                    else (PositionState.LONG if position.side == "LONG" else PositionState.SHORT)
                )
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
                    PositionStateSnapshot(symbol=candle.symbol, state=state),
                    PendingOrdersState(symbol=candle.symbol),
                    quote,
                    StrategyRuntimeState(),
                )
                if decision.action is not ACTION.HOLD:
                    spec = self.specification or SymbolSpecification(
                        symbol=candle.symbol,
                        tick_size=0.01,
                        tick_value_per_lot=1,
                        contract_size=100,
                        lot_step=0.01,
                        min_lot=0.01,
                        max_lot=100,
                        stop_level_distance=0,
                        freeze_level_distance=0,
                    )
                    account = AccountSnapshot(
                        broker_timestamp=candle.timestamp,
                        equity=max(self.session.equity, 0.01),
                        free_margin=max(self.session.equity, 0),
                        margin_level=1000,
                        leverage=100,
                        daily_loss=0,
                        drawdown_percent=0,
                        trades_today=self.session.trade_count,
                        consecutive_losses=0,
                        symbol_exposure=0,
                        correlated_exposure=0,
                    )
                    current = (
                        None
                        if position is None
                        else RiskPositionSnapshot(
                            symbol=candle.symbol,
                            position_ticket=1,
                            direction=RiskPositionDirection(position.side),
                            volume_lots=position.volume,
                            owned=True,
                        )
                    )
                    plan = risk.assess(decision, account, quote, spec, self.risk_configuration, current)
                    if plan.approval_status is ApprovalStatus.APPROVED:
                        self.executor.submit(plan, signal, decision)
            processed += 1
            if self.progress_interval and processed % self.progress_interval == 0:
                self._progress(processed, feed.length())
            candle = feed.next()
        self._summary(processed)
        return self.session

    def _progress(self, n, total):
        print(f"Processed:\n{n} / {total}\nTrades:\n{self.session.trade_count}\nBalance:\n{self.session.balance:.2f}")

    def _summary(self, n):
        s = self.session
        print(
            f"Replay Complete\nCandles Processed: {n}\nTrades: {s.trade_count}\nWins: {s.winning_trades}\nLosses: {s.losing_trades}\nOpen Trades: {len(s.open_positions)}\nClosed Trades: {len(s.closed_trades)}\nNet Profit: {s.balance - s.equity_history[0][1]:.2f}\nEnding Balance: {s.balance:.2f}\nMax Drawdown: {s.drawdown:.2f}"
        )
