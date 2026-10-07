"""Request schemas (validated input). Money arrives in taka from the client and is converted to paisa."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

GroupType = Literal["friends", "roommates", "trip", "event", "other"]


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)


class LoginIn(BaseModel):
    # Not validated as an address: an unknown or malformed email simply fails as "incorrect".
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class DeleteAccountIn(BaseModel):
    confirm: str = Field(max_length=10)


class ProfileUpdateIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)


class GroupCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=280)
    group_type: GroupType = "friends"
    member_names: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("member_names")
    @classmethod
    def _clean_names(cls, v: list[str]) -> list[str]:
        return [n.strip()[:80] for n in v if n and n.strip()]


class GroupUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=280)
    group_type: GroupType | None = None
    monthly_budget: float | None = Field(default=None, ge=0, le=10_000_000)


class MemberAddIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)


class JoinIn(BaseModel):
    claim_member_id: str | None = None


class ExpenseCreateIn(BaseModel):
    description: str = Field(min_length=1, max_length=200)
    amount: float = Field(gt=0, le=100_000_000)
    payer_member_id: str
    participant_ids: list[str] = Field(default_factory=list, max_length=50)
    occurred_at: datetime | None = None
    subcategory: str | None = None
    merchant: str | None = Field(default=None, max_length=120)
    payment_method: Literal["cash", "mobile_wallet", "card", "bank_transfer"] = "mobile_wallet"
    split_method: Literal["equal", "percentage", "exact"] = "equal"
    split_values: dict[str, float] | None = None
    notes: str | None = Field(default=None, max_length=500)


class ExpenseUpdateIn(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=200)
    amount: float | None = Field(default=None, gt=0, le=100_000_000)
    payer_member_id: str | None = None
    participant_ids: list[str] | None = None
    occurred_at: datetime | None = None
    subcategory: str | None = None
    notes: str | None = Field(default=None, max_length=500)


class ReviewIn(BaseModel):
    action: Literal["valid", "dismiss", "reopen"]


class CategoryIn(BaseModel):
    subcategory: str


class CategorizeIn(BaseModel):
    text: str = Field(min_length=1, max_length=240)
    group_id: str | None = None


class SettlementIn(BaseModel):
    from_member_id: str
    to_member_id: str
    amount: float = Field(gt=0, le=100_000_000)
    note: str | None = Field(default=None, max_length=200)
    occurred_at: datetime | None = None


class GoalIn(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=280)
    target: float = Field(gt=0, le=100_000_000)
    deadline: date
    start_date: date | None = None


class GoalUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=280)
    target: float | None = Field(default=None, gt=0, le=100_000_000)
    deadline: date | None = None
    status: Literal["active", "achieved", "archived"] | None = None


class ContributionIn(BaseModel):
    member_id: str
    amount: float = Field(gt=0, le=100_000_000)
    note: str | None = Field(default=None, max_length=200)
    occurred_at: datetime | None = None


class WhatIfIn(BaseModel):
    category_changes: dict[str, float] = Field(default_factory=dict)
    overall_change_pct: float = Field(default=0, ge=-90, le=300)
    extra_monthly_contribution: float = Field(default=0, ge=0, le=10_000_000)
    goal_id: str | None = None
    redirect_savings: bool = True

    @field_validator("category_changes")
    @classmethod
    def _bounds(cls, v: dict[str, float]) -> dict[str, float]:
        if len(v) > 20:
            raise ValueError("Too many categories.")
        return {k[:40]: max(-100.0, min(300.0, float(p))) for k, p in v.items()}


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class CopilotIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    history: list[ChatTurn] = Field(default_factory=list, max_length=8)


class RecommendationActionIn(BaseModel):
    action: Literal["accepted", "dismissed"]


# ----------------------------------------------------------------------------- mobile wallet (MFS)
class StatementIn(BaseModel):
    csv: str = Field(min_length=1, max_length=300_000)


class ImportSelection(BaseModel):
    txn_id: str = Field(min_length=1, max_length=64)
    action: Literal["expense", "settlement"]
    subcategory: str | None = Field(default=None, max_length=60)
    to_member_id: str | None = Field(default=None, max_length=36)
    description: str | None = Field(default=None, max_length=200)


class StatementImportIn(StatementIn):
    selections: list[ImportSelection] = Field(min_length=1, max_length=200)
    participant_ids: list[str] = Field(min_length=1, max_length=50)


class PaymentRequestIn(BaseModel):
    purpose: Literal["settlement", "goal_contribution"]
    amount: float = Field(gt=0, le=100_000_000)
    payee_member_id: str | None = Field(default=None, max_length=36)
    goal_id: str | None = Field(default=None, max_length=36)
    payer_member_id: str | None = Field(default=None, max_length=36)  # set to request money from someone


class SandboxActionIn(BaseModel):
    action: Literal["approve", "decline"]
