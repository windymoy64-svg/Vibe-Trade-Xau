"""Ticket-pinned, side-effect-free MT5 position reconciliation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import UUID

from src.trading.forex_positions.contracts import (
    AccountPolicy,
    DealEntry,
    DealHistorySnapshot,
    Direction,
    MT5PositionEntry,
    MT5PositionSnapshot,
    PendingOrderEntry,
    PendingOrdersSnapshot,
    PositionLifecycle,
    PositionStateSnapshot,
    _canonical_json,
)
from src.trading.forex_risk import ApprovalStatus, ApprovedOrderPlan
from src.trading.forex_signals.engine import _deterministic_uuid7


class PositionManagerError(ValueError):
    pass


class DuplicateIntentError(PositionManagerError):
    pass


class DuplicateTicketError(PositionManagerError):
    pass


class InconsistentMT5StateError(PositionManagerError):
    pass


@dataclass(frozen=True)
class OwnershipPolicy:
    strategy_name: str
    strategy_version: str
    magic_number: int
    comment_prefix: str
    account_policy: AccountPolicy = AccountPolicy.HEDGING
    allow_manual_positions: bool = False


class RuntimeForexPositionManager:
    """Reconcile approved intent against caller-supplied immutable MT5 evidence."""

    def __init__(self, ownership: OwnershipPolicy) -> None:
        if not ownership.strategy_name or not ownership.strategy_version or not ownership.comment_prefix:
            raise ValueError("ownership identity must be complete")
        self.ownership = ownership
        self._seen_intents: set[UUID] = set()

    def reconcile(
        self,
        plan: ApprovedOrderPlan,
        positions: MT5PositionSnapshot,
        pending_orders: PendingOrdersSnapshot,
        deals: DealHistorySnapshot,
    ) -> PositionStateSnapshot:
        if not isinstance(plan, ApprovedOrderPlan):
            raise PositionManagerError("missing approved order plan")
        if not all(isinstance(value, expected) for value, expected in (
            (positions, MT5PositionSnapshot),
            (pending_orders, PendingOrdersSnapshot),
            (deals, DealHistorySnapshot),
        )):
            raise PositionManagerError("invalid MT5 snapshot contract")
        if plan.intent_id in self._seen_intents:
            raise DuplicateIntentError("duplicated intent")
        self._validate_unique_tickets(positions, pending_orders, deals)

        owned_positions = tuple(item for item in positions.positions if self._owned(item))
        owned_orders = tuple(item for item in pending_orders.orders if self._owned(item))
        owned_deals = tuple(item for item in deals.deals if self._owned(item))
        self._reject_claimed_foreign(plan, positions, pending_orders, deals)
        if self.ownership.account_policy is AccountPolicy.NETTING:
            symbol_positions = tuple(item for item in owned_positions if item.symbol == plan.symbol)
            if len(symbol_positions) > 1:
                raise InconsistentMT5StateError("netting policy found multiple owned symbol positions")

        matched_positions = self._match_positions(plan, owned_positions, owned_deals)
        matched_orders = tuple(item for item in owned_orders if item.intent_id == plan.intent_id)
        matched_deals = tuple(item for item in owned_deals if item.intent_id == plan.intent_id)
        if len(matched_positions) > 1:
            raise InconsistentMT5StateError("intent resolves to multiple MT5 position tickets")
        if len(matched_orders) > 1:
            raise InconsistentMT5StateError("intent resolves to multiple pending order tickets")

        state = self._derive(plan, matched_positions, matched_orders, matched_deals)
        snapshot = self._build(plan, positions, pending_orders, deals, state)
        self._seen_intents.add(plan.intent_id)
        return snapshot

    @classmethod
    def replay(
        cls,
        ownership: OwnershipPolicy,
        inputs: tuple[tuple[ApprovedOrderPlan, MT5PositionSnapshot, PendingOrdersSnapshot, DealHistorySnapshot], ...]
        | list[tuple[ApprovedOrderPlan, MT5PositionSnapshot, PendingOrdersSnapshot, DealHistorySnapshot]],
    ) -> tuple[PositionStateSnapshot, ...]:
        manager = cls(ownership)
        return tuple(manager.reconcile(*item) for item in inputs)

    def _owned(self, record: MT5PositionEntry | PendingOrderEntry | DealEntry) -> bool:
        return (
            record.magic_number == self.ownership.magic_number
            and record.comment.startswith(self.ownership.comment_prefix)
            and record.strategy_name == self.ownership.strategy_name
            and record.strategy_version == self.ownership.strategy_version
        )

    def _reject_claimed_foreign(self, plan, positions, orders, deals) -> None:  # type: ignore[no-untyped-def]
        records = (*positions.positions, *orders.orders, *deals.deals)
        if any(record.intent_id == plan.intent_id and not self._owned(record) for record in records):
            raise PositionManagerError("ownership mismatch for claimed intent")

    @staticmethod
    def _validate_unique_tickets(positions, orders, deals) -> None:  # type: ignore[no-untyped-def]
        for name, tickets in (
            ("position", [item.ticket for item in positions.positions]),
            ("order", [item.ticket for item in orders.orders]),
            ("deal", [item.ticket for item in deals.deals]),
        ):
            if len(tickets) != len(set(tickets)):
                raise DuplicateTicketError(f"duplicated MT5 {name} ticket")

    @staticmethod
    def _match_positions(plan, positions, deals):  # type: ignore[no-untyped-def]
        linked_tickets = {deal.position_ticket for deal in deals if deal.intent_id == plan.intent_id and deal.position_ticket}
        return tuple(
            item for item in positions
            if item.intent_id == plan.intent_id or item.ticket in linked_tickets
        )

    @staticmethod
    def _derive(plan, positions, orders, deals):  # type: ignore[no-untyped-def]
        position = positions[0] if positions else None
        order = orders[0] if orders else None
        latest_deal = max(deals, key=lambda item: (item.deal_time, item.ticket)) if deals else None
        if plan.approval_status is ApprovalStatus.REJECTED or any(item.rejected for item in (*orders, *deals)):
            return PositionLifecycle.REJECTED, position, order, latest_deal
        if latest_deal and latest_deal.is_exit and position is None:
            return PositionLifecycle.CLOSED, None, order, latest_deal
        if position is not None:
            if order and order.is_exit:
                return PositionLifecycle.PENDING_EXIT, position, order, latest_deal
            if position.volume_lots < plan.volume_lots:
                return PositionLifecycle.PARTIALLY_FILLED, position, order, latest_deal
            if position.volume_lots > plan.volume_lots:
                raise InconsistentMT5StateError("position volume exceeds approved plan")
            return PositionLifecycle.OPEN, position, order, latest_deal
        if order is not None:
            return (
                PositionLifecycle.PENDING_EXIT if order.is_exit else PositionLifecycle.PENDING_ENTRY,
                None, order, latest_deal,
            )
        if latest_deal is not None and latest_deal.volume_lots < plan.volume_lots:
            return PositionLifecycle.PARTIALLY_FILLED, None, None, latest_deal
        return PositionLifecycle.PENDING_ENTRY, None, None, latest_deal

    def _build(self, plan, positions_snapshot, orders_snapshot, deals_snapshot, derived):  # type: ignore[no-untyped-def]
        lifecycle, position, order, deal = derived
        direction = position.direction if position else order.direction if order else deal.direction if deal else _plan_direction(plan)
        volume = position.volume_lots if position else deal.volume_lots if deal else 0.0
        entry = position.entry_price if position else deal.price if deal and deal.price > 0 else plan.entry_price
        open_time = position.open_time if position else deal.deal_time if deal and not deal.is_exit else None
        updated = max(positions_snapshot.captured_at, orders_snapshot.captured_at, deals_snapshot.captured_at)
        strategy_position_id = _deterministic_uuid7(
            plan.expiration,
            _canonical_json({"intent_id": str(plan.intent_id), "strategy": self.ownership.strategy_name, "symbol": plan.symbol}),
        )
        material = {
            "comment": f"{self.ownership.comment_prefix}{plan.intent_id}",
            "current_state": lifecycle.value,
            "direction": direction.value,
            "entry_price": entry,
            "intent_id": str(plan.intent_id),
            "last_update_time": updated.isoformat(),
            "magic_number": self.ownership.magic_number,
            "mt5_deal_ticket": deal.ticket if deal else None,
            "mt5_order_ticket": order.ticket if order else position.order_ticket if position else None,
            "mt5_position_ticket": position.ticket if position else deal.position_ticket if deal else None,
            "open_time": open_time.isoformat() if open_time else None,
            "plan_digest": plan.digest,
            "stop_loss": position.stop_loss if position else plan.stop_loss,
            "strategy_name": self.ownership.strategy_name,
            "strategy_position_id": str(strategy_position_id),
            "strategy_version": self.ownership.strategy_version,
            "symbol": plan.symbol,
            "take_profit": position.take_profit if position else plan.take_profit,
            "volume_lots": volume,
        }
        position_state_id = _deterministic_uuid7(updated, _canonical_json(material))
        replay_hash = hashlib.sha256(
            _canonical_json({**material, "position_state_id": str(position_state_id)}).encode("utf-8")
        ).hexdigest()
        return PositionStateSnapshot(
            position_state_id=position_state_id,
            strategy_position_id=strategy_position_id,
            symbol=plan.symbol,
            strategy_name=self.ownership.strategy_name,
            strategy_version=self.ownership.strategy_version,
            magic_number=self.ownership.magic_number,
            comment=material["comment"],
            mt5_position_ticket=material["mt5_position_ticket"],
            mt5_order_ticket=material["mt5_order_ticket"],
            mt5_deal_ticket=material["mt5_deal_ticket"],
            current_state=lifecycle,
            direction=direction,
            volume_lots=volume,
            entry_price=entry,
            stop_loss=material["stop_loss"],
            take_profit=material["take_profit"],
            open_time=open_time,
            last_update_time=updated,
            replay_hash=replay_hash,
        )


def _plan_direction(plan: ApprovedOrderPlan) -> Direction:
    if plan.action in {"OPEN_LONG", "REVERSE_TO_LONG"}:
        return Direction.LONG
    if plan.action in {"OPEN_SHORT", "REVERSE_TO_SHORT"}:
        return Direction.SHORT
    return Direction.NONE
