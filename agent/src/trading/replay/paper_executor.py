"""Deterministic broker simulator; deliberately has no MetaTrader imports."""
from __future__ import annotations
from dataclasses import dataclass
from uuid import uuid4
from src.trading.forex_decisions import ACTION

@dataclass
class PaperPosition:
    trade_id: str; symbol: str; side: str; volume: float; entry_price: float; entry_time: object
    sl: float|None; tp: float|None; entry_bar: int; signal: object; decision: object

class PaperExecutor:
    def __init__(self, session, journal, *, contract_size=100.0):
        self.session=session; self.journal=journal; self.contract_size=float(contract_size); self.pending=None
    def submit(self, plan, signal, decision):
        if plan.action in {ACTION.OPEN_LONG.value, ACTION.OPEN_SHORT.value, ACTION.CLOSE_POSITION.value}:
            self.pending=(plan, signal, decision)
    def process_candle(self, candle, bar_index):
        # Orders created from candle N are filled only now, at candle N+1 open.
        if self.pending:
            plan, signal, decision=self.pending; self.pending=None
            if plan.action == ACTION.CLOSE_POSITION.value:
                self._close(plan.symbol, candle.open, candle.timestamp, bar_index, "SIGNAL")
            elif plan.symbol not in self.session.open_positions:
                side="LONG" if plan.action == ACTION.OPEN_LONG.value else "SHORT"
                self.session.open_positions[plan.symbol]=PaperPosition(str(uuid4()), plan.symbol, side, plan.volume_lots,
                    candle.open, candle.timestamp, plan.stop_loss, plan.take_profit, bar_index, signal, decision)
        for symbol, position in list(self.session.open_positions.items()):
            hit=self._protective_fill(position, candle)
            if hit: self._close(symbol, hit[0], candle.timestamp, bar_index, hit[1])
        self._mark(candle)
    def _protective_fill(self, p, c):
        # Deterministic intrabar path assumption: OPEN -> HIGH -> LOW -> CLOSE.
        # Gap-through protection fills at open; otherwise HIGH is visited before LOW.
        if p.side == "LONG":
            if p.tp is not None and c.open >= p.tp: return c.open,"TP"
            if p.sl is not None and c.open <= p.sl: return c.open,"SL"
            if p.tp is not None and c.high >= p.tp: return p.tp,"TP"
            if p.sl is not None and c.low <= p.sl: return p.sl,"SL"
        else:
            if p.sl is not None and c.open >= p.sl: return c.open,"SL"
            if p.tp is not None and c.open <= p.tp: return c.open,"TP"
            # On OPEN->HIGH->LOW, a short stop is reached before its target.
            if p.sl is not None and c.high >= p.sl: return p.sl,"SL"
            if p.tp is not None and c.low <= p.tp: return p.tp,"TP"
        return None
    def _close(self, symbol, price, timestamp, bar_index, reason):
        p=self.session.open_positions.pop(symbol, None)
        if not p: return
        direction=1 if p.side=="LONG" else -1
        profit=(price-p.entry_price)*direction*p.volume*self.contract_size
        risk=abs(p.entry_price-p.sl)*p.volume*self.contract_size if p.sl is not None else 0
        trade=self.journal.record(trade_id=p.trade_id,symbol=symbol,entry_time=p.entry_time,exit_time=timestamp,
            entry_price=p.entry_price,exit_price=price,side=p.side,volume=p.volume,sl=p.sl,tp=p.tp,profit=profit,
            r_multiple=profit/risk if risk else 0.0,holding_candles=bar_index-p.entry_bar+1,close_reason=reason,
            signal=p.signal.model_dump(mode="json") if hasattr(p.signal,"model_dump") else p.signal,
            decision=p.decision.model_dump(mode="json") if hasattr(p.decision,"model_dump") else p.decision)
        self.session.balance += profit; self.session.closed_trades.append(trade); self.session.trade_count += 1
        self.session.winning_trades += profit>0; self.session.losing_trades += profit<0
    def _mark(self, candle):
        unrealized=sum((candle.close-p.entry_price)*(1 if p.side=="LONG" else -1)*p.volume*self.contract_size
                       for p in self.session.open_positions.values())
        self.session.mark_equity(self.session.balance+unrealized, candle.timestamp)