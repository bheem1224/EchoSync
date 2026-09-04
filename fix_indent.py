with open('services/metadata_enhancer.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '                            return {' in line:
        lines[i] = '                        return {\n'
    elif '                                "title": isrc_track.title,' in line:
        lines[i] = '                            "title": isrc_track.title,\n'
    elif '                                "artist": isrc_track.artist_name,' in line:
        lines[i] = '                            "artist": isrc_track.artist_name,\n'
    elif '                                "album": isrc_track.album_title,' in line:
        lines[i] = '                            "album": isrc_track.album_title,\n'
    elif '                                "recording_id": isrc_track.identifiers.get("musicbrainz_id", "") if isrc_track.identifiers else "",' in line:
        lines[i] = '                            "recording_id": isrc_track.identifiers.get("musicbrainz_id", "") if isrc_track.identifiers else "",\n'
    elif '                                "release_id": isrc_track.identifiers.get("musicbrainz_release_group_id", "") if isrc_track.identifiers else "",' in line:
        lines[i] = '                            "release_id": isrc_track.identifiers.get("musicbrainz_release_group_id", "") if isrc_track.identifiers else "",\n'
    elif '                                "track_number": isrc_track.track_number,' in line:
        lines[i] = '                            "track_number": isrc_track.track_number,\n'
    elif '                                "isrc": isrc_track.isrc,' in line:
        lines[i] = '                            "isrc": isrc_track.isrc,\n'
    elif '                                "date": isrc_track.release_year,' in line:
        lines[i] = '                            "date": isrc_track.release_year,\n'
    elif '                            }, 0.92' in line:
        lines[i] = '                        }, 0.92\n'

with open('services/metadata_enhancer.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

