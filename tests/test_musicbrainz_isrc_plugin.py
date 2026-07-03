import pytest
from core.enums import Capability
from core.nexus_framework.plugin_loader import get_plugin_by_capability, PluginRegistry
from core.matching_engine.echo_sync_track import EchosyncTrack
from plugins.EchoSync.musicbrainz.client import MusicBrainzClient

def test_musicbrainz_isrc_plugin_resolution():
    # Register the plugin class with PluginRegistry manually for testing
    PluginRegistry.register(MusicBrainzClient, name="EchoSync.musicbrainz", source_type="core")

    provider = get_plugin_by_capability(Capability.FETCH_BY_ISRC)
    assert provider is not None
    assert provider.name == "EchoSync.musicbrainz"

    # Crazy Eyes (USRC17607839)
    # Using real MusicBrainz API call via the plugin
    track = provider.search_by_isrc("USRC17607839")
    assert track is not None
    assert isinstance(track, EchosyncTrack)
    assert "Crazy Eyes" in track.raw_title or "Crazy Eyes" in track.title
    assert "Daryl Hall" in track.artist_name
    assert track.release_year == 1976
