"""Library adapter for summarizing library servers and canonical tracks."""

from typing import Dict, List

from plugins.plugin_system import plugin_registry, PluginScope
from core.provider_capabilities import get_provider_capabilities, MetadataRichness


def _metadata_completeness(richness: str) -> str:
    mapping = {
        'LOW': 'partial',
        'MEDIUM': 'standard',
        'HIGH': 'complete',
    }
    return mapping.get(richness, 'unknown')


class LibraryAdapter:
    def overview(self) -> Dict:
        """Summarize available library servers and canonical tracks.

        Returns:
            dict: servers, stats, tracks, artists
        """
        servers: List[Dict] = []
        tracks: List[Dict] = []

        library_plugins = plugin_registry.get_plugins_by_scope(PluginScope.LIBRARY)
        for plugin in library_plugins:
            if not getattr(plugin, "enabled", True):
                continue
            try:
                caps = get_provider_capabilities(plugin.name)
                richness = caps.metadata.name
            except KeyError:
                richness = MetadataRichness.MEDIUM.name

            servers.append({
                "name": plugin.name,
                "type": plugin.plugin_type.value,
                "metadata_richness": richness,
                "track_count": 0,
            })

            tracks.append({
                "id": f"track-{plugin.name}-1",
                "title": f"Sample from {plugin.name}",
                "artists": ["Sample Artist"],
                "album": "Sample Album",
                "duration_ms": 180000,
                "isrc": None,
                "provider_refs": {plugin.name: "sample-id"},
                "source_provider": plugin.name,
                "metadata_richness": richness,
                "metadata_completeness": _metadata_completeness(richness),
            })

        artists = self._aggregate_artists(tracks)
        stats = {
            "total_tracks": len(tracks),
            "total_artists": len(artists),
        }

        return {
            "servers": servers,
            "stats": stats,
            "tracks": tracks,
            "artists": artists,
        }

    @staticmethod
    def _aggregate_artists(tracks: List[Dict]) -> List[Dict]:
        counts: Dict[str, int] = {}
        for t in tracks:
            for artist in t.get("artists", []) or ["Unknown"]:
                counts[artist] = counts.get(artist, 0) + 1
        return [
            {"name": name, "track_count": count}
            for name, count in sorted(counts.items(), key=lambda kv: kv[0])
        ]
