"""Tests for automatic recommendation generation from diagnostic patterns."""

from __future__ import annotations

import pytest

from src.diagnostics.recommendation_service import DiagnosticRecommendationService
from src.diagnostics.store import DiagnosticsStore


def _insert_pattern(
    store: DiagnosticsStore,
    pattern_id: str,
    user_id: str,
    category: str,
    *,
    percentage: float = 50.0,
    confidence: float = 90.0,
) -> None:
    store._conn.execute(
        "INSERT INTO pola_kekalahan VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            pattern_id, user_id, f"{category} pattern", category, "Evidence", 5,
            percentage, confidence, "HIGH", "[]", 0.0, "2026-07-01",
            "2026-07-31", "2026-07-31T12:00:00Z", "now", "now",
        ),
    )
    store._conn.commit()


def test_generate_and_persist_is_deterministic_user_scoped_and_idempotent(tmp_path):
    with DiagnosticsStore(tmp_path / "recommendations.db") as store:
        _insert_pattern(store, "pattern_trend", "alice", "TREND")
        _insert_pattern(store, "pattern_session", "alice", "SESSION", percentage=20)
        _insert_pattern(store, "pattern_bob", "bob", "REGIME")
        service = DiagnosticRecommendationService(store)

        first = service.generate_and_persist("alice")
        second = service.generate_and_persist("alice")
        persisted = store.persisted_recommendations("alice")

        assert [item["id"] for item in first["recommendations"]] == [
            item["id"] for item in second["recommendations"]
        ]
        assert [item["id"] for item in persisted] == [
            "rec_pattern_trend", "rec_pattern_session",
        ]
        assert store.persisted_recommendations("bob") == []


def test_regeneration_preserves_applied_status_and_removes_stale_rows(tmp_path):
    with DiagnosticsStore(tmp_path / "recommendations.db") as store:
        _insert_pattern(store, "pattern_trend", "alice", "TREND")
        service = DiagnosticRecommendationService(store)
        service.generate_and_persist("alice")
        store.set_recommendation_applied("alice", "rec_pattern_trend", True)

        refreshed = service.generate_and_persist("alice")
        assert refreshed["recommendations"][0]["status"] == "APPLIED"
        assert store.persisted_recommendations("alice")[0]["status"] == "APPLIED"

        store._conn.execute("DELETE FROM pola_kekalahan WHERE user_id = 'alice'")
        store._conn.commit()
        empty = service.generate_and_persist("alice")
        assert empty["recommendations"] == []
        assert store.persisted_recommendations("alice") == []


@pytest.mark.parametrize(
    ("severity", "loss_share", "expected"),
    [
        ("HIGH", 40.0, "CRITICAL"),
        ("HIGH", 39.99, "HIGH"),
        ("MEDIUM", 100.0, "HIGH"),
        ("LOW", 100.0, "MEDIUM"),
    ],
)
def test_calculate_priority_applies_evidence_thresholds(severity, loss_share, expected):
    assert DiagnosticRecommendationService.calculate_priority(severity, loss_share) == expected


def test_calculate_priority_rejects_invalid_evidence():
    with pytest.raises(ValueError, match="Unsupported pattern severity"):
        DiagnosticRecommendationService.calculate_priority("UNKNOWN", 50.0)
    with pytest.raises(ValueError, match="between 0 and 100"):
        DiagnosticRecommendationService.calculate_priority("HIGH", 101.0)


def test_calculate_expected_impact_weights_confidence_and_caps_result():
    calculate = DiagnosticRecommendationService.calculate_expected_impact
    assert calculate(40.0, 75.0) == 15.0
    assert calculate(100.0, 100.0) == 50.0
    with pytest.raises(ValueError, match="confidence must be between 0 and 100"):
        calculate(40.0, -1.0)


def test_recommendations_use_priority_impact_and_confidence_tie_breakers(tmp_path):
    with DiagnosticsStore(tmp_path / "recommendations.db") as store:
        _insert_pattern(store, "pattern_low_impact", "alice", "SESSION", percentage=40, confidence=80)
        _insert_pattern(store, "pattern_high_impact", "alice", "MOMENTUM", percentage=50, confidence=80)
        service = DiagnosticRecommendationService(store)

        recommendations = service.list_recommendations("alice")["recommendations"]

        assert [item["id"] for item in recommendations] == [
            "rec_pattern_high_impact", "rec_pattern_low_impact",
        ]
        assert [item["expectedImpact"] for item in recommendations] == [20.0, 16.0]