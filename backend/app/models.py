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
