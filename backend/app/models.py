"""SQLAlchemy ORM models.

Money is stored as integer *paisa* (1 taka = 100 paisa) so every balance calculation is exact.
`occurred_at` timestamps are local (Asia/Dhaka) wall-clock times; audit timestamps are UTC.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .config import utc_now
from .db import Base


def new_id() -> str:
    return str(uuid.uuid4())


def new_invite_code() -> str:
    return secrets.token_urlsafe(8).replace("-", "x").replace("_", "y")[:10]


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    # local | supabase | demo | synthetic (synthetic = generated co-members, cannot sign in)
    auth_provider: Mapped[str] = mapped_column(String(16), default="local")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_color: Mapped[str] = mapped_column(String(16), default="#0057B8")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String(280))
    group_type: Mapped[str] = mapped_column(String(16), default="friends")  # friends|roommates|trip|event|other
    currency: Mapped[str] = mapped_column(String(3), default="BDT")
    invite_code: Mapped[str] = mapped_column(String(16), unique=True, default=new_invite_code)
    monthly_budget_paisa: Mapped[int | None] = mapped_column(BigInteger)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    # Incremented on every financial mutation; used as a cache key for analytics/ML results.
    data_version: Mapped[int] = mapped_column(Integer, default=0)

    members: Mapped[list[GroupMember]] = relationship(
        back_populates="group", cascade="all, delete-orphan", passive_deletes=True, order_by="GroupMember.joined_at"
    )


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_member_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    # Null for guest members (people tracked in the group who don't use the app).
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(16), default="member")  # owner|member|guest
    status: Mapped[str] = mapped_column(String(16), default="active")  # active|left
    avatar_color: Mapped[str] = mapped_column(String(16), default="#0057B8")
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    left_at: Mapped[datetime | None] = mapped_column(DateTime)

    group: Mapped[Group] = relationship(back_populates="members")


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (Index("ix_expense_group_time", "group_id", "occurred_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    payer_member_id: Mapped[str] = mapped_column(ForeignKey("group_members.id", ondelete="CASCADE"))
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    amount_paisa: Mapped[int] = mapped_column(BigInteger)
    description: Mapped[str] = mapped_column(String(200))
    merchant: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40))
    subcategory: Mapped[str] = mapped_column(String(60))
    expense_type: Mapped[str] = mapped_column(String(60))
    # ai = model suggestion accepted as-is, user = chosen/corrected by a person, feedback = learned from a past correction
    category_source: Mapped[str] = mapped_column(String(16), default="ai")
    category_confidence: Mapped[float | None] = mapped_column(Float)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    payment_method: Mapped[str] = mapped_column(String(24), default="mobile_wallet")
    split_method: Mapped[str] = mapped_column(String(16), default="equal")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    anomaly_score: Mapped[float | None] = mapped_column(Float)
    anomaly_status: Mapped[str] = mapped_column(String(16), default="none")  # none|flagged|valid|dismissed
    anomaly_reasons: Mapped[list | None] = mapped_column(JSON)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    splits: Mapped[list[ExpenseSplit]] = relationship(
        back_populates="expense", cascade="all, delete-orphan", passive_deletes=True
    )


class ExpenseSplit(Base):
    __tablename__ = "expense_splits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    expense_id: Mapped[str] = mapped_column(ForeignKey("expenses.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[str] = mapped_column(ForeignKey("group_members.id", ondelete="CASCADE"), index=True)
    share_paisa: Mapped[int] = mapped_column(BigInteger)

    expense: Mapped[Expense] = relationship(back_populates="splits")


class Settlement(Base):
    __tablename__ = "settlements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    from_member_id: Mapped[str] = mapped_column(ForeignKey("group_members.id", ondelete="CASCADE"))
    to_member_id: Mapped[str] = mapped_column(ForeignKey("group_members.id", ondelete="CASCADE"))
    amount_paisa: Mapped[int] = mapped_column(BigInteger)
    occurred_at: Mapped[datetime] = mapped_column(DateTime)
    note: Mapped[str | None] = mapped_column(String(200))
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String(280))
    target_paisa: Mapped[int] = mapped_column(BigInteger)
    start_date: Mapped[date] = mapped_column(Date)
    deadline: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active|achieved|archived
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class GoalContribution(Base):
    __tablename__ = "goal_contributions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    goal_id: Mapped[str] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[str] = mapped_column(ForeignKey("group_members.id", ondelete="CASCADE"))
    amount_paisa: Mapped[int] = mapped_column(BigInteger)
    occurred_at: Mapped[datetime] = mapped_column(DateTime)
    note: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class CategoryFeedback(Base):
    """A human correction of an AI category suggestion (training signal + per-group memory)."""

    __tablename__ = "category_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    group_id: Mapped[str | None] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    expense_id: Mapped[str | None] = mapped_column(ForeignKey("expenses.id", ondelete="SET NULL"))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    text: Mapped[str] = mapped_column(String(240))
    predicted_subcategory: Mapped[str | None] = mapped_column(String(60))
    corrected_subcategory: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class AIOutput(Base):
    """Audit log of AI outputs: what was predicted, by which model/version, with what confidence."""

    __tablename__ = "ai_outputs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    group_id: Mapped[str | None] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # categorization|anomaly|forecast|copilot|recommendation
    entity_id: Mapped[str | None] = mapped_column(String(36))
    model_name: Mapped[str] = mapped_column(String(80))
    model_version: Mapped[str] = mapped_column(String(40))
    confidence: Mapped[float | None] = mapped_column(Float)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class RecommendationAction(Base):
    """Whether people accepted or dismissed a recommendation — AI recommends, users decide."""

    __tablename__ = "recommendation_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    recommendation_key: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(16))  # accepted|dismissed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class PaymentRequest(Base):
    """A request to move money through a mobile wallet (settle a debt or fund a shared goal).

    GroupWise never holds money. The wallet provider executes the payment and reports the outcome
    with a signed event; only then is the settlement or goal contribution recorded.
    """

    __tablename__ = "payment_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(24))  # settlement|goal_contribution
    payer_member_id: Mapped[str] = mapped_column(ForeignKey("group_members.id", ondelete="CASCADE"))
    payee_member_id: Mapped[str | None] = mapped_column(ForeignKey("group_members.id", ondelete="CASCADE"))
    goal_id: Mapped[str | None] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"))
    amount_paisa: Mapped[int] = mapped_column(BigInteger)
    reference: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(24), default="sandbox")
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|paid|failed|cancelled|expired
    provider_txn_id: Mapped[str | None] = mapped_column(String(64))
    result_id: Mapped[str | None] = mapped_column(String(36))  # the settlement / contribution it produced
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class WalletImportItem(Base):
    """One wallet-statement transaction already imported into a group (prevents double counting)."""

    __tablename__ = "wallet_import_items"
    __table_args__ = (UniqueConstraint("group_id", "member_id", "provider_txn_id", name="uq_wallet_import_txn"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[str] = mapped_column(ForeignKey("group_members.id", ondelete="CASCADE"))
    provider_txn_id: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16))  # expense|settlement
    entity_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class ExperimentAssignment(Base):
    """Randomized arm of a group in a controlled pilot experiment (group-level A/B test)."""

    __tablename__ = "experiment_assignments"

    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    experiment: Mapped[str] = mapped_column(String(40))
    arm: Mapped[str] = mapped_column(String(16))  # control|treatment
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class ActivityDay(Base):
    """One row per user per day they used a group (retention, without tracking what they looked at)."""

    __tablename__ = "activity_days"
    __table_args__ = (UniqueConstraint("user_id", "group_id", "day", name="uq_activity_day"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date)


class AuditLog(Base):
    """Security-relevant events (who did what, from where, with what outcome). Never stores passwords,
    tokens or full emails; failed logins keep only a hash of the email for lockout."""

    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_action_time", "action", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    group_id: Mapped[str | None] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(40))
    outcome: Mapped[str] = mapped_column(String(16), default="ok")  # ok|denied|failed
    ip_hash: Mapped[str | None] = mapped_column(String(16))
    subject_hash: Mapped[str | None] = mapped_column(String(16), index=True)  # e.g. hashed email for failed logins
    detail: Mapped[dict | None] = mapped_column(JSON)


class RevokedToken(Base):
    """Signed-out session tokens (checked on every request until they would have expired anyway)."""

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class SessionEpoch(Base):
    """'Sign out everywhere': tokens issued before `not_before` are rejected."""

    __tablename__ = "session_epochs"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    not_before: Mapped[datetime] = mapped_column(DateTime)


class RateLimitEvent(Base):
    """Shared rate-limit counter so limits hold across several API instances (RATE_LIMIT_BACKEND=db)."""

    __tablename__ = "rate_limit_events"
    __table_args__ = (Index("ix_rate_key_time", "key", "at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    key: Mapped[str] = mapped_column(String(80))
    at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class OutboxEvent(Base):
    """Transactional outbox: domain events written in the same transaction as the change they describe,
    then relayed to other systems (a wallet partner, analytics) by scripts/outbox_relay.py."""

    __tablename__ = "outbox_events"
    __table_args__ = (Index("ix_outbox_unpublished", "published_at", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    topic: Mapped[str] = mapped_column(String(40))
    group_id: Mapped[str | None] = mapped_column(String(36), index=True)
    aggregate_id: Mapped[str | None] = mapped_column(String(36))
    payload: Mapped[dict] = mapped_column(JSON)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class GroupSetting(Base):
    """Per-group privacy choices. Group dynamics (who pays first, who settles late) is the most sensitive
    analysis, so any member can see this setting and the group can switch it off."""

    __tablename__ = "group_settings"

    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    dynamics_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36))


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("user_id", "dedupe_key", name="uq_notification_dedupe"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[str | None] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(24))  # expense|anomaly|goal|forecast|settlement|member|insight
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(String(400))
    link: Mapped[str | None] = mapped_column(String(200))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    dedupe_key: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
