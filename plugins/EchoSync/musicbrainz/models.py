from sqlalchemy import Column, String, JSON, DateTime
from datetime import datetime, timezone
from core.nexus_framework.plugin_orm import get_plugin_base
from core.nexus_framework.plugin_SDK import sdk

Base = get_plugin_base("musicbrainz")

class PluginMusicbrainzCache(Base):
    __tablename__ = 'cache'

    id = Column(String, primary_key=True)
    lookup_hash = Column(String, index=True, nullable=False)
    mbid = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

def init_db():
    working_db = sdk.storage.get_working_database()
    Base.metadata.create_all(bind=working_db.engine)
