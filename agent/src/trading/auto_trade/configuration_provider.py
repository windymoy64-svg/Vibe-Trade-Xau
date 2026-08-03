"""Load immutable, execution-ready bot configuration snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class BotConfigurationSource(Protocol):
    def get_auto_trade_configuration(
        self, user_id: str, config_id: str,
    ) -> dict[str, object] | None: ...


@dataclass(frozen=True, slots=True)
class BotExecutionConfiguration:
    id: str
    user_id: str
    symbol: str
    timeframe: str
    strategy: str
    risk_per_trade: float
    daily_loss_limit: float
    paper_mode: bool
    lot_size: float
    stop_loss_pips: float
    take_profit_pips: float
    version: str


class BotConfigurationNotReadyError(ValueError):
    pass


class BotExecutionConfigurationProvider:
    """Resolve persisted settings while keeping live mode opt-in."""

    def __init__(self, source: BotConfigurationSource, *, allow_live: bool = False) -> None:
        self._source = source
        self.allow_live = allow_live

    def load(self, user_id: str, configuration_id: str) -> BotExecutionConfiguration:
        values = self._source.get_auto_trade_configuration(user_id, configuration_id)
        if values is None:
            raise BotConfigurationNotReadyError("auto-trade configuration not found")
        controls = values.get("robotControls")
        if not isinstance(controls, dict):
            raise BotConfigurationNotReadyError("robot controls are unavailable")
        if str(values.get("userId", "")) != user_id or str(values.get("id", "")) != configuration_id:
            raise BotConfigurationNotReadyError("configuration ownership mismatch")
        if not bool(controls.get("enabled")):
            raise BotConfigurationNotReadyError("auto-trade robot is disabled")
        paper_mode = bool(values.get("paperMode"))
        if not paper_mode and not self.allow_live:
            raise BotConfigurationNotReadyError("live auto-trading is not authorized")
        return BotExecutionConfiguration(
            id=str(values["id"]),
            user_id=str(values["userId"]),
            symbol=str(values["symbol"]).strip().upper(),
            timeframe=str(values["timeframe"]).strip().upper(),
            strategy=str(values["strategy"]).strip(),
            risk_per_trade=float(values["riskPerTrade"]),
            daily_loss_limit=float(values["dailyLossLimit"]),
            paper_mode=paper_mode,
            lot_size=float(controls["lotSize"]),
            stop_loss_pips=float(controls["stopLossPips"]),
            take_profit_pips=float(controls["takeProfitPips"]),
            version=str(values["updatedAt"]),
        )
