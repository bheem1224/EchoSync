import re
"""
WeightedMatchingEngine - Core scoring logic with 5-step gating

This module implements the scoring algorithm for matching tracks.

5-Step Gating Logic:
1. Version Check: Detect version mismatches (Remix vs Original), apply penalties
2. Edition/Track Check: Detect edition mismatches (remaster, deluxe, etc), apply penalties
3. Fuzzy Text Matching: Compare title, artist, album using fuzzy matching
4. Duration Matching: Compare track duration with tolerance
5. Quality Tie-Breaker: Apply quality bonus to break ties

Each step gates the score and applies cumulative penalties/bonuses.
Final score: 0-100 confidence percentage.
"""

from typing import Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher
import logging
import os

from .echo_sync_track import EchosyncTrack
from .scoring_profile import ScoringProfile, ScoringWeights, ProfileType
from .fingerprinting import FingerprintMatcher

logger = logging.getLogger(__name__)

# DEV_MODE killswitch: set ECHOSYNC_DEV_MODE=1 (or "true"/"yes") in the environment
# to bypass the ISRC instant-match fast-path during development/testing.
# Uses .get() with a safe default so the app never raises if the variable is absent.
_ISRC_FAST_PATH_ENABLED = os.environ.get("ECHOSYNC_DEV_MODE", "").strip().lower() not in ("1", "true", "yes")


@dataclass
class MatchResult:
    """Result from a track comparison"""
    confidence_score: float  # 0-100
    passed_version_check: bool
    passed_edition_check: bool
    fuzzy_text_score: float
    duration_match_score: float
    quality_bonus_applied: float
    version_penalty_applied: float
    edition_penalty_applied: float
    reasoning: str  # Human-readable explanation
    target_source: Optional[str] = None  # e.g., plex, jellyfin
    target_identifier: Optional[str] = None  # Provider-opaque item ID (e.g. provider_item_id; ratingKey for Plex, item Id UUID for Jellyfin)
    target_exists: bool = False  # True if identifier is present for target
    # Signals that this failed match is a likely alternate edition (Radio Edit vs.
    # Album Version, etc.) — the text was an exceptional match but the duration
    # exceeded the strict tolerance.  The score is still 0.0 (match REJECTED), but
    # this flag allows the caller to route the track to the Suggestion Engine
    # instead of silently discarding it.
    is_near_miss: bool = False


class WeightedMatchingEngine:
    """
    Core weighted matching engine implementing 5-step gating logic
    """

    @staticmethod
    def is_valid_isrc(isrc_string: str) -> bool:
        if not isrc_string:
            return False
        cleaned_isrc = str(isrc_string).replace("-", "").strip().upper()
        if cleaned_isrc in ["0", "NULL", "NONE", "N/A", "UNKNOWN"]:
            return False
        isrc_pattern = re.compile(r'^[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}$')
        return bool(isrc_pattern.match(cleaned_isrc))

    VERSION_KEYWORDS = {
        'remix', 'rmx', 'mix', 'edit', 'extended', 'instrumental',
        'acapella', 'bootleg', 'cover', 'remaster', 'remastered',
        'original', 'club', 'radio', 'house', 'deep', 'progressive',
        'version', 'ver', 'alternative', 'alt', 'acoustic', 'live'
    }

    EDITION_KEYWORDS = {
        'deluxe', 'standard', 'explicit', 'clean', 'remaster',
        'remastered', '24bit', '16bit', 'lossless', 'radio', 'extended'
    }

    def __init__(self, profile: ScoringProfile):
        """
        Initialize engine with a scoring profile

        Args:
            profile: ScoringProfile defining weights and penalties
        """
        self.profile = profile
        self.weights = profile.get_weights()

        if not self.weights.validate():
            raise ValueError("Invalid scoring weights")

    def calculate_match(
        self,
        source: EchosyncTrack,
        candidate: EchosyncTrack,
        target_source: Optional[str] = None,
        target_identifier: Optional[str] = None,
    ) -> MatchResult:
        """
        Calculate match confidence between source and candidate tracks

        Args:
            source: Source track (what we're looking for)
            candidate: Candidate track (what we're comparing)

        Returns:
            MatchResult with confidence score (0-100) and detailed breakdown
        """

        # Initialize scoring components
        score = 0.0
        max_possible_score = 0.0
        version_penalty = 0.0
        edition_penalty = 0.0
        quality_bonus = 0.0
        fingerprint_score = 0.0
        reasoning_parts = []

        # ===== STEP 0a: ISRC INSTANT MATCH or AUTO-FAIL (highest confidence) =====
        # If both tracks have valid ISRCs and they match exactly, instant 100% confidence.
        # If both have valid ISRCs and they differ, auto-fail (score 0).
        # Guarded by _ISRC_FAST_PATH_ENABLED so this step can be disabled in DEV_MODE
        # without throwing an exception if the env var is absent.
        if _ISRC_FAST_PATH_ENABLED:
            src_isrc = getattr(source, "isrc", None)
            cand_isrc = getattr(candidate, "isrc", None)
            src_valid = self.is_valid_isrc(src_isrc)
            cand_valid = self.is_valid_isrc(cand_isrc)
            if src_valid and cand_valid:
                # is_valid_isrc() already confirmed both are non-None, non-empty strings
                # that match the ISRC regex — .strip().upper() is safe here.
                if src_isrc.strip().upper() == cand_isrc.strip().upper():
                    return self._attach_target_context(MatchResult(
                        confidence_score=100.0,
                        passed_version_check=True,
                        passed_edition_check=True,
                        fuzzy_text_score=1.0,
                        duration_match_score=1.0,
                        quality_bonus_applied=0.0,
                        version_penalty_applied=0.0,
                        edition_penalty_applied=0.0,
                        reasoning="ISRC match (identical recording - instant 100% confidence)"
                    ), target_source, target_identifier)
                else:
                    reasoning_parts.append("ISRC mismatch (both present, different codes) - auto-fail")
                    return self._attach_target_context(MatchResult(
                        confidence_score=0.0,
                        passed_version_check=False,
                        passed_edition_check=False,
                        fuzzy_text_score=0.0,
                        duration_match_score=0.0,
                        quality_bonus_applied=0.0,
                        version_penalty_applied=0.0,
                        edition_penalty_applied=0.0,
                        reasoning=" | ".join(reasoning_parts)
                    ), target_source, target_identifier)

        # Continue with standard matching...
        return self._attach_target_context(
            self._calculate_standard_match(source, candidate),
            target_source,
            target_identifier,
        )

    def calculate_title_duration_match(
        self,
        source: EchosyncTrack,
        candidate: EchosyncTrack,
        target_source: Optional[str] = None,
        target_identifier: Optional[str] = None,
    ) -> MatchResult:
        """
        Calculate match for Tier 2 fallback: exact title + duration only (ignores artist).
        Used when artist metadata is unreliable but title+duration are reliable.

        Stricter criteria:
        - ISRC match = instant 100%
        - Exact title match required (case-insensitive, normalized)
        - Duration within 2 seconds or 2% (stricter than standard)
        - Returns 90-100% confidence if both pass

        Args:
            source: Source track
            candidate: Candidate track

        Returns:
            MatchResult with confidence score
        """
        reasoning_parts = []

        # Check ISRC first (highest confidence)
        if source.isrc and candidate.isrc:
            if source.isrc.strip().upper() == candidate.isrc.strip().upper():
                return self._attach_target_context(MatchResult(
                    confidence_score=100.0,
                    passed_version_check=True,
                    passed_edition_check=True,
                    fuzzy_text_score=1.0,
                    duration_match_score=1.0,
                    quality_bonus_applied=0.0,
                    version_penalty_applied=0.0,
                    edition_penalty_applied=0.0,
                    reasoning="Tier 2: ISRC match (instant 100%)"
                ), target_source, target_identifier)
            else:
                reasoning_parts.append("ISRC mismatch (different recordings)")
                return self._attach_target_context(MatchResult(
                    confidence_score=0.0,
                    passed_version_check=False,
                    passed_edition_check=False,
                    fuzzy_text_score=0.0,
                    duration_match_score=0.0,
                    quality_bonus_applied=0.0,
                    version_penalty_applied=0.0,
                    edition_penalty_applied=0.0,
                    reasoning=" | ".join(reasoning_parts)
                ), target_source, target_identifier)

        # Title must be exact match (normalized)
        source_title_norm = self._normalize_string_for_comparison(source.title or "")
        candidate_title_norm = self._normalize_string_for_comparison(candidate.title or "")

        if source_title_norm != candidate_title_norm:
            reasoning_parts.append(f"Title mismatch: '{source.title}' != '{candidate.title}'")
            return self._attach_target_context(MatchResult(
                confidence_score=0.0,
                passed_version_check=False,
                passed_edition_check=False,
                fuzzy_text_score=0.0,
                duration_match_score=0.0,
                quality_bonus_applied=0.0,
                version_penalty_applied=0.0,
                edition_penalty_applied=0.0,
                reasoning=" | ".join(reasoning_parts)
            ), target_source, target_identifier)

        reasoning_parts.append("Title exact match")

        # Duration must be within strict tolerance (2 seconds since artist is ignored)
        if not source.duration or not candidate.duration:
            reasoning_parts.append("Missing duration - cannot validate")
            return self._attach_target_context(MatchResult(
                confidence_score=0.0,
                passed_version_check=False,
                passed_edition_check=False,
                fuzzy_text_score=1.0,
                duration_match_score=0.0,
                quality_bonus_applied=0.0,
                version_penalty_applied=0.0,
                edition_penalty_applied=0.0,
                reasoning=" | ".join(reasoning_parts)
            ), target_source, target_identifier)

        duration_diff_ms = abs(source.duration - candidate.duration)
        tolerance_ms = 2000  # 2 seconds strict tolerance for Tier 2

        # Allow plugins to relax the duration gate (e.g. CJK drama context boost).
        from core.hook_manager import hook_manager as _hm_t2
        _t2_mod = _hm_t2.apply_filters(
            'scoring_modifier', {},
            source=source, candidate=candidate,
        )
        _t2_dur_override: Optional[int] = (
            int(_t2_mod['duration_override'])
            if isinstance(_t2_mod, dict) and _t2_mod.get('duration_override')
            else None
        )
        _t2_score_boost: float = (
            float(_t2_mod.get('boost', 0.0))
            if isinstance(_t2_mod, dict)
            else 0.0
        )
        if _t2_dur_override is not None:
            tolerance_ms = _t2_dur_override

        if duration_diff_ms > tolerance_ms:
            reasoning_parts.append(
                f"Duration outside tolerance: {duration_diff_ms}ms > {tolerance_ms}ms "
                f"({source.duration}ms vs {candidate.duration}ms)"
            )
            return MatchResult(
                confidence_score=0.0,
                passed_version_check=False,
                passed_edition_check=False,
                fuzzy_text_score=1.0,
                duration_match_score=0.0,
                quality_bonus_applied=0.0,
                version_penalty_applied=0.0,
                edition_penalty_applied=0.0,
                reasoning=" | ".join(reasoning_parts)
            )

        # Calculate confidence based on duration proximity
        duration_score = 1.0 - (duration_diff_ms / tolerance_ms) * 0.1  # Max 10% deduction
        confidence = 90.0 + (duration_score * 10.0)  # 90-100% range

        reasoning_parts.append(
            f"Duration match: {duration_diff_ms}ms difference (within {tolerance_ms}ms tolerance)"
        )
        if _t2_score_boost:
            confidence = min(100.0, confidence + _t2_score_boost)
            reasoning_parts.append(f"Plugin boost applied: +{_t2_score_boost:.1f} → {confidence:.1f}%")
        reasoning_parts.append(f"Tier 2: Title+Duration match (artist ignored) → {confidence:.1f}%")

        return self._attach_target_context(MatchResult(
            confidence_score=confidence,
            passed_version_check=True,
            passed_edition_check=True,
            fuzzy_text_score=1.0,
            duration_match_score=duration_score,
            quality_bonus_applied=0.0,
            version_penalty_applied=0.0,
            edition_penalty_applied=0.0,
            reasoning=" | ".join(reasoning_parts)
        ), target_source, target_identifier)

    def _calculate_standard_match(
        self,
        source: EchosyncTrack,
        candidate: EchosyncTrack
    ) -> MatchResult:
        """
        Standard matching logic (original calculate_match implementation)
        """
        score = 0.0
        max_possible_score = 0.0
        version_penalty = 0.0
        edition_penalty = 0.0
        quality_bonus = 0.0
        fingerprint_score = 0.0
        reasoning_parts = []
        
        # ===== STEP 0b: FINGERPRINT MATCHING (if available) =====
        # Check fingerprints first - if they match, we can be very confident
        if source.fingerprint and candidate.fingerprint:
            if FingerprintMatcher.fingerprints_match(source.fingerprint, candidate.fingerprint):
                fingerprint_score = self.weights.fingerprint_weight * 100
                score += fingerprint_score
                max_possible_score += self.weights.fingerprint_weight * 100
                reasoning_parts.append(f"Fingerprint match: {fingerprint_score:.1f} points (high confidence)")
                # Fingerprint match is authoritative - skip other checks
                return MatchResult(
                    confidence_score=min(100.0, score),
                    passed_version_check=True,
                    passed_edition_check=True,
                    fuzzy_text_score=1.0,
                    duration_match_score=1.0,
                    quality_bonus_applied=0.0,
                    version_penalty_applied=0.0,
                    edition_penalty_applied=0.0,
                    reasoning="Fingerprint match (audio fingerprint identical)"
                )
            else:
                reasoning_parts.append("Fingerprint available but no match")

        # ===== STEP 1: VERSION CHECK =====
        version_match, version_reasoning = self._check_version_match(source, candidate)

        if not version_match:
            version_penalty = self.weights.version_mismatch_penalty
            reasoning_parts.append(f"Version mismatch: {version_reasoning} (-{version_penalty})")
            
            # Version mismatch is ALWAYS a critical failure - reject immediately
            # Duration filtering at search time should prevent remix/live versions from appearing
            logger.debug(f"REJECTING candidate due to version mismatch: {version_reasoning}")
            return MatchResult(
                confidence_score=0.0,  # Hard fail on version mismatch
                passed_version_check=False,
                passed_edition_check=True,
                fuzzy_text_score=1.0,
                duration_match_score=0.0,
                quality_bonus_applied=0.0,
                version_penalty_applied=version_penalty,
                edition_penalty_applied=0.0,
                reasoning=" | ".join(reasoning_parts) + " | REJECTED: Version mismatch is critical failure"
            )
        else:
            reasoning_parts.append(f"Version match: {version_reasoning}")

        # ===== STEP 2: EDITION/TRACK CHECK =====
        edition_match, edition_reasoning = self._check_edition_match(source, candidate)

        if not edition_match:
            edition_penalty = self.weights.edition_mismatch_penalty
            reasoning_parts.append(f"Edition mismatch: {edition_reasoning} (-{edition_penalty})")
        else:
            reasoning_parts.append(f"Edition match: {edition_reasoning}")

        # ===== STEP 3: FUZZY TEXT MATCHING =====
        fuzzy_score = self._calculate_fuzzy_text_match(source, candidate)
        text_contribution = fuzzy_score * self.weights.text_weight * 100

        reasoning_parts.append(f"Text match: {fuzzy_score:.1%} × {self.weights.text_weight:.1%} = {text_contribution:.1f} points")

        # Store individual component scores for later use (e.g., duration bonus)
        artist_fuzzy_score = 0.0
        if source.artist_name and candidate.artist_name:
            artist_fuzzy_score = self._fuzzy_match(source.artist_name, candidate.artist_name)

        # Title score — computed here (once) so both the strong-pair rescues below
        # and the safe duration bonus further down share a single _fuzzy_match call.
        title_fuzzy_score = 0.0
        if source.title and candidate.title:
            title_fuzzy_score = self._fuzzy_match(source.title, candidate.title)

        # ── Pre-score plugin check ─────────────────────────────────────────────
        # Fire the scoring_modifier hook here — BEFORE the fuzzy threshold gate —
        # so plugins can signal force_artist_score_to_100 when an external
        # context (e.g. matching CJK drama brackets) definitively identifies the
        # artist, making a "Various Artists" tag or a romanised-vs-hanzi mismatch
        # irrelevant.  Setting artist_fuzzy_score = 1.0 here means:
        #   • Rescue A (title+artist ≥ 0.95) fires if the title also matches.
        #   • STEP 4's Artist Match Duration Escalation (→ 8500ms) activates.
        # The hook fires a second time at the normal plugin-modifier block below
        # for boost / duration_override; double-firing is safe (pure read op).
        from core.hook_manager import hook_manager as _hm_pre
        _pre_mod: dict = _hm_pre.apply_filters(
            'scoring_modifier', {},
            source=source, candidate=candidate,
        ) or {}
        _force_artist: bool = bool(_pre_mod.get('force_artist_score_to_100', False))
        _pre_dur_override: Optional[int] = (
            int(_pre_mod['duration_override'])
            if _pre_mod.get('duration_override')
            else None
        )
        if _force_artist:
            artist_fuzzy_score = 1.0
            reasoning_parts.append(
                "Drama context confirmed by plugin → artist_score forced to 1.0 "
                "(artist tag treated as verified regardless of romanisation/compilation tagging)"
            )

        # ── Reverse Various Artists Amnesty ───────────────────────────────────
        # Scenario: Spotify asks for a specific singer (e.g. 'Hu Xia') but the
        # local file is part of an OST compilation tagged 'Various Artists'.
        # The raw_title of the local track carries a CJK drama-series marker
        # (e.g. '无题 - 网剧《山河令》插曲') that proves the track's provenance
        # even though the artist field is a generic compilation tag.
        #
        # Conditions (all must hold):
        #   1. title_fuzzy_score == 1.0 — cleaned titles are a perfect match.
        #   2. candidate.artist_name is 'Various Artists' (case-insensitive).
        #   3. candidate.raw_title contains a CJK OST marker — at least one of
        #      《…》/【…】 brackets OR recognised Chinese suffix keywords.
        #
        # Effect: force artist_score to 1.0 and widen duration tolerance to
        # 10 000 ms so that TV-edit / trailer-length variants are not rejected.
        if (
            not _force_artist
            and title_fuzzy_score >= 1.0
            and candidate.artist_name
            and candidate.artist_name.strip().lower() == 'various artists'
        ):
            import re as _re_va
            _raw = getattr(candidate, 'raw_title', '') or candidate.title or ''
            _CJK_OST_RE = _re_va.compile(
                r'《[^》]+》'           # 《山河令》 style drama title
                r'|【[^】]+】'          # 【山河令】 style
                r'|[片主插推片片]\s*[头尾]?\s*曲'  # 片头曲/片尾曲/主题曲/插曲/推广曲
                r'|原声带|原声|配乐'     # 原声带 (OST)
                r'|网剧|电视剧|电影'     # drama/film prefixes
            )
            if _CJK_OST_RE.search(_raw):
                _force_artist = True
                _pre_dur_override = max(_pre_dur_override or 0, 10000)
                artist_fuzzy_score = 1.0
                reasoning_parts.append(
                    "Reverse Various Artists Amnesty: title=1.00, candidate artist='Various Artists', "
                    f"raw_title contains CJK OST marker → artist_score forced to 1.0, "
                    f"duration_tolerance raised to {_pre_dur_override}ms"
                )

        if fuzzy_score < self.weights.fuzzy_match_threshold:
            # ── Strong-pair rescues ────────────────────────────────────────────
            # The combined fuzzy average can fall below the threshold when album
            # data is absent from the source (playlists rarely surface it) or
            # wrong (compilations, re-releases).  Rather than hard-failing, check
            # whether two mutually-independent high-confidence signals agree.
            # Both rescues require the version gate to have already passed.

            # Rescue A — Title + Artist (both ≥ 0.95, album discounted)
            # A near-exact title AND near-exact artist independently identify the
            # recording.  Album mismatches drag the combined score below threshold
            # but are not probative when the other two dimensions are near-perfect.
            if title_fuzzy_score >= 0.95 and artist_fuzzy_score >= 0.95:
                ta_total_w = self.weights.title_weight + self.weights.artist_weight
                ta_norm = (
                    title_fuzzy_score * self.weights.title_weight
                    + artist_fuzzy_score * self.weights.artist_weight
                ) / ta_total_w
                # Artist is already confirmed ≥ 0.95 (the enclosing condition).
                # Use the plugin's duration_override if supplied (e.g. 15000ms when
                # CJK drama context is confirmed), otherwise fall back to the standard
                # 8500ms Artist Match Escalation.  This ensures tracks with TV-edit /
                # trailer-length differences (up to ~15 s) are not rejected here.
                _rescue_a_tol: int = max(8500, _pre_dur_override or 0)
                dur_score_a = self._calculate_duration_match(source, candidate, _rescue_a_tol)
                # Score is album-free text component + duration component
                rescued_a = (
                    ta_norm * self.weights.text_weight * 100
                    + dur_score_a * self.weights.duration_weight * 100
                ) / ((self.weights.text_weight + self.weights.duration_weight) * 100) * 100
                rescued_a = max(0.0, min(100.0, rescued_a))
                if rescued_a >= self.weights.min_confidence_to_accept:
                    reasoning_parts.append(
                        f"Title+Artist exact-pair rescue (album discounted, dur_tol={_rescue_a_tol}ms): "
                        f"title={title_fuzzy_score:.2f} artist={artist_fuzzy_score:.2f} "
                        f"dur={dur_score_a:.2f} → {rescued_a:.1f}%"
                    )
                    return MatchResult(
                        confidence_score=rescued_a,
                        passed_version_check=version_match,
                        passed_edition_check=edition_match,
                        fuzzy_text_score=ta_norm,
                        duration_match_score=dur_score_a,
                        quality_bonus_applied=0.0,
                        version_penalty_applied=version_penalty,
                        edition_penalty_applied=edition_penalty,
                        reasoning=" | ".join(reasoning_parts),
                    )

            # Rescue B — Title + Duration (title ≥ 0.95 AND duration ≤ 2 s)
            # When artist metadata is unreliable (featured-artist suffixes,
            # romanised names, compilation credits) a near-exact title with a
            # tight duration window uniquely identifies the recording without
            # needing artist or album agreement.
            if title_fuzzy_score >= 0.95 and source.duration and candidate.duration:
                dur_diff_ms = abs(source.duration - candidate.duration)
                if dur_diff_ms <= 2000:
                    td_dur_score = 1.0 - (dur_diff_ms / 2000) * 0.5
                    rescued_b = 88.0 + td_dur_score * 5.0  # 88 – 93 range
                    rescued_b = max(0.0, min(100.0, rescued_b))
                    reasoning_parts.append(
                        f"Title+Duration exact-pair rescue (artist discounted): "
                        f"title={title_fuzzy_score:.2f} dur_diff={dur_diff_ms}ms ≤ 2000ms "
                        f"→ {rescued_b:.1f}%"
                    )
                    return MatchResult(
                        confidence_score=rescued_b,
                        passed_version_check=version_match,
                        passed_edition_check=edition_match,
                        fuzzy_text_score=title_fuzzy_score,
                        duration_match_score=td_dur_score,
                        quality_bonus_applied=0.0,
                        version_penalty_applied=version_penalty,
                        edition_penalty_applied=edition_penalty,
                        reasoning=" | ".join(reasoning_parts),
                    )

            # ── End rescues — fall through to hard fail ────────────────────────
            # If fuzzy match is below threshold and no rescue applied, fail this match
            reasoning_parts.append(
                f"FAILED: Fuzzy text score below threshold "
                f"({fuzzy_score:.1%} < {self.weights.fuzzy_match_threshold:.1%})"
            )

            return MatchResult(
                confidence_score=0.0,
                passed_version_check=version_match,
                passed_edition_check=edition_match,
                fuzzy_text_score=fuzzy_score,
                duration_match_score=0.0,
                quality_bonus_applied=0.0,
                version_penalty_applied=version_penalty,
                edition_penalty_applied=edition_penalty,
                reasoning=" | ".join(reasoning_parts)
            )

        score += text_contribution
        max_possible_score += self.weights.text_weight * 100

        # ===== STEP 4: DURATION MATCHING =====
        # Artist Match Duration Escalation — when artist confidence is ≥ 0.95 the
        # artist is definitively identified; slight duration drift from extra silence,
        # streaming re-masters, or gapless album padding should not kill an otherwise
        # strong match.  The tolerance is raised from the profile default up to 8500ms
        # for this candidate only.  The same linear penalty formula (max −0.5 at the
        # new edge) applies, so the scoring still degrades gracefully and a track 4 s
        # off does not get the same score as one that is bang-on.
        _artist_dur_tolerance: Optional[int] = None
        if artist_fuzzy_score >= 0.95:
            _artist_dur_tolerance = 8500
            reasoning_parts.append(
                f"Artist Match Duration Escalation: artist={artist_fuzzy_score:.2f} ≥ 0.95 "
                f"→ duration tolerance raised to {_artist_dur_tolerance}ms"
            )
        duration_score = self._calculate_duration_match(source, candidate, _artist_dur_tolerance)
        duration_contribution = duration_score * self.weights.duration_weight * 100

        reasoning_parts.append(
            f"Duration match: {duration_score:.1%} × {self.weights.duration_weight:.1%} = {duration_contribution:.1f} points"
        )

        # ── Plugin scoring modifiers ───────────────────────────────────────────
        # Fired here — after the standard duration check but BEFORE the near-miss
        # guard — so that a plugin can:
        #   a) supply a relaxed duration_tolerance_override (ms) to rescue OST
        #      tracks whose TV edit / trailer mix differs from the album length;
        #   b) supply a score_boost (float) applied to the final normalised score.
        # The hook receives (modifier_dict, source=, candidate=) and returns the
        # possibly-mutated dict.  An empty dict means "no modification".
        from core.hook_manager import hook_manager as _hm_mod
        _plugin_mod = _hm_mod.apply_filters(
            'scoring_modifier', {},
            source=source, candidate=candidate,
        )
        _score_boost: float = (
            float(_plugin_mod.get('boost', 0.0))
            if isinstance(_plugin_mod, dict)
            else 0.0
        )
        _dur_override: Optional[int] = (
            int(_plugin_mod['duration_override'])
            if isinstance(_plugin_mod, dict) and _plugin_mod.get('duration_override')
            else None
        )
        # If a plugin supplied a relaxed duration tolerance and the standard check
        # already returned 0.0, re-evaluate before confirming a near-miss / fail.
        if _dur_override is not None and duration_score == 0.0:
            _rescored = self._calculate_duration_match(source, candidate, _dur_override)
            if _rescored > 0.0:
                duration_score = _rescored
                duration_contribution = duration_score * self.weights.duration_weight * 100
                reasoning_parts.append(
                    f"Duration rescued by plugin (tolerance_override={_dur_override}ms → "
                    f"new_score={duration_score:.2f})"
                )
        if _score_boost:
            reasoning_parts.append(f"Plugin boost queued: +{_score_boost:.1f}")
        # ── End plugin modifiers ───────────────────────────────────────────────

        # ── Near-miss detection ────────────────────────────────────────────────
        # If duration hard-failed (score=0.0) but the text match was exceptionally
        # strong (title ≥ 0.95 AND artist ≥ 0.95), this is almost certainly an
        # alternate edition (Radio Edit, Single Mix, Album Version) rather than a
        # wrong track.  Flag it so the caller can route it to the Suggestion Engine.
        # The match MUST still fail — we return 0.0 confidence.
        if duration_score == 0.0 and title_fuzzy_score >= 0.95 and artist_fuzzy_score >= 0.95:
            dur_diff_ms = (
                abs(source.duration - candidate.duration)
                if source.duration and candidate.duration
                else None
            )
            reasoning_parts.append(
                f"NEAR-MISS: duration outside tolerance (diff={dur_diff_ms}ms) "
                f"but title={title_fuzzy_score:.2f} artist={artist_fuzzy_score:.2f} — "
                f"likely alternate edition; flagged for Suggestion Engine"
            )
            return MatchResult(
                confidence_score=0.0,
                passed_version_check=version_match,
                passed_edition_check=edition_match,
                fuzzy_text_score=fuzzy_score,
                duration_match_score=0.0,
                quality_bonus_applied=0.0,
                version_penalty_applied=version_penalty,
                edition_penalty_applied=edition_penalty,
                reasoning=" | ".join(reasoning_parts),
                is_near_miss=True,
            )

        score += duration_contribution
        max_possible_score += self.weights.duration_weight * 100

        # ===== STEP 5: QUALITY TIE-BREAKER =====
        if candidate.quality_tags:
            quality_bonus = self.weights.quality_bonus * 100
            score += quality_bonus
            max_possible_score += self.weights.quality_bonus * 100
            reasoning_parts.append(f"Quality bonus applied: +{quality_bonus:.1f} points")
        else:
            reasoning_parts.append("No quality bonus (candidate has no quality tags)")

        # ===== APPLY CUMULATIVE PENALTIES =====
        final_penalty = version_penalty + edition_penalty
        score -= final_penalty

        # ===== NORMALIZE SCORE TO 0-100 =====
        if max_possible_score > 0:
            normalized_score = (score / max_possible_score) * 100
        else:
            normalized_score = 0.0

        # ===== SAFE DURATION BONUS =====
        # If duration is near-perfect match (<= 1500ms) AND artist fuzzy score >= 60%,
        # apply a bonus to help messy filenames pass the threshold.
        # CRITICAL: Only apply if artist match is strong (prevents false positives).
        duration_bonus = 0.0
        if source.duration and candidate.duration:
            duration_diff_ms = abs(source.duration - candidate.duration)
            if duration_diff_ms <= 1500:  # Near-perfect duration match
                if artist_fuzzy_score >= 0.60:  # Artist match is strong enough
                    duration_bonus = 15.0
                    normalized_score += duration_bonus
                    reasoning_parts.append(f"Safe duration bonus: +{duration_bonus:.1f} (duration_diff={duration_diff_ms}ms, artist_score={artist_fuzzy_score:.1%})")
                else:
                    reasoning_parts.append(f"Duration bonus NOT applied (artist_score={artist_fuzzy_score:.1%} < 60%)")

        # Clamp to 0-100 range
        if _score_boost:
            normalized_score += _score_boost
            reasoning_parts.append(
                f"Plugin score_boost applied: +{_score_boost:.1f} → "
                f"adjusted={normalized_score:.1f}"
            )
        final_score = max(0.0, min(100.0, normalized_score))

        reasoning_parts.append(f"FINAL SCORE: {final_score:.1f}/100")

        return MatchResult(
            confidence_score=final_score,
            passed_version_check=version_match,
            passed_edition_check=edition_match,
            fuzzy_text_score=fuzzy_score,
            duration_match_score=duration_score,
            quality_bonus_applied=quality_bonus,
            version_penalty_applied=version_penalty,
            edition_penalty_applied=edition_penalty,
            reasoning=" | ".join(reasoning_parts)
        )

    def _attach_target_context(
        self,
        result: MatchResult,
        target_source: Optional[str],
        target_identifier: Optional[str],
    ) -> MatchResult:
        if target_source:
            result.target_source = target_source
            result.target_identifier = target_identifier
            result.target_exists = bool(target_identifier)
        return result

    def _check_version_match(self, source: EchosyncTrack, candidate: EchosyncTrack) -> Tuple[bool, str]:
        """
        Check if versions match

        Returns:
            (matches: bool, reasoning: str)
        """

        # If both have no edition, perfect match
        if not source.edition and not candidate.edition:
            return True, "Both tracks have no version info (prefer originals)"

        # If source has no version but candidate does, this is a MISMATCH
        # When user wants original, don't give them remix/live
        if not source.edition and candidate.edition:
            candidate_lower = candidate.edition.lower()
            # Check if candidate is a remix/live/etc (not just remaster which is usually okay)
            unwanted_versions = {'remix', 'live', 'acoustic', 'instrumental', 'demo', 'radio edit', 'club'}
            if any(unwanted in candidate_lower for unwanted in unwanted_versions):
                return False, f"Source wants original but candidate is '{candidate.edition}' (version mismatch)"
            # Remaster/deluxe/etc are usually acceptable if source has no version preference
            return True, f"Candidate is '{candidate.edition}' (remaster/edition okay)"

        # If candidate has no version but source specifies one, usually okay
        # (candidate might be original or just missing metadata)
        if source.edition and not candidate.edition:
            return True, "Candidate has no version info (might be original)"

        # Both have editions - check if they're the same or related
        source_version_lower = source.edition.lower()
        candidate_version_lower = candidate.edition.lower()

        # Exact match
        if source_version_lower == candidate_version_lower:
            return True, f"Versions match: '{source.edition}'"

        # Check if both have version keywords from same family
        source_keywords = self._extract_version_keywords(source_version_lower)
        candidate_keywords = self._extract_version_keywords(candidate_version_lower)

        # If no recognizable keywords, consider fuzzy match
        if not source_keywords and not candidate_keywords:
            return True, "Both have unrecognized version formats"

        # If either is empty, mismatch
        if not source_keywords or not candidate_keywords:
            return False, f"'{source.edition}' vs '{candidate.edition}' (different types)"

        # Check for keyword overlap
        overlap = source_keywords & candidate_keywords
        if overlap:
            return True, f"Version keywords match: {overlap}"

        # If "remix" in one but not other, that's a mismatch
        if ('remix' in source_keywords) != ('remix' in candidate_keywords):
            return False, f"One is remix, other is original"

        # Otherwise, consider it a version mismatch
        return False, f"Different versions: '{source.edition}' vs '{candidate.edition}'"

    def _check_edition_match(self, source: EchosyncTrack, candidate: EchosyncTrack) -> Tuple[bool, str]:
        """
        Check if editions match (disc_number, etc)
        
        Logic:
        - Treat blank edition/disc_number as "original" / disc 1
        - If both resolve to original/disc 1: pass (discount edition check)
        - If one is remix and other is original: fail (they don't match)
        - If both have specific editions/disc numbers: they must match exactly

        Returns:
            (matches: bool, reasoning: str)
        """
        # Treat blank/missing disc_number as disc 1 (original/standard)
        source_disc = source.disc_number or 1
        candidate_disc = candidate.disc_number or 1
        
        # Disc numbers must match
        if source_disc != candidate_disc:
            return False, f"Disc number mismatch: disc {source_disc} vs {candidate_disc}"
        
        # If both resolve to disc 1 (both original), pass
        if source_disc == 1 and candidate_disc == 1:
            return True, "Remaster/edition okay (both original)"
        
        # If both have same disc number > 1, pass
        return True, f"Edition match: both disc {source_disc}"

    def _tokenize_artists(self, artist_string: str) -> set:
        """
        Tokenize artist string into individual artist names.
        Splits by &, feat., featuring, with, and, commas.
        
        Args:
            artist_string: Artist name(s) as string
            
        Returns:
            Set of normalized artist tokens
        """
        import re
        
        if not artist_string:
            return set()
        
        # Split by common delimiters
        # Matches: &, feat., ft., featuring, with, and, ,
        tokens = re.split(r'\s*(?:&|\bfeat\.?|\bft\.?|\bfeaturing\b|\bwith\b|\band\b|,)\s*', artist_string, flags=re.IGNORECASE)
        
        # Normalize each token
        normalized = set()
        for token in tokens:
            token = token.strip()
            if token:
                # Normalize using the same logic as string comparison
                normalized.add(self._normalize_string_for_comparison(token))
        
        return normalized
    
    def _check_artist_subset_match(self, source: EchosyncTrack, candidate: EchosyncTrack) -> Tuple[bool, float, str]:
        """
        Check if one artist list is a subset of the other (tokenized intersection).
        Used as a rescue mechanism when fuzzy matching fails.
        
        Logic: If 100% of artists in the shorter list appear in the longer list,
        and duration is within 2 seconds, consider it a valid match.
        
        Args:
            source: Source track
            candidate: Candidate track
            
        Returns:
            Tuple of (is_subset_match, confidence_boost, reasoning)
        """
        if not source.artist_name or not candidate.artist_name:
            return False, 0.0, "Missing artist info"
        
        source_tokens = self._tokenize_artists(source.artist_name)
        candidate_tokens = self._tokenize_artists(candidate.artist_name)
        
        if not source_tokens or not candidate_tokens:
            return False, 0.0, "Could not tokenize artists"
        
        # Check if one is a subset of the other
        if source_tokens.issubset(candidate_tokens):
            subset_pct = len(source_tokens) / len(candidate_tokens) * 100
            return True, 1.0, f"Source artists are subset of candidate ({source.artist_name} ⊆ {candidate.artist_name}, {subset_pct:.0f}% overlap)"
        elif candidate_tokens.issubset(source_tokens):
            subset_pct = len(candidate_tokens) / len(source_tokens) * 100
            return True, 1.0, f"Candidate artists are subset of source ({candidate.artist_name} ⊆ {source.artist_name}, {subset_pct:.0f}% overlap)"
        else:
            # Check partial intersection
            intersection = source_tokens & candidate_tokens
            if intersection:
                overlap_pct = len(intersection) / min(len(source_tokens), len(candidate_tokens)) * 100
                return False, 0.0, f"Partial artist overlap: {overlap_pct:.0f}% ({intersection})"
            else:
                return False, 0.0, "No artist token overlap"

    def _calculate_fuzzy_text_match(self, source: EchosyncTrack, candidate: EchosyncTrack) -> float:
        """
        Calculate fuzzy text match score for title, artist, album.
        Includes artist subset rescue mechanism and dual-pass base string matching.

        Returns:
            Score 0.0-1.0
        """

        import re
        scores = []

        # Title match (most important)
        if source.title and candidate.title:
            title_score = self._fuzzy_match(source.title, candidate.title)

            # Dual-Pass 'Base String' Matching for Title
            # If Pass 1 is below a high threshold (e.g. 0.85), strip parentheticals, brackets, and post-hyphen info
            if title_score < 0.85:
                # Aggressively strip out anything inside (), [], and anything after -
                base_source = re.sub(r'[\(\[].*?[\)\]]', '', source.title)
                base_source = re.sub(r'-.*$', '', base_source)

                base_candidate = re.sub(r'[\(\[].*?[\)\]]', '', candidate.title)
                base_candidate = re.sub(r'-.*$', '', base_candidate)

                pass_2_score = self._fuzzy_match(base_source, base_candidate)

                # Apply 0.85 penalty multiplier to the base string match score
                adjusted_pass_2_score = pass_2_score * 0.85

                if adjusted_pass_2_score > title_score:
                    title_score = adjusted_pass_2_score

            scores.append(('title', title_score, self.weights.title_weight))

        # Artist match with subset rescue
        if source.artist_name and candidate.artist_name:
            artist_score = self._fuzzy_match(source.artist_name, candidate.artist_name)
            
            # If fuzzy match is low, check for artist subset match
            # Rescue mechanism: if one artist list is subset of other AND duration is tight (within 2s)
            if artist_score < 0.8:  # Only attempt rescue if fuzzy score is low
                is_subset, subset_score, subset_reason = self._check_artist_subset_match(source, candidate)
                
                if is_subset:
                    # Check duration as guard rail (must be within 2 seconds)
                    if source.duration and candidate.duration:
                        duration_diff_ms = abs(source.duration - candidate.duration)
                        if duration_diff_ms <= 2000:  # 2 second tolerance for subset rescue
                            artist_score = subset_score  # Promote to 1.0
                            # Note: reasoning will be logged in the main matching flow
            
            scores.append(('artist', artist_score, self.weights.artist_weight))

        # Album match (if available)
        if source.album_title and candidate.album_title:
            album_score = self._fuzzy_match(source.album_title, candidate.album_title)
            scores.append(('album', album_score, self.weights.album_weight))

        # If no comparison possible, return fallback
        if not scores:
            return self.weights.text_match_fallback

        # Weighted average
        total_weight = sum(w for _, _, w in scores)
        if total_weight == 0:
            return self.weights.text_match_fallback

        weighted_score = sum(score * weight for _, score, weight in scores) / total_weight
        return weighted_score

    def _calculate_duration_match(
        self,
        source: EchosyncTrack,
        candidate: EchosyncTrack,
        tolerance_override_ms: Optional[int] = None,
    ) -> float:
        """
        Calculate duration match score

        Returns:
            Score 0.0-1.0 (1.0 = exact match, decreases with difference)
        """

        if not source.duration or not candidate.duration:
            # If either has no duration, return neutral score to avoid inflating confidence
            return 0.5

        diff_ms = abs(source.duration - candidate.duration)
        tolerance_ms = (
            tolerance_override_ms
            if tolerance_override_ms is not None
            else self.weights.duration_tolerance_ms
        )

        if diff_ms <= tolerance_ms:
            # Within tolerance - score based on how close
            return 1.0 - (diff_ms / tolerance_ms) * 0.5  # Max 0.5 deduction
        else:
            # Outside tolerance - fail
            return 0.0

    def _fuzzy_match(self, a: str, b: str) -> float:
        """
        Calculate fuzzy string match ratio (0.0-1.0)

        Uses SequenceMatcher for efficient comparison
        """

        if not a or not b:
            return 0.0

        # Normalize strings
        a_norm = self._normalize_string_for_comparison(a)
        b_norm = self._normalize_string_for_comparison(b)

        if not a_norm or not b_norm:
            return 0.0

        # Use SequenceMatcher for fuzzy matching
        ratio = SequenceMatcher(None, a_norm, b_norm).ratio()
        return ratio

    def _romanize_text(self, text: str) -> str:
        """
        Stub for i18n transliteration architecture.
        In the future, use libraries like `anyascii` or `unidecode` here to map CJK/Cyrillic to Latin.
        """
        return text

    def _normalize_string_for_comparison(self, s: str) -> str:
        """
        Normalize string for comparison (lowercase, remove special chars, strip featured artists).

        For CJK text: applies noise-strip + Traditional → Simplified normalization via the
        ``pre_normalize_text`` hook so that both sides of a fuzzy comparison are always in the
        same native script.  The hook's gatekeeper returns immediately for non-CJK strings,
        so Latin / Cyrillic tracks incur zero overhead.

        Transliteration to Latin (Pinyin / Romaji) is intentionally NOT performed here —
        scoring always compares native script to native script.
        """

        import re
        # Apply CJK script normalization (T→S) before any further processing.
        # For non-CJK text the hook returns immediately (zero overhead).
        try:
            from core.hook_manager import hook_manager as _hm_cmp
            s = _hm_cmp.apply_filters('pre_normalize_text', s)
        except Exception:
            pass
        s = s.lower()
        # Strip featured artist markers first
        s = re.sub(r"[\(\[]\s*(?:feat\.?|ft\.?|featuring|with)\s+.*?[\]\)]|\s+(?:feat\.?|ft\.?|featuring|with)\s+.*$", "", s, flags=re.IGNORECASE)
        # Remove special characters but keep spaces
        s = re.sub(r'[^\w\s]', '', s)
        # Collapse multiple spaces
        s = ' '.join(s.split())
        return s

    def _extract_version_keywords(self, version_str: str) -> set:
        """
        Extract recognized version keywords from version string

        Returns:
            Set of matched keywords
        """

        matched = set()
        version_lower = version_str.lower()

        for keyword in self.VERSION_KEYWORDS:
            if keyword in version_lower:
                matched.add(keyword)

        return matched

    def select_best_download_candidate(
        self,
        target_track: EchosyncTrack,
        candidates: list[EchosyncTrack]
    ) -> Optional[EchosyncTrack]:
        """
        Select the best download candidate from a list of raw search results.
        Uses the profile weights to score and rank candidates.

        Args:
            target_track: The track we want to find
            candidates: List of raw results from SlskdProvider

        Returns:
            The winning EchosyncTrack or None if no acceptable match found
        """
        if not candidates:
            return None

        ranked_candidates = []
        rejected_count = 0

        for candidate in candidates:
            # --- Duration Gating (if enabled) ---
            if self.weights.enforce_duration_match and target_track.duration and candidate.duration:
                diff_ms = abs(target_track.duration - candidate.duration)
                if diff_ms > self.weights.duration_tolerance_ms:
                    rejected_count += 1
                    logger.debug(
                        f"Rejected '{candidate.title}' - Duration mismatch: {diff_ms}ms > {self.weights.duration_tolerance_ms}ms"
                    )
                    continue

            # Calculate match score
            match_result = self.calculate_match(target_track, candidate)

            # Additional check: Quality/Peer Stats weighting
            # The standard calculate_match focuses on metadata correctness (Is this the right song?)
            # We add a secondary score component for "Is this a good file to download?"

            # Base metadata confidence
            final_score = match_result.confidence_score

            # Only consider candidates that pass the minimum confidence threshold for metadata
            if final_score < self.weights.min_confidence_to_accept:
                rejected_count += 1
                logger.debug(
                    f"Rejected '{candidate.title}' by '{candidate.artist_name}' - "
                    f"Score {final_score:.1f} < {self.weights.min_confidence_to_accept}. "
                    f"Reason: {match_result.reasoning}"
                )
                continue

            # --- Secondary Download Quality Scoring ---
            # (Note: These adjust the sort order among valid metadata matches,
            # they don't override a bad metadata match)

            # 1. Bitrate/Quality Bonus
            # If identifiers has bitrate, prefer higher (up to a point) or specific formats
            bitrate = candidate.identifiers.get('bitrate', 0) or 0
            if bitrate >= 320:
                final_score += 5  # Bonus for high quality
            elif bitrate < 192:
                final_score -= 10 # Penalty for low quality

            # 2. Peer Stats (Speed, Queue)
            upload_speed = candidate.identifiers.get('upload_speed', 0) or 0
            queue_length = candidate.identifiers.get('queue_length', 0) or 0
            free_slots = candidate.identifiers.get('free_upload_slots', 0) or 0

            if upload_speed > 1000000: # >1MB/s
                final_score += 5
            elif upload_speed < 50000: # <50KB/s
                final_score -= 5

            if free_slots > 0:
                final_score += 5

            if queue_length > 10:
                final_score -= 10
            elif queue_length > 50:
                final_score -= 20

            ranked_candidates.append((final_score, candidate))

        logger.info(
            f"Download candidate filtering: {len(candidates)} candidates, "
            f"{rejected_count} rejected, {len(ranked_candidates)} accepted"
        )

        if not ranked_candidates:
            try:
                from core.hook_manager import hook_manager
                plugin_match = hook_manager.apply_filters('ON_MATCH_FAILED', None, target_track=target_track.to_dict(), candidates=[c.to_dict() for c in candidates])
                if plugin_match is not None and isinstance(plugin_match, dict):
                    logger.info(f"Plugin salvaged failed match for: '{target_track.title}'")
                    return EchosyncTrack.from_dict(plugin_match)
            except Exception as e:
                logger.error(f"Error in ON_MATCH_FAILED hook: {e}")

            logger.warning(
                f"No candidates passed minimum confidence threshold ({self.weights.min_confidence_to_accept}%). "
                f"Target: '{target_track.title}' by '{target_track.artist_name}'"
            )
            return None

        # --- Size Sorting ---
        # Logic:
        # 1. Primary Sort: Final Score (Descending) - Metadata correctness & Quality score is king.
        # 2. Secondary Sort: File Size
        #    - If prefer_max_quality=True: Larger size is better (Desc)
        #    - If prefer_max_quality=False: Smaller (but valid) size is better (Asc)

        def sort_key(item):
            score, cand = item
            size = cand.file_size_bytes or cand.identifiers.get('size', 0) or 0

            if self.weights.prefer_max_quality:
                # Descending score, Descending size
                return (score, size)
            else:
                # Descending score, Ascending size (negate size to sort Ascending in a Descending sort?)
                # No, Python sort is stable and we can use a key.
                # If we sort by key descending: (High Score, High Size) works.
                # If we want (High Score, Low Size): We return (score, -size).
                return (score, -size)

        ranked_candidates.sort(key=sort_key, reverse=True)

        # Log top 3 for debugging
        logger.info(f"Top 3 download candidates for '{target_track.title}':")
        for score, cand in ranked_candidates[:3]:
            size_mb = (cand.identifiers.get('size', 0) / 1024 / 1024)
            logger.info(f"  Score: {score:.1f} | {cand.identifiers.get('provider_item_id')} | Speed: {cand.identifiers.get('upload_speed')} | Size: {size_mb:.1f}MB")

        return ranked_candidates[0][1]


def create_matcher(profile: ScoringProfile) -> WeightedMatchingEngine:
    """Convenience function to create a matcher with a profile"""
    return WeightedMatchingEngine(profile)


from core.provider import ServiceRegistry
ServiceRegistry.register_default('matching_engine', WeightedMatchingEngine)
