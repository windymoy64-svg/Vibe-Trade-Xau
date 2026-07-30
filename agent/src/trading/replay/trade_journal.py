from dataclasses import dataclass, asdict
import json

@dataclass(frozen=True)
class TradeRecord:
    trade_id: str; symbol: str; entry_time: object; exit_time: object; entry_price: float; exit_price: float
    side: str; volume: float; sl: float|None; tp: float|None; profit: float; r_multiple: float
    holding_candles: int; close_reason: str; signal: object=None; decision: object=None

class TradeJournal:
    def __init__(self): self.trades=[]
    def record(self, **kwargs):
        trade = TradeRecord(**kwargs); self.trades.append(trade); return trade
    def to_json(self): return json.dumps([asdict(t) for t in self.trades], default=str)