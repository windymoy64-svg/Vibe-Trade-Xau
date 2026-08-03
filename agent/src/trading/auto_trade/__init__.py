"""Evidence-gated auto-trading services."""

from .signal_validator import (
    DiagnosticSignalValidationService,
    SignalValidationContext,
    SignalValidationResult,
)
from .broker_order_service import (
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerOrderService,
    DuplicateBrokerOrderError,
)
from .execution_queue import ScheduledTrade, TradeExecutionQueue
from .parameter_validator import (
    TradingParameterLimits,
    TradingParameters,
    TradingParameterValidationService,
)
from .configuration_provider import (
    BotConfigurationNotReadyError,
    BotExecutionConfiguration,
    BotExecutionConfigurationProvider,
)
from .broker_connection import (
    BrokerConnectionVerification,
    BrokerConnectionVerificationService,
    BrokerCredentialNotFoundError,
)
from .execution_logger import (
    AutoTradeExecutionLogger,
    ExecutionLogEvent,
    ExecutionLogUserNotFoundError,
)
from .credential_encryption import (
    BrokerCredentialEncryptionService,
    CredentialEncryptionConfigurationError,
    EncryptedCredential,
)

__all__ = [
    "DiagnosticSignalValidationService",
    "BrokerOrderRequest",
    "BrokerOrderResult",
    "BrokerOrderService",
    "DuplicateBrokerOrderError",
    "ScheduledTrade",
    "TradeExecutionQueue",
    "TradingParameterLimits",
    "TradingParameters",
    "TradingParameterValidationService",
    "BotConfigurationNotReadyError",
    "BotExecutionConfiguration",
    "BotExecutionConfigurationProvider",
    "BrokerConnectionVerification",
    "BrokerConnectionVerificationService",
    "BrokerCredentialNotFoundError",
    "AutoTradeExecutionLogger",
    "ExecutionLogEvent",
    "ExecutionLogUserNotFoundError",
    "BrokerCredentialEncryptionService",
    "CredentialEncryptionConfigurationError",
    "EncryptedCredential",
    "SignalValidationContext",
    "SignalValidationResult",
]
