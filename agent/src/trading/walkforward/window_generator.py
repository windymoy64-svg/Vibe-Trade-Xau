"""Leakage-safe chronological walk-forward window generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


class WindowType(str, Enum):
    ROLLING = "rolling"
    EXPANDING = "expanding"
    SLIDING = "sliding"


@dataclass(frozen=True)
class WalkForwardConfig:
    training_size: timedelta
    validation_size: timedelta
    forward_size: timedelta
    step_size: timedelta | None = None
    window_type: WindowType | str = WindowType.ROLLING
    minimum_trades: int = 1

    def __post_init__(self) -> None:
        kind = WindowType(self.window_type.lower()) if isinstance(self.window_type, str) else self.window_type
        object.__setattr__(self, "window_type", kind)
        durations = (self.training_size, self.validation_size, self.forward_size)
        if any(value <= timedelta(0) for value in durations):
            raise ValueError("training, validation, and forward sizes must be positive")
        step = self.step_size or (self.forward_size if kind is WindowType.SLIDING else self.forward_size)
        if step <= timedelta(0):
            raise ValueError("step_size must be positive")
        if step < self.forward_size:
            raise ValueError("step_size must be at least forward_size to prevent overlapping forward periods")
        if self.minimum_trades < 0:
            raise ValueError("minimum_trades must not be negative")
        object.__setattr__(self, "step_size", step)


@dataclass(frozen=True)
class Period:
    """A half-open UTC interval, preventing observations leaking at boundaries."""

    start: datetime
    end: datetime

    def contains(self, timestamp: datetime) -> bool:
        return self.start <= timestamp < self.end


@dataclass(frozen=True)
class WalkForwardWindow:
    index: int
    train: Period
    validation: Period
    forward: Period


class WindowGenerator:
    def __init__(self, config: WalkForwardConfig) -> None:
        self.config = config

    def generate(self, start: datetime, end: datetime) -> tuple[WalkForwardWindow, ...]:
        start, end = _utc(start), _utc(end)
        if start >= end:
            raise ValueError("dataset start must precede dataset end")
        windows: list[WalkForwardWindow] = []
        index = 1
        cursor = start
        while True:
            train_start = start if self.config.window_type is WindowType.EXPANDING else cursor
            train_end = cursor + self.config.training_size
            validation_end = train_end + self.config.validation_size
            forward_end = validation_end + self.config.forward_size
            if forward_end > end:
                break
            windows.append(
                WalkForwardWindow(
                    index,
                    Period(train_start, train_end),
                    Period(train_end, validation_end),
                    Period(validation_end, forward_end),
                )
            )
            cursor += self.config.step_size
            index += 1
        return tuple(windows)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("window boundaries must be timezone-aware")
    return value.astimezone(timezone.utc)
