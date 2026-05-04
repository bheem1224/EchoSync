from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

Base = declarative_base()

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    namespace = Column(String, nullable=False)
    plugin_id = Column(Integer, nullable=True)
    display_name = Column(String)
    service_type = Column(String)
    description = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True) 

    configs = relationship("ServiceConfig", back_populates="service", cascade="all, delete-orphan")
    accounts = relationship("Account", back_populates="service", cascade="all, delete-orphan")

class ServiceConfig(Base):
    __tablename__ = "service_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    config_key = Column(String, nullable=False)
    config_value = Column(Text)
    is_sensitive = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    service = relationship("Service", back_populates="configs")

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    account_name = Column(String)
    user_id = Column(String)
    account_email = Column(String)
    is_active = Column(Boolean, default=False)
    is_authenticated = Column(Boolean, default=False)
    last_authenticated_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    service = relationship("Service", back_populates="accounts")
    token = relationship("AccountToken", back_populates="account", uselist=False, cascade="all, delete-orphan")

class AccountToken(Base):
    __tablename__ = "account_tokens"
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), unique=True, nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    token_type = Column(String, default="Bearer")
    expires_at = Column(Integer)
    scope = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    account = relationship("Account", back_populates="token")

class SystemSetting(Base):
    __tablename__ = "system_settings"
    key = Column(String, primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class QualityProfile(Base):
    __tablename__ = "quality_profiles"
    id = Column(String, primary_key=True)
    name = Column(String)
    prefer_max_quality = Column(Boolean, default=False)

    steps = relationship("QualityProfileStep", back_populates="profile", cascade="all, delete-orphan")

class QualityProfileStep(Base):
    __tablename__ = "quality_profile_steps"
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(String, ForeignKey("quality_profiles.id", ondelete="CASCADE"), nullable=False)
    priority = Column(Integer, nullable=False)
    rules = Column(JSON) 

    profile = relationship("QualityProfile", back_populates="steps")

class PKCESession(Base):
    __tablename__ = "pkce_sessions"
    pkce_id = Column(String, primary_key=True)
    service = Column(String, nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    code_verifier = Column(String, nullable=False)
    code_challenge = Column(String, nullable=False)
    redirect_uri = Column(String, nullable=False)
    client_id = Column(String, nullable=False)
    created_at = Column(Integer, nullable=False)
    expires_at = Column(Integer, nullable=False)

class AccountMapping(Base):
    __tablename__ = "account_mappings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    media_server_id = Column(String, nullable=False)
    managed_user_id = Column(String, nullable=False)
    provider_id = Column(String, nullable=False)
    provider_account_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class PluginSnapshot(Base):
    __tablename__ = "plugin_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(String, nullable=False, unique=True)
    snapshot_data = Column(Text, nullable=False)
    expires_at = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.now())
