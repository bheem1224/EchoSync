from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, String

from core.nexus_framework.plugin_orm import get_plugin_base
from core.nexus_framework.plugin_SDK import sdk

Base = get_plugin_base("musicbrainz")


class PluginMusicbrainzCache(Base):
    __tablename__ = "cache"

    id = Column(String, primary_key=True)
    lookup_hash = Column(String, index=True, nullable=False)
    mbid = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


def init_db():
    with sdk.db.get_plugin_session() as session:
        Base.metadata.create_all(bind=session.bind)
