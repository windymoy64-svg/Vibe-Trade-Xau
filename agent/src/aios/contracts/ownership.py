"""Ownership metadata for governed resources."""

from __future__ import annotations

from pydantic import field_validator

from src.aios.contracts.identifiers import FrozenContract, validate_identifier_segment


class Ownership(FrozenContract):
    """Required accountable ownership with optional control owners."""

    technical_owner: str
    business_owner: str
    risk_owner: str | None = None
    data_steward: str | None = None
    cost_center: str | None = None
    on_call: str | None = None

    @field_validator("technical_owner", "business_owner")
    @classmethod
    def _required_owner(cls, value: str) -> str:
        return validate_identifier_segment(value, field_name="owner")

    @field_validator("risk_owner", "data_steward", "cost_center", "on_call")
    @classmethod
    def _optional_owner(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_identifier_segment(value, field_name="owner")
