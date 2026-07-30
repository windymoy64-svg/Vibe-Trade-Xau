"""Acceptance tests for ticket-pinned runtime forex position reconciliation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.trading.forex_positions import (
    AccountPolicy,
    DealEntry,
    DealHistorySnapshot,
    Direction,
    DuplicateIntentError,
    DuplicateTicketError,
    InconsistentMT5StateError,
    MT5PositionEntry,
    MT5PositionSnapshot,
    OwnershipPolicy,
    PendingOrderEntry,
    PendingOrdersSnapshot,
    PositionLifecycle,
    RuntimeForexPositionManager,
)
from src.trading.forex_risk import ApprovalStatus, ApprovedOrderPlan

NOW = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
INTENT = UUID("019ff5bd-6d20-7e1d-8fee-32d2f34d3bc0")


def _plan(*, status: ApprovalStatus = ApprovalStatus.APPROVED) -> ApprovedOrderPlan:
    return ApprovedOrderPlan(
        order_plan_id=UUID("019ff5bd-6d20-7465-a13c-4a5376241e73"),
        intent_id=INTENT,
        symbol="XAUUSD",
        action="OPEN_LONG",
        volume_lots=0.1 if status is ApprovalStatus.APPROVED else 0.0,
        entry_price=2400.2,
        stop_loss=2390.2,
        take_profit=2420.2,
        risk_percent=1.0,
        risk_amount=100.0,
        reward_ratio=2.0,
        max_slippage=0.5,
        expiration=NOW + timedelta(minutes=1),
        approval_status=status,
        rejection_reason=None if status is ApprovalStatus.APPROVED else "RISK_REJECTED",
        replay_hash="a" * 64,
    )


def _owned(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "symbol": "XAUUSD",
        "magic_number": 862001,
        "comment": "vibe-forex:entry",
        "strategy_name": "forex-ema-macd-rsi-baseline",
        "strategy_version": "1.0.0",
        "intent_id": INTENT,
    }
    payload.update(changes)
    return payload


def _position(ticket: int = 1001, volume: float = 0.1, **changes: object) -> MT5PositionEntry:
    payload = {
        **_owned(),
        "ticket": ticket,
        "order_ticket": 2001,
        "deal_ticket": 3001,
        "direction": Direction.LONG,
        "volume_lots": volume,
        "entry_price": 2400.2,
        "stop_loss": 2390.2,
        "take_profit": 2420.2,
        "open_time": NOW - timedelta(minutes=1),
        "update_time": NOW,
    }
    payload.update(changes)
    return MT5PositionEntry(**payload)


def _order(ticket: int = 2001, **changes: object) -> PendingOrderEntry:
    payload = {
        **_owned(),
        "ticket": ticket,
        "direction": Direction.LONG,
        "requested_volume": 0.1,
        "remaining_volume": 0.1,
        "setup_time": NOW - timedelta(seconds=30),
    }
    payload.update(changes)
    return PendingOrderEntry(**payload)


def _deal(ticket: int = 3001, volume: float = 0.1, **changes: object) -> DealEntry:
    payload = {
        **_owned(),
        "ticket": ticket,
        "order_ticket": 2001,
        "position_ticket": 1001,
        "direction": Direction.LONG,
        "volume_lots": volume,
        "price": 2400.2,
        "deal_time": NOW,
    }
    payload.update(changes)
    return DealEntry(**payload)


def _snapshots(*, positions=(), orders=(), deals=()):  # type: ignore[no-untyped-def]
    return (
        MT5PositionSnapshot(captured_at=NOW, positions=tuple(positions)),
        PendingOrdersSnapshot(captured_at=NOW, orders=tuple(orders)),
        DealHistorySnapshot(captured_at=NOW, deals=tuple(deals)),
    )


def _policy(mode: AccountPolicy = AccountPolicy.HEDGING) -> OwnershipPolicy:
    return OwnershipPolicy(
        strategy_name="forex-ema-macd-rsi-baseline",
        strategy_version="1.0.0",
        magic_number=862001,
        comment_prefix="vibe-forex:",
        account_policy=mode,
    )


def test_startup_reconciliation_and_restart_recovery() -> None:
    evidence = _snapshots(positions=(_position(),), deals=(_deal(),))
    first = RuntimeForexPositionManager(_policy()).reconcile(_plan(), *evidence)
    recovered = RuntimeForexPositionManager(_policy()).reconcile(_plan(), *evidence)
    assert first.current_state is PositionLifecycle.OPEN
    assert first.mt5_position_ticket == 1001
    assert first.canonical_json() == recovered.canonical_json()


def test_ownership_filtering_and_claimed_mismatch_rejection() -> None:
    manual = _position(intent_id=None, magic_number=0, comment="manual", strategy_name="manual")
    snapshot = RuntimeForexPositionManager(_policy()).reconcile(_plan(), *_snapshots(positions=(manual,)))
    assert snapshot.current_state is PositionLifecycle.PENDING_ENTRY
    claimed_foreign = _position(magic_number=999)
    with pytest.raises(ValueError, match="ownership mismatch"):
        RuntimeForexPositionManager(_policy()).reconcile(_plan(), *_snapshots(positions=(claimed_foreign,)))


def test_duplicate_intent_and_ticket_rejection() -> None:
    manager = RuntimeForexPositionManager(_policy())
    manager.reconcile(_plan(), *_snapshots())
    with pytest.raises(DuplicateIntentError):
        manager.reconcile(_plan(), *_snapshots())
    with pytest.raises(DuplicateTicketError):
        RuntimeForexPositionManager(_policy()).reconcile(
            _plan(), *_snapshots(positions=(_position(), _position()))
        )


def test_partial_fill_and_rejected_order_lifecycle() -> None:
    partial = RuntimeForexPositionManager(_policy()).reconcile(
        _plan(), *_snapshots(positions=(_position(volume=0.04),), deals=(_deal(volume=0.04),))
    )
    assert partial.current_state is PositionLifecycle.PARTIALLY_FILLED
    rejected = RuntimeForexPositionManager(_policy()).reconcile(
        _plan(), *_snapshots(orders=(_order(rejected=True),))
    )
    assert rejected.current_state is PositionLifecycle.REJECTED
    rejected_plan = RuntimeForexPositionManager(_policy()).reconcile(
        _plan(status=ApprovalStatus.REJECTED), *_snapshots()
    )
    assert rejected_plan.current_state is PositionLifecycle.REJECTED


def test_inconsistent_overfill_is_rejected() -> None:
    with pytest.raises(InconsistentMT5StateError, match="exceeds approved"):
        RuntimeForexPositionManager(_policy()).reconcile(
            _plan(), *_snapshots(positions=(_position(volume=0.2),))
        )


def test_pending_entry_and_pending_exit_reconciliation() -> None:
    entry = RuntimeForexPositionManager(_policy()).reconcile(
        _plan(), *_snapshots(orders=(_order(),))
    )
    assert entry.current_state is PositionLifecycle.PENDING_ENTRY
    exit_state = RuntimeForexPositionManager(_policy()).reconcile(
        _plan(), *_snapshots(positions=(_position(),), orders=(_order(is_exit=True),))
    )
    assert exit_state.current_state is PositionLifecycle.PENDING_EXIT


def test_hedging_policy_selects_only_intent_owned_ticket() -> None:
    other = _position(ticket=1002, intent_id=UUID("019ff5bd-6d20-7e1d-8fee-32d2f34d3bc1"))
    state = RuntimeForexPositionManager(_policy(AccountPolicy.HEDGING)).reconcile(
        _plan(), *_snapshots(positions=(_position(), other))
    )
    assert state.mt5_position_ticket == 1001


def test_netting_policy_rejects_multiple_owned_symbol_positions() -> None:
    other = _position(ticket=1002, intent_id=UUID("019ff5bd-6d20-7e1d-8fee-32d2f34d3bc1"))
    with pytest.raises(InconsistentMT5StateError, match="netting"):
        RuntimeForexPositionManager(_policy(AccountPolicy.NETTING)).reconcile(
            _plan(), *_snapshots(positions=(_position(), other))
        )


def test_ticket_pinning_and_sltp_synchronization_state() -> None:
    position = _position(stop_loss=2391.0, take_profit=2419.0)
    state = RuntimeForexPositionManager(_policy()).reconcile(
        _plan(), *_snapshots(positions=(position,), deals=(_deal(),))
    )
    assert state.mt5_position_ticket == position.ticket
    assert state.stop_loss == 2391.0
    assert state.take_profit == 2419.0


def test_closed_lifecycle_from_exit_deal() -> None:
    state = RuntimeForexPositionManager(_policy()).reconcile(
        _plan(), *_snapshots(deals=(_deal(is_exit=True),))
    )
    assert state.current_state is PositionLifecycle.CLOSED
    assert state.mt5_position_ticket == 1001


def test_immutable_deterministic_replay_and_hash_stability() -> None:
    inputs = ((_plan(), *_snapshots(positions=(_position(),), deals=(_deal(),))),)
    first = RuntimeForexPositionManager.replay(_policy(), inputs)[0]
    second = RuntimeForexPositionManager.replay(_policy(), inputs)[0]
    assert first.canonical_json() == second.canonical_json()
    assert first.position_state_id.version == 7
    assert first.strategy_position_id.version == 7
    assert first.replay_hash == second.replay_hash
    assert len(first.replay_hash) == 64
    with pytest.raises(ValidationError):
        first.current_state = PositionLifecycle.FLAT  # type: ignore[misc]
