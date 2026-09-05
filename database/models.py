import time

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def current_epoch():
    return int(time.time())


class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    absolute_install_path = Column(String, nullable=True)
    loaded_modules = Column(String, nullable=True)
    version = Column(String, nullable=True)
    plugin_id = Column(Integer, nullable=True)
    service_type = Column(String)
    description = Column(Text)
    created_at = Column(Integer, default=current_epoch)
    updated_at = Column(Integer, default=current_epoch, onupdate=current_epoch)
    is_active = Column(Boolean, default=True)
    beta_opt_in = Column(Boolean, nullable=True, default=None)
    previous_version_path = Column(String, nullable=True)
    verified_source = Column(Boolean, default=False, server_default="0")
    privileged_mode = Column(Boolean, default=False, server_default="0")
    permissions = Column(String, default="[]", server_default="[]")

    configs = relationship(
        "ServiceConfig", back_populates="service", cascade="all, delete-orphan"
    )
    accounts = relationship(
        "Account", back_populates="service", cascade="all, delete-orphan"
    )
    ui_components = relationship(
        "UIComponent",
        back_populates="service",
        foreign_keys="UIComponent.plugin_id",
        primaryjoin="Service.plugin_id == UIComponent.plugin_id",
    )


class ServiceConfig(Base):
    __tablename__ = "service_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(
        Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False
    )
    config_key = Column(String, nullable=False)
    config_value = Column(Text)
    is_sensitive = Column(Boolean, default=False)
    created_at = Column(Integer, default=current_epoch)
    updated_at = Column(Integer, default=current_epoch, onupdate=current_epoch)

    service = relationship("Service", back_populates="configs")


class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(
        Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False
    )
    account_name = Column(String)
    display_name = Column(String)
    user_id = Column(String)
    account_email = Column(String)
    is_active = Column(Boolean, default=False)
    is_authenticated = Column(Boolean, default=False)
    last_authenticated_at = Column(Integer)
    created_at = Column(Integer, default=current_epoch)
    updated_at = Column(Integer, default=current_epoch, onupdate=current_epoch)

    service = relationship("Service", back_populates="accounts")
    token = relationship(
        "AccountToken",
        back_populates="account",
        uselist=False,
        cascade="all, delete-orphan",
    )


class AccountToken(Base):
    __tablename__ = "account_tokens"
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(
        Integer,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    token_type = Column(String, default="Bearer")
    expires_at = Column(Integer)
    scope = Column(String)
    created_at = Column(Integer, default=current_epoch)
    updated_at = Column(Integer, default=current_epoch, onupdate=current_epoch)

    account = relationship("Account", back_populates="token")


class SystemSetting(Base):
    __tablename__ = "system_settings"
    key = Column(String, primary_key=True)
    value = Column(Text)
    updated_at = Column(Integer, default=current_epoch, onupdate=current_epoch)


class QualityProfile(Base):
    __tablename__ = "quality_profiles"
    id = Column(String, primary_key=True)
    name = Column(String)
    prefer_max_quality = Column(Boolean, default=False)

    steps = relationship(
        "QualityProfileStep", back_populates="profile", cascade="all, delete-orphan"
    )


class QualityProfileStep(Base):
    __tablename__ = "quality_profile_steps"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(
        String, ForeignKey("quality_profiles.id", ondelete="CASCADE"), nullable=False
    )
    priority = Column(Integer, nullable=False)
    rules = Column(JSON)

    profile = relationship("QualityProfile", back_populates="steps")


class PKCESession(Base):
    __tablename__ = "pkce_sessions"
    pkce_id = Column(String, primary_key=True)
    service = Column(String, nullable=False)
    account_id = Column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    code_verifier = Column(String, nullable=False)
    code_challenge = Column(String, nullable=False)
    redirect_uri = Column(String, nullable=False)
    client_id = Column(String, nullable=False)
    created_at = Column(Integer, nullable=False)
    expires_at = Column(Integer, nullable=False)


class AccountMapping(Base):
    __tablename__ = "account_mappings"
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 1. Generic Pointers: Both columns point directly to the accounts table
    source_account_id = Column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    mapped_account_id = Column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )

    created_at = Column(Integer, default=current_epoch)
    updated_at = Column(Integer, default=current_epoch, onupdate=current_epoch)

    # 2. Database-Level Deduplication & Safety Rules
    __table_args__ = (
        # Rule A: Prevent exact duplicate mappings (cannot map 5 to 6 twice)
        UniqueConstraint(
            "source_account_id", "mapped_account_id", name="uq_account_mapping"
        ),
        # Rule B: Prevent an account from mapping to itself (cannot map 5 to 5)
        CheckConstraint(
            "source_account_id != mapped_account_id", name="chk_no_self_mapping"
        ),
    )

    # 3. Optional ORM Relationships (makes querying in Python much easier)
    source_account = relationship("Account", foreign_keys=[source_account_id])
    mapped_account = relationship("Account", foreign_keys=[mapped_account_id])


class PluginSnapshot(Base):
    __tablename__ = "plugin_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(Integer, nullable=False, unique=True)
    snapshot_data = Column(Text, nullable=False)
    expires_at = Column(Integer, nullable=False)
    created_at = Column(Integer, default=current_epoch)


class UIComponent(Base):
    """Central UI Registry — all Web Component, Theme, and Dashboard awareness.

    Populated once at plugin boot/install from ui_manifest.json.
    Queried by the Svelte frontend via GET /api/ui/registry.
    """

    __tablename__ = "ui_components"
    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(
        Integer, nullable=True, index=True
    )  # CRC32 integer; nullable for core components
    tag_name = Column(String, unique=True, nullable=False)  # e.g. es-spotify-card
    component_type = Column(
        String, nullable=False, index=True
    )  # card, page, settings, theme
    entry_path = Column(String, nullable=False)  # static route path to compiled .js
    is_core = Column(Boolean, default=False, server_default="0")
    created_at = Column(Integer, default=current_epoch)
    updated_at = Column(Integer, default=current_epoch, onupdate=current_epoch)

    service = relationship(
        "Service",
        back_populates="ui_components",
        foreign_keys=[plugin_id],
        primaryjoin="UIComponent.plugin_id == Service.plugin_id",
        viewonly=True,
    )
