"""Validated immutable configuration shared by every production runtime stage."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    ema_fast: int = Field(default=20, alias="EMA_FAST", gt=0)
    ema_medium: int = Field(default=50, alias="EMA_MEDIUM", gt=0)
    ema_slow: int = Field(default=200, alias="EMA_SLOW", gt=0)
    atr_period: int = Field(default=14, alias="ATR_PERIOD", gt=0)
    atr_multiplier: float = Field(default=1.0, alias="ATR_MULTIPLIER", gt=0)
    rsi_period: int = Field(default=14, alias="RSI_PERIOD", gt=0)
    rsi_long_threshold: float = Field(default=55.0, alias="RSI_LONG_THRESHOLD", ge=0, le=100)
    rsi_short_threshold: float = Field(default=45.0, alias="RSI_SHORT_THRESHOLD", ge=0, le=100)
    macd_fast: int = Field(default=12, alias="MACD_FAST", gt=0)
    macd_slow: int = Field(default=26, alias="MACD_SLOW", gt=0)
    macd_signal: int = Field(default=9, alias="MACD_SIGNAL", gt=0)
    volume_lookback: int = Field(default=20, alias="VOLUME_LOOKBACK", gt=0)
    trend_lookback: int = Field(default=200, alias="TREND_LOOKBACK", gt=0)
    rr: float = Field(default=2.0, alias="RR", gt=0)
    stop_distance: float = Field(default=10.0, alias="STOP_DISTANCE", gt=0)
    risk_percent: float = Field(default=0.01, alias="RISK_PERCENT", gt=0, le=100)
    session_filter: bool = Field(default=False, alias="SESSION_FILTER")
    volatility_filter: bool = Field(default=False, alias="VOLATILITY_FILTER")

    @model_validator(mode="after")
    def _relationships(self) -> "RuntimeConfig":
        if not self.ema_fast < self.ema_medium < self.ema_slow:
            raise ValueError("EMA periods must satisfy EMA_FAST < EMA_MEDIUM < EMA_SLOW")
        if self.macd_fast >= self.macd_slow:
            raise ValueError("MACD_FAST must be less than MACD_SLOW")
        if self.rsi_short_threshold > self.rsi_long_threshold:
            raise ValueError("RSI_SHORT_THRESHOLD must not exceed RSI_LONG_THRESHOLD")
        return self
