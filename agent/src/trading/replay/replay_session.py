from dataclasses import dataclass, field

@dataclass
class ReplaySession:
    balance: float = 10000.0
    equity: float = 10000.0
    equity_peak: float = 10000.0
    drawdown: float = 0.0
    open_positions: dict = field(default_factory=dict)
    closed_trades: list = field(default_factory=list)
    trade_count: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    equity_history: list = field(default_factory=list)
    def mark_equity(self, value, timestamp=None):
        self.equity = float(value); self.equity_peak = max(self.equity_peak, self.equity)
        self.drawdown = max(self.drawdown, self.equity_peak - self.equity)
        self.equity_history.append((timestamp, self.equity))