import re

with open("core/metadata/engine.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Imports
imports = """from core.metadata.plugins import get_acoustid_plugin, get_musicbrainz_plugin
from core.metadata.scoring import calculate_acoustid_duration_weight, calculate_text_duration_weight, score_acoustid_candidate
from core.metadata.cache import ChromaprintCache
from core.metadata.dsp import extract_physical_tags, probe_physical_audio
"""
text = re.sub(
    r"(from core\.tiered_logger import get_logger\n\nlogger = get_logger\(\"core\.metadata\.engine\"\)\n)",
    r"\1\n" + imports,
    text,
)

# 2. Remove calculate_acoustid_duration_weight & calculate_text_duration_weight
text = re.sub(
    r"def calculate_acoustid_duration_weight.*?(?=def calculate_text_duration_weight)", "", text, flags=re.DOTALL
)
text = re.sub(r"def calculate_text_duration_weight.*?(?=def extract_filename_title)", "", text, flags=re.DOTALL)

# 3. Replace _get_acoustid_plugin & _get_mb_plugin
text = re.sub(
    r"    def _get_acoustid_plugin\(self\) -> Any \| None:\n.*?(?=    def _get_mb_plugin)",
    r"    def _get_acoustid_plugin(self) -> Any | None:\n        return get_acoustid_plugin(self._acoustid_provider)\n\n",
    text,
    flags=re.DOTALL,
)
text = re.sub(
    r"    def _get_mb_plugin\(self\) -> Any \| None:\n.*?(?=    def score_candidate)",
    r"    def _get_mb_plugin(self) -> Any | None:\n        return get_musicbrainz_plugin(self._metadata_provider)\n\n",
    text,
    flags=re.DOTALL,
)

# 4. Replace score_candidate
text = re.sub(
    r"    def score_candidate\(\n        self,\n        candidate: dict\[str, Any\],\n        baseline_title: str,\n        file_duration_ms: int,\n        baseline_artist: str \| None = None,\n        baseline_album: str \| None = None,\n        filename: str \| None = None,\n    \) -> float:\n.*?(?=    def resolve_track)",
    r'''    def score_candidate(
        self,
        candidate: dict[str, Any],
        baseline_title: str,
        file_duration_ms: int,
        baseline_artist: str | None = None,
        baseline_album: str | None = None,
        filename: str | None = None,
    ) -> float:
        """Score AcoustID recording candidate by duration proximity, variant disambiguation penalties,
        and canonical studio release weighting using WeightedMatchingEngine(PROFILE_EXACT_SYNC).
        """
        return score_acoustid_candidate(
            matcher=self.matcher,
            candidate=candidate,
            baseline_title=baseline_title,
            file_duration_ms=file_duration_ms,
            baseline_artist=baseline_artist,
            baseline_album=baseline_album,
            filename=filename,
        )

''',
    text,
    flags=re.DOTALL,
)

# 5. Modify __init__ cache
text = re.sub(
    r"        import collections\n\n        self\._chromaprint_cache: collections\.OrderedDict\[str, dict\[str, Any\]\] = collections\.OrderedDict\(\)",
    r"        self.cache = ChromaprintCache()",
    text,
)
text = re.sub(
    r"    def invalidate_cache\(self, chromaprint: str \| None = None\) -> None:\n        \"\"\"Invalidate in-memory chromaprint cache entry or entire cache\.\"\"\"\n        if chromaprint:\n            self\._chromaprint_cache\.pop\(chromaprint, None\)\n        else:\n            self\._chromaprint_cache\.clear\(\)",
    r'    def invalidate_cache(self, chromaprint: str | None = None) -> None:\n        """Invalidate in-memory chromaprint cache entry or entire cache."""\n        self.cache.invalidate(chromaprint)',
    text,
)

# 6. Replace _check_local_chromaprint_cache
text = re.sub(
    r"    def _check_local_chromaprint_cache\(self, chromaprint: str, sync_id: str \| None = None\) -> dict\[str, Any\] \| None:\n.*?(?=    def _resolve_acoustid)",
    r"    def _check_local_chromaprint_cache(self, chromaprint: str, sync_id: str | None = None) -> dict[str, Any] | None:\n        return self.cache.check_local(chromaprint, sync_id)\n\n",
    text,
    flags=re.DOTALL,
)


# 7. Replace physical inspection in _resolve_acoustid_isolated
replace_isolated = r"""        # ── Minimal physical inspection ────────────────────────────────────────
        raw_tags: dict[str, Any] = {}
        duration_ms = 0
        channels = 2
        try:
            raw_tags = extract_physical_tags(file_path)
            raw_dur = raw_tags.get("duration_ms") or raw_tags.get("duration")
            if raw_dur is not None:
                d_val = float(raw_dur)
                duration_ms = round(d_val * 1000) if d_val < 10000 else round(d_val)

            raw_ch = raw_tags.get("channels")
            if raw_ch is not None:
                channels = int(raw_ch)
        except (ValueError, TypeError):
            channels = 2

        if request.duration_ms and duration_ms <= 0:
            duration_ms = request.duration_ms
        elif request.duration and duration_ms <= 0:
            d_val = float(request.duration)
            duration_ms = round(d_val * 1000) if d_val < 10000 else round(d_val)

        chromaprint, duration_ms = probe_physical_audio(
            file_path=file_path, 
            channels=channels, 
            duration_ms=duration_ms, 
            existing_chromaprint=request.chromaprint,
            log_prefix="[resolution_engine] [acoustid-isolated]"
        )
        if chromaprint:
            request.chromaprint = chromaprint
"""
text = re.sub(
    r"        # ── Minimal physical inspection ────────────────────────────────────────\n        raw_tags: dict\[str, Any\].*?(?=        # ── Stage 3: AcoustID \(isolated\))",
    replace_isolated,
    text,
    flags=re.DOTALL,
)


# 8. Replace physical inspection in _execute_waterfall
replace_waterfall = r"""        # ── Stage 1: Physical Inspection ──────────────────────────────────────
        raw_tags = extract_physical_tags(file_path)

        if not file_path.exists() and not raw_tags and not request.baseline_title:
            logger.warning(
                "[resolution_engine] File not found on disk and no metadata: %s",
                request.file_path,
            )
            return ResolutionResult(
                media_id=request.media_id,
                sync_id=request.sync_id,
                title=request.baseline_title or file_path.stem,
                artist=request.baseline_artist or "Unknown Artist",
                album=request.baseline_album,
                confidence_score=0.0,
                resolution_method="text_waterfall",
            )

        # Determine channel count: probe header tags or assume stereo
        channels = 2
        try:
            raw_ch = raw_tags.get("channels")
            if raw_ch is not None:
                channels = int(raw_ch)
        except (ValueError, TypeError):
            channels = 2

        # Extract duration from physical header if present
        duration_ms = 0
        raw_dur = raw_tags.get("duration_ms")
        if raw_dur is not None:
            try:
                duration_ms = int(raw_dur)
            except (ValueError, TypeError):
                duration_ms = 0
        elif raw_tags.get("duration") is not None:
            try:
                d_sec = float(raw_tags["duration"])
                duration_ms = round(d_sec * 1000) if d_sec < 10000 else round(d_sec)
            except (ValueError, TypeError):
                duration_ms = 0

        if request.duration_ms and duration_ms <= 0:
            duration_ms = request.duration_ms
        elif request.duration and duration_ms <= 0:
            d_val = float(request.duration)
            duration_ms = round(d_val * 1000) if d_val < 10000 else round(d_val)

        chromaprint, duration_ms = probe_physical_audio(
            file_path=file_path, 
            channels=channels, 
            duration_ms=duration_ms, 
            existing_chromaprint=request.chromaprint,
            log_prefix="[resolution_engine]"
        )
        if chromaprint:
            request.chromaprint = chromaprint
"""
text = re.sub(
    r'        # ── Stage 1: Physical Inspection ──────────────────────────────────────\n.*?tag_title = raw_tags\.get\("title"\)',
    replace_waterfall + '\n        tag_title = raw_tags.get("title")',
    text,
    flags=re.DOTALL,
)


with open("core/metadata/engine.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Refactoring complete.")
