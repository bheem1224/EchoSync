from plugins.slskd.client import _sanitize_peer_filename


def test_sanitize_peer_filename_strips_remote_path_components():
    assert _sanitize_peer_filename("../../unsafe/..\\track.flac") == "track.flac"
    assert _sanitize_peer_filename("Artist/Album/01 - Song.mp3") == "01 - Song.mp3"
    assert _sanitize_peer_filename("") == "downloaded_file"