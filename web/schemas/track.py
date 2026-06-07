from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class TrackSchema:
    id: Optional[str] = None
    title: Optional[str] = None
    artists: List[str] = field(default_factory=list)
    album: Optional[str] = None
    album_artist: Optional[str] = None
    duration_ms: Optional[int] = None
    isrc: Optional[str] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    plugin_refs: Dict[str, str] = field(default_factory=dict)
    source_plugin: Optional[str] = None
    metadata_richness: Optional[str] = None
    metadata_completeness: Optional[str] = None
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    file_size_bytes: Optional[int] = None
    added_at: Optional[str] = None
    file_format: Optional[str] = None
    musicbrainz_id: Optional[str] = None
    acoustid_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "artists": self.artists,
            "album": self.album,
            "album_artist": self.album_artist,
            "duration_ms": self.duration_ms,
            "isrc": self.isrc,
            "track_number": self.track_number,
            "disc_number": self.disc_number,
            "plugin_refs": self.plugin_refs,
            "source_plugin": self.source_plugin,
            "metadata_richness": self.metadata_richness,
            "metadata_completeness": self.metadata_completeness,
            "bitrate": self.bitrate,
            "sample_rate": self.sample_rate,
            "file_size_bytes": self.file_size_bytes,
            "added_at": self.added_at,
            "file_format": self.file_format,
            "musicbrainz_id": self.musicbrainz_id,
            "acoustid_id": self.acoustid_id,
        }
