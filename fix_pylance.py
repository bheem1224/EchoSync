with open("services/metadata_enhancer.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

has_generate_import = any("generate_plugin_id" in l for l in lines)
if not has_generate_import:
    lines.insert(
        0, "from core.nexus_framework.plugin_loader import generate_plugin_id\n"
    )

for i, line in enumerate(lines):
    if (
        line.startswith("from sqlalchemy.orm.attributes import flag_modified")
        or line.startswith("from sqlalchemy.exc import OperationalError")
        or "import echosync_core" in line
    ):
        lines[i] = line.rstrip() + "  # pyright: ignore[reportMissingImports]\n"
    elif (
        'if hasattr(fingerprint_provider, "resolve_fingerprint_details"):' in line
        or 'elif hasattr(fingerprint_provider, "resolve_fingerprint"):' in line
        or "results = metadata_provider.search_metadata" in line
        or "results = mb_client.search_metadata" in line
        or "details = fingerprint_provider.resolve_fingerprint_details" in line
    ):
        lines[i] = line.rstrip() + "  # type: ignore[attr-defined]\n"
    elif "Gatekeeper.authorize_and_execute" in line:
        lines[i] = line.replace(
            "Gatekeeper.authorize_and_execute", "Gatekeeper().authorize_and_execute"
        )
    elif "track.fingerprint_confidence = 1.0" in line:
        lines[i] = line.rstrip() + "  # type: ignore[attr-defined]\n"
    elif (
        "album_title=track.album_title if hasattr(track, 'album_title') else None,"
        in line
    ):
        lines[i] = line.replace(
            "album_title=track.album_title if hasattr(track, 'album_title') else None,",
            "album_title=track.album_title if hasattr(track, 'album_title') and track.album_title else \"\",",
        )
    elif "return isrc_track, 0.92" in line:
        lines[i] = """                            return {
                                "title": isrc_track.title,
                                "artist": isrc_track.artist_name,
                                "album": isrc_track.album_title,
                                "recording_id": isrc_track.identifiers.get("musicbrainz_id", "") if isrc_track.identifiers else "",
                                "release_id": isrc_track.identifiers.get("musicbrainz_release_group_id", "") if isrc_track.identifiers else "",
                                "track_number": isrc_track.track_number,
                                "isrc": isrc_track.isrc,
                                "date": isrc_track.release_year,
                            }, 0.92\n"""
    elif 'PluginRegistry.get_plugin("musicbrainz")' in line:
        lines[i] = line.replace(
            'PluginRegistry.get_plugin("musicbrainz")',
            'PluginRegistry.get_plugin(generate_plugin_id("EchoSync.musicbrainz"))',
        )
    elif 'PluginRegistry.get_plugin("spotify")' in line:
        lines[i] = line.replace(
            'PluginRegistry.get_plugin("spotify")',
            'PluginRegistry.get_plugin(generate_plugin_id("EchoSync.spotify"))',
        )

with open("services/metadata_enhancer.py", "w", encoding="utf-8") as f:
    f.writelines(lines)
