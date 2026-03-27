#!/usr/bin/env python3

"""SQLAlchemy models for config.db schema migration support.

Runtime config I/O continues to use sqlite3 in config_database.py. These models
exist so Alembic can autogenerate and track schema changes for config.db.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ConfigBase(DeclarativeBase):
    """Base metadata class for config database models."""


class Service(ConfigBase):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String)
    service_type: Mapped[Optional[str]] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[Optional[int]] = mapped_column(Integer)
    updated_at: Mapped[Optional[int]] = mapped_column(Integer)


class ServiceConfig(ConfigBase):
    __tablename__ = "service_config"
    __table_args__ = (
        UniqueConstraint("service_id", "config_key", name="uq_service_config"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False
    )
    config_key: Mapped[str] = mapped_column(String, nullable=False)
    config_value: Mapped[Optional[str]] = mapped_column(String)
    is_sensitive: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[Optional[int]] = mapped_column(Integer)
    updated_at: Mapped[Optional[int]] = mapped_column(Integer)


class Account(ConfigBase):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False
    )
    account_name: Mapped[Optional[str]] = mapped_column(String)
    display_name: Mapped[Optional[str]] = mapped_column(String)
    user_id: Mapped[Optional[str]] = mapped_column(String)
    account_email: Mapped[Optional[str]] = mapped_column(String)
    is_active: Mapped[Optional[int]] = mapped_column(Integer)
    is_authenticated: Mapped[Optional[int]] = mapped_column(Integer)
    last_authenticated_at: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[Optional[int]] = mapped_column(Integer)
    updated_at: Mapped[Optional[int]] = mapped_column(Integer)


class AccountToken(ConfigBase):
    __tablename__ = "account_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    access_token: Mapped[str] = mapped_column(String, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(String)
    token_type: Mapped[Optional[str]] = mapped_column(String)
    expires_at: Mapped[Optional[int]] = mapped_column(Integer)
    scope: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[Optional[int]] = mapped_column(Integer)
    updated_at: Mapped[Optional[int]] = mapped_column(Integer)


class AccountMetadata(ConfigBase):
    __tablename__ = "account_metadata"
    __table_args__ = (
        UniqueConstraint("account_id", "metadata_key", name="uq_account_metadata"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    metadata_key: Mapped[str] = mapped_column(String, nullable=False)
    metadata_value: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[Optional[int]] = mapped_column(Integer)
    updated_at: Mapped[Optional[int]] = mapped_column(Integer)


class PkceSession(ConfigBase):
    __tablename__ = "pkce_sessions"

    pkce_id: Mapped[str] = mapped_column(String, primary_key=True)
    service: Mapped[str] = mapped_column(String, nullable=False)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    code_verifier: Mapped[str] = mapped_column(String, nullable=False)
    code_challenge: Mapped[str] = mapped_column(String, nullable=False)
    redirect_uri: Mapped[str] = mapped_column(String, nullable=False)
    client_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[int] = mapped_column(Integer, nullable=False)


__all__ = [
    "ConfigBase",
    "Service",
    "ServiceConfig",
    "Account",
    "AccountToken",
    "AccountMetadata",
    "PkceSession",
]
