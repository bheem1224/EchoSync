from typing import Any
from core.db.echo_sync_track import EchosyncTrack
from core.matching_engine.trust_gate import clean_title_from_filename, is_generic_title


def calculate_acoustid_duration_weight(track_duration: float, candidate_duration: float) -> float:
    delta = abs(track_duration - candidate_duration)
    if delta > 2.0:
        return 0.0
    # Progressive parabolic curve: 1.0 at 0s, 0.75 at 1s, 0.0 at 2s
    return max(0.0, 1.0 - (delta / 2.0) ** 2)


def calculate_text_duration_weight(track_duration: float, candidate_duration: float) -> float:
    delta = abs(track_duration - candidate_duration)
    if delta > 8.0:
        return 0.0
    return max(0.0, 1.0 - (delta / 8.0))


def score_acoustid_candidate(
    matcher: Any,
    candidate: dict[str, Any],
    baseline_title: str,
    file_duration_ms: int,
    baseline_artist: str | None = None,
    baseline_album: str | None = None,
    filename: str | None = None,
    prefer_studio_album: bool = True,
) -> float:
    """Score AcoustID recording candidate by duration proximity, variant disambiguation penalties,
    and canonical studio release weighting using WeightedMatchingEngine(PROFILE_EXACT_SYNC).
    """
    cand_dur = candidate.get("length") or candidate.get("duration_ms") or candidate.get("duration")
    cand_dur_ms: int | None = None
    duration_weight = 1.0
    delta_sec = 0.0
    if cand_dur:
        try:
            cand_dur_val = float(cand_dur)
            if 0 < cand_dur_val < 10000:
                cand_dur_val *= 1000.0
            cand_dur_ms = int(cand_dur_val)
            if file_duration_ms > 0:
                track_dur_sec = file_duration_ms / 1000.0
                cand_dur_sec = cand_dur_ms / 1000.0
                delta_sec = abs(track_dur_sec - cand_dur_sec)
                duration_weight = calculate_acoustid_duration_weight(track_dur_sec, cand_dur_sec)
                if duration_weight <= 0.0 or delta_sec > 2.0:
                    return 0.0  # Hard AcoustID duration gate (reject delta > 2.0s)
        except (ValueError, TypeError):
            pass

    c_title = str(candidate.get("title") or "")
    c_artist = str(candidate.get("artist") or candidate.get("artist_name") or "")
    c_album = str(candidate.get("album") or candidate.get("album_title") or "")

    clean_file_title = clean_title_from_filename(filename) if filename else ""
    query_title = clean_file_title if (clean_file_title and not is_generic_title(clean_file_title)) else baseline_title

    query_track = EchosyncTrack(
        raw_title=query_title or c_title,
        artist_name=baseline_artist or c_artist,
        album_title=baseline_album or c_album,
        duration=file_duration_ms if file_duration_ms > 0 else None,
    )
    cand_track = EchosyncTrack(
        raw_title=c_title,
        artist_name=c_artist,
        album_title=c_album,
        duration=cand_dur_ms,
        version=candidate.get("disambiguation") or candidate.get("version"),
    )
    match_res = matcher.calculate_match(query_track, cand_track)
    matcher_score = match_res.confidence_score if match_res else 0.0

    # Preference for canonical studio release groups
    release_group = candidate.get("release_group") or candidate.get("release-group") or {}
    if not release_group and candidate.get("releases"):
        for r in candidate.get("releases") or []:
            if isinstance(r, dict):
                rg = r.get("release-group") or r.get("release_group") or {}
                if rg.get("primary_type") == "Album" or rg.get("primary-type") == "Album":
                    release_group = rg
                    break

    p_type = (release_group.get("primary_type") or release_group.get("primary-type") or "").strip().lower()
    s_types = [
        str(st).strip().lower()
        for st in (release_group.get("secondary_types") or release_group.get("secondary-types") or [])
    ]

    is_compilation = any(t in s_types for t in ["compilation", "dj-mix", "sampler", "remix"])
    c_title_lower = c_title.lower()
    title_has_mix = "mix" in c_title_lower or "remix" in c_title_lower

    penalty = 0.0
    if is_compilation and not title_has_mix:
        penalty = -35.0  # -0.35 mapped to 0-100 scale

    bonus = 0.0
    if prefer_studio_album and p_type == "album" and not s_types:
        bonus = 25.0  # +0.25 mapped to 0-100 scale

    artist_credit = candidate.get("artist-credit") or candidate.get("artists") or []
    if "various artists" in str(artist_credit).lower():
        penalty -= 10.0

    # Base physical acoustic evidence grants high confidence when tags are corrupted
    base_score = matcher_score if matcher_score > 0.0 else 80.0
    score = base_score + bonus + penalty

    # Progressive Duration Multiplier:
    # If delta <= 1.0s, duration weight yields maximum weight (dominates candidate ranking
    # and preserves canonical release group advantages).
    # Beyond 1.0s, steep progressive parabolic decay applies.
    if delta_sec <= 1.0:
        score = score * (0.95 + 0.05 * duration_weight)
    else:
        score = score * duration_weight

    return max(score, 0.0)
