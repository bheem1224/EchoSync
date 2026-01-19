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

from .soul_sync_track import SoulSyncTrack
from .scoring_profile import ScoringProfile, ScoringWeights
from .fingerprinting import FingerprintMatcher

logger = logging.getLogger(__name__)


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
    target_identifier: Optional[str] = None  # e.g., Plex ratingKey
    target_exists: bool = False  # True if identifier is present for target


class WeightedMatchingEngine:
    """
    Core weighted matching engine implementing 5-step gating logic
    """

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
        source: SoulSyncTrack,
        candidate: SoulSyncTrack,
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

        # ===== STEP 0a: ISRC INSTANT MATCH (highest confidence) =====
        # If both tracks have ISRC and they match exactly, instant 100% confidence
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
                    reasoning="ISRC match (identical recording - instant 100% confidence)"
                ), target_source, target_identifier)
            else:
                reasoning_parts.append("ISRC available but no match (different recordings)")

        # Continue with standard matching...
        return self._attach_target_context(
            self._calculate_standard_match(source, candidate),
            target_source,
            target_identifier,
        )

    def calculate_title_duration_match(
        self,
        source: SoulSyncTrack,
        candidate: SoulSyncTrack,
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
        source: SoulSyncTrack,
        candidate: SoulSyncTrack
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

        if fuzzy_score < self.weights.fuzzy_match_threshold:
            # If fuzzy match is below threshold, fail this match
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
        duration_score = self._calculate_duration_match(source, candidate)
        duration_contribution = duration_score * self.weights.duration_weight * 100

        reasoning_parts.append(
            f"Duration match: {duration_score:.1%} × {self.weights.duration_weight:.1%} = {duration_contribution:.1f} points"
        )

        score += duration_contribution
        max_possible_score += self.weights.duration_weight * 100

        # ===== STEP 5: QUALITY TIE-BREAKER =====
        if candidate.quality_tags:
            quality_bonus = self.weights.quality_bonus * 100
            score += quality_bonus
            reasoning_parts.append(f"Quality bonus applied: +{quality_bonus:.1f} points")
        else:
            reasoning_parts.append("No quality bonus (candidate has no quality tags)")

        max_possible_score += self.weights.quality_bonus * 100

        # ===== APPLY CUMULATIVE PENALTIES =====
        final_penalty = version_penalty + edition_penalty
        score -= final_penalty

        # ===== NORMALIZE SCORE TO 0-100 =====
        if max_possible_score > 0:
            normalized_score = (score / max_possible_score) * 100
        else:
            normalized_score = 0.0

        # Clamp to 0-100 range
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

    def _check_version_match(self, source: SoulSyncTrack, candidate: SoulSyncTrack) -> Tuple[bool, str]:
        """
        Check if versions match

        Returns:
            (matches: bool, reasoning: str)
        """

        # If either has no edition, consider it a match (no strong signal)
        if not source.edition and not candidate.edition:
            return True, "Both tracks have no version info"

        if not source.edition:
            return True, "Source has no version, accepting candidate version"

        if not candidate.edition:
            return True, "Candidate has no version, accepting source version"

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

    def _check_edition_match(self, source: SoulSyncTrack, candidate: SoulSyncTrack) -> Tuple[bool, str]:
        """
        Check if editions match (disc_number, etc)

        Returns:
            (matches: bool, reasoning: str)
        """
        # If source has disc_number, check if candidate matches
        if source.disc_number and candidate.disc_number:
            if source.disc_number == candidate.disc_number:
                return True, f"Disc numbers match: disc {source.disc_number}"
            else:
                return False, f"Disc number mismatch: disc {source.disc_number} vs {candidate.disc_number}"

        # No strong edition signals
        return True, "No edition info to compare"

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
    
    def _check_artist_subset_match(self, source: SoulSyncTrack, candidate: SoulSyncTrack) -> Tuple[bool, float, str]:
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

    def _calculate_fuzzy_text_match(self, source: SoulSyncTrack, candidate: SoulSyncTrack) -> float:
        """
        Calculate fuzzy text match score for title, artist, album.
        Includes artist subset rescue mechanism.

        Returns:
            Score 0.0-1.0
        """

        scores = []

        # Title match (most important)
        if source.title and candidate.title:
            title_score = self._fuzzy_match(source.title, candidate.title)
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

    def _calculate_duration_match(self, source: SoulSyncTrack, candidate: SoulSyncTrack) -> float:
        """
        Calculate duration match score

        Returns:
            Score 0.0-1.0 (1.0 = exact match, decreases with difference)
        """

        if not source.duration or not candidate.duration:
            # If either has no duration, assume match
            return 1.0

        diff_ms = abs(source.duration - candidate.duration)
        tolerance_ms = self.weights.duration_tolerance_ms

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

    def _normalize_string_for_comparison(self, s: str) -> str:
        """
        Normalize string for comparison (lowercase, remove special chars, strip featured artists)
        """

        import re
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
        target_track: SoulSyncTrack,
        candidates: list[SoulSyncTrack]
    ) -> Optional[SoulSyncTrack]:
        """
        Select the best download candidate from a list of raw search results.
        Uses the profile weights to score and rank candidates.

        Args:
            target_track: The track we want to find
            candidates: List of raw results from SlskdProvider

        Returns:
            The winning SoulSyncTrack or None if no acceptable match found
        """
        if not candidates:
            return None

        ranked_candidates = []

        for candidate in candidates:
            # --- Duration Gating (if enabled) ---
            if self.weights.enforce_duration_match and target_track.duration and candidate.duration:
                diff_ms = abs(target_track.duration - candidate.duration)
                if diff_ms > self.weights.duration_tolerance_ms:
                    continue  # Skip strictly

            # Calculate match score
            match_result = self.calculate_match(target_track, candidate)

            # Additional check: Quality/Peer Stats weighting
            # The standard calculate_match focuses on metadata correctness (Is this the right song?)
            # We add a secondary score component for "Is this a good file to download?"

            # Base metadata confidence
            final_score = match_result.confidence_score

            # Only consider candidates that pass the minimum confidence threshold for metadata
            if final_score < self.weights.min_confidence_to_accept:
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

        if not ranked_candidates:
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
