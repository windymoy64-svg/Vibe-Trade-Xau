"""Runtime forex pipeline integration."""

from src.trading.runtime_pipeline.contracts import (
    CandleOutcome,
    PipelineResult,
    PipelineStage,
    RuntimeEvent,
)
from src.trading.runtime_pipeline.event_log import RuntimeEventLog
from src.trading.runtime_pipeline.runner import RuntimeInputs, RuntimeMarketData, RuntimePipelineRunner
from src.trading.runtime_pipeline.mt5_wiring import MT5BrokerTransport, MT5RuntimeInputs

__all__ = [
    "CandleOutcome",
    "PipelineResult",
    "PipelineStage",
    "RuntimeEvent",
    "RuntimeEventLog",
    "RuntimeInputs",
    "MT5BrokerTransport",
    "MT5RuntimeInputs",
    "RuntimeMarketData",
    "RuntimePipelineRunner",
]
