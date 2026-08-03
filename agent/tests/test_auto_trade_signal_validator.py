from src.trading.auto_trade import DiagnosticSignalValidationService, SignalValidationContext


class PatternSource:
    def __init__(self, patterns):
        self.patterns = patterns
        self.requested_user = None

    def loss_pattern_analysis(self, user_id):
        self.requested_user = user_id
        return {"patterns": self.patterns}


def _context(**overrides):
    return SignalValidationContext(**{
        "user_id": "alice", "direction": "BUY", "trend": "BULLISH",
        "market_regime": "TRENDING", "session": "LONDON", "rsi": 55.0,
        **overrides,
    })


def test_signal_passes_when_active_evidence_guardrails_are_satisfied():
    source = PatternSource([
        {"id": "trend", "category": "TREND", "severity": "HIGH", "confidence": 90},
        {"id": "weak", "category": "SESSION", "severity": "MEDIUM", "confidence": 99},
    ])

    result = DiagnosticSignalValidationService(source).validate(_context())

    assert result.accepted is True
    assert result.evidence_pattern_ids == ()
    assert source.requested_user == "alice"


def test_signal_is_blocked_with_auditable_evidence_ids():
    source = PatternSource([
        {"id": "trend-loss", "category": "TREND", "severity": "HIGH", "confidence": 91},
        {"id": "session-loss", "category": "SESSION", "severity": "HIGH", "confidence": 82},
        {"id": "low-confidence", "category": "REGIME", "severity": "HIGH", "confidence": 50},
    ])

    result = DiagnosticSignalValidationService(source).validate(
        _context(trend="BEARISH", session="ASIA", market_regime="RANGING"),
    )

    assert result.accepted is False
    assert result.evidence_pattern_ids == ("trend-loss", "session-loss")
    assert any("conflicts" in reason for reason in result.reasons)
    assert any("Asia" in reason for reason in result.reasons)


def test_momentum_guard_blocks_only_overextended_signal_side():
    source = PatternSource([
        {"id": "momentum", "category": "MOMENTUM", "severity": "HIGH", "confidence": 80},
    ])
    service = DiagnosticSignalValidationService(source)

    assert service.validate(_context(rsi=71)).accepted is False
    assert service.validate(_context(direction="SELL", trend="BEARISH", rsi=71)).accepted is True
