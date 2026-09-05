from typing import Any

from core.caching.plugin_cache import plugin_cache
from core.db.echo_sync_track import EchosyncTrack
from core.nexus_framework.plugin_SDK import (
    MetadataRichness,
    PlaylistSupport,
    PluginBase,
    ProviderCapabilities,
    SearchCapabilities,
)
from core.tiered_logger import get_logger

logger = get_logger("provider.acoustid")


class AcoustIDProvider(PluginBase):
    name = "EchoSync.acoustid"
    service_type = "metadata"
    capabilities = ProviderCapabilities(
        name="EchoSync.acoustid",
        supports_playlists=PlaylistSupport.NONE,
        search=SearchCapabilities(
            tracks=False, artists=False, albums=False, playlists=False
        ),
        metadata=MetadataRichness.LOW,
        supports_cover_art=False,
        supports_lyrics=False,
        supports_user_auth=False,
        supports_library_scan=False,
        supports_streaming=False,
        supports_downloads=False,
        supports_fingerprinting=True,  # Special capability for fingerprinting
        fingerprint_algorithms=["chromaprint"],
        pre_filters=[],
    )

    def __init__(self):
        super().__init__()
        self.api_base = "https://api.acoustid.org/v2"

        # Configure rate limit: 1 request/second per AcoustID API guidelines
        from core.request_manager import RateLimitConfig

        self.http.rate = RateLimitConfig(requests_per_second=1.0)

    def _get_api_key(self) -> str | None:
        """Get AcoustID API key from namespaced config with proper decryption."""
        # Check namespaced config/secrets first
        api_key = self.secrets.get("api_key") or self.config.get("api_key")

        if api_key:
            api_key = str(api_key).strip()
            if api_key.startswith("enc:"):
                from core.security import decrypt_string

                api_key = decrypt_string(api_key)
            logger.debug(
                f"AcoustID API key loaded from namespaced storage (length={len(api_key)})"
            )
            return api_key or None

        # Fallback to global config (legacy)
        api_key = self.sdk.config.get("acoustid.api_key")
        if api_key:
            api_key = str(api_key).strip()
            if api_key.startswith("enc:"):
                from core.security import decrypt_string

                api_key = decrypt_string(api_key)
            logger.debug(
                f"AcoustID API key loaded from global config (length={len(api_key)})"
            )
        return api_key or None

    def _get_submit_keys(self) -> tuple[str | None, str | None]:
        """Get AcoustID client and user API keys for submission endpoints."""
        client_key = self.secrets.get("api_key") or self.config.get("api_key")
        user_key = self.secrets.get("user_api_key") or self.config.get("user_api_key")

        from core.security import decrypt_string

        if client_key and str(client_key).startswith("enc:"):
            client_key = decrypt_string(str(client_key))
        if user_key and str(user_key).startswith("enc:"):
            user_key = decrypt_string(str(user_key))

        client_key = str(client_key).strip() if client_key else None
        user_key = str(user_key).strip() if user_key else None

        if not client_key:
            client_key = self._get_api_key()

        if not user_key:
            cfg_user_key = self.sdk.config.get("acoustid.user_api_key")
            if cfg_user_key:
                user_key = str(cfg_user_key).strip()

        return client_key or None, user_key or None

    @plugin_cache(ttl_seconds=2592000)
    def resolve_fingerprint_details(
        self, fingerprint: str, duration: int
    ) -> dict[str, Any]:
        """
        Resolve fingerprint and return both AcoustID result ID and MBID candidates.

        Returns:
            {
                "acoustid_id": Optional[str],
                "mbids": List[str],
                "score": Optional[float]
            }
        """
        api_key = self._get_api_key()
        if not api_key:
            logger.warning("AcoustID API key not configured")
            return {"acoustid_id": None, "mbids": [], "score": None, "match_status": "UNRESOLVED"}

        if not fingerprint or not fingerprint.strip():
            logger.warning("Empty fingerprint provided")
            return {"acoustid_id": None, "mbids": [], "score": None, "match_status": "UNRESOLVED"}

        try:
            duration_val = float(duration)
        except (ValueError, TypeError):
            duration_val = 0.0

        if duration_val > 10000:
            logger.debug(
                f"AcoustID duration abnormally high ({duration_val}), assuming milliseconds and converting to seconds."
            )
            duration_val = duration_val / 1000.0

        duration_int = int(round(duration_val))

        if duration_int <= 0:
            logger.warning(
                "[system] - Aborting AcoustID lookup: Invalid track duration (0s) detected."
            )
            return {"acoustid_id": None, "mbids": [], "score": None, "match_status": "UNRESOLVED"}
        payload = {
            "client": api_key,
            "meta": "recordingids",
            "fingerprint": fingerprint.strip(),
            "duration": duration_int,
        }

        try:
            logger.debug(
                f"AcoustID payload: fingerprint_len={len(fingerprint)}, duration={duration}, api_key_len={len(api_key)}"
            )
            response = self.http.post(f"{self.api_base}/lookup", data=payload)

            if response.status_code != 200:
                if response.status_code == 400:
                    logger.warning(
                        f"AcoustID lookup rejected (400). Response: {response.text[:200]}"
                    )
                else:
                    logger.error(
                        f"AcoustID API error: {response.status_code} - {response.text[:200]}"
                    )
                return {"acoustid_id": None, "mbids": [], "score": None, "match_status": "UNRESOLVED"}

            data = response.json()
            if data.get("status") != "ok":
                logger.error(f"AcoustID API returned error status: {data}")
                return {"acoustid_id": None, "mbids": [], "score": None, "match_status": "UNRESOLVED"}

            results = data.get("results") or []
            if not results:
                logger.debug(
                    "AcoustID lookup succeeded but found 0 matches for fingerprint."
                )
            mbids: list[str] = []
            seen_mbid = set()
            best_result: dict[str, Any] | None = None
            best_score = -1.0

            for result in results:
                if not isinstance(result, dict):
                    continue

                try:
                    score = float(result.get("score") or 0.0)
                except Exception:
                    score = 0.0

                if best_result is None or score > best_score:
                    best_result = result
                    best_score = score

                for recording in result.get("recordings", []) or []:
                    if not isinstance(recording, dict):
                        continue
                    mbid = str(recording.get("id") or "").strip()
                    if mbid and mbid not in seen_mbid:
                        seen_mbid.add(mbid)
                        mbids.append(mbid)

            acoustid_id = None
            if isinstance(best_result, dict):
                result_id = str(best_result.get("id") or "").strip()
                if result_id:
                    acoustid_id = result_id

            match_status = "MATCHED" if (acoustid_id or mbids) else "UNRESOLVED"
            return {
                "acoustid_id": acoustid_id,
                "mbids": mbids,
                "score": best_score if best_score >= 0.0 else None,
                "match_status": match_status,
            }
        except Exception as e:
            logger.error(f"Failed to resolve fingerprint: {e}")
            return {"acoustid_id": None, "mbids": [], "score": None, "match_status": "UNRESOLVED"}

    def resolve_fingerprint(self, fingerprint: str, duration: int) -> list[str]:
        """
        Exchange Chromaprint for MusicBrainz Recording IDs.

        Args:
            fingerprint: The raw fingerprint string
            duration: Duration in seconds (integer)

        Returns:
            List of MusicBrainz Recording IDs (MBIDs)
        """
        details = self.resolve_fingerprint_details(fingerprint, duration)
        mbids = details.get("mbids") or []
        return [str(mbid).strip() for mbid in mbids if str(mbid).strip()]

    def submit_fingerprint(self, fingerprint: str, duration: int, mbid: str) -> bool:
        """Submit fingerprint to AcoustID for community contribution."""
        client_key, user_key = self._get_submit_keys()
        if not client_key or not user_key:
            logger.debug("Skipping AcoustID submit: missing client or user API key")
            return False

        # Opt-in check: only submit if auto_contribute is enabled in settings
        auto_contribute = self.config.get("auto_contribute")
        if not (auto_contribute == "true" or auto_contribute is True):
            logger.debug("Skipping AcoustID submission: auto_contribute is disabled")
            return False

        if (
            not fingerprint
            or not str(fingerprint).strip()
            or not mbid
            or not str(mbid).strip()
        ):
            logger.debug("Skipping AcoustID submit: missing fingerprint or MBID")
            return False

        try:
            duration_val = float(duration)
            if duration_val > 10000:
                duration_val = duration_val / 1000.0
            duration_int = int(round(duration_val))
            if duration_int <= 0:
                return False
        except Exception:
            logger.debug("Skipping AcoustID submit: invalid duration")
            return False

        payload = {
            "client": client_key,
            "user": user_key,
            "fingerprint.0": str(fingerprint).strip(),
            "duration.0": duration_int,
            "mbid.0": str(mbid).strip(),
        }

        try:
            response = self.http.post(f"{self.api_base}/submit", data=payload)
            if response.status_code != 200:
                logger.warning(
                    f"AcoustID submit failed ({response.status_code}): {response.text[:200]}"
                )
                return False

            data = response.json() or {}
            if data.get("status") != "ok":
                logger.warning(f"AcoustID submit returned non-ok response: {data}")
                return False

            logger.info("Submitted AcoustID fingerprint contribution")
            return True
        except Exception as e:
            logger.warning(f"AcoustID submit failed: {e}")
            return False

    def queue_fingerprint_submission(self, fingerprint: str, duration: int, mbid: str):
        """Queue a background job to submit an AcoustID fingerprint."""
        import time

        job_name = f"submit_{mbid}_{int(time.time() * 1000)}"

        def submit_job():
            self.submit_fingerprint(fingerprint, duration, mbid)

        self.sdk.jobs.register_job(
            name=job_name,
            func=submit_job,
            enabled=True,
            max_retries=3,
            backoff_base=10.0,
        )
        self.sdk.jobs.dispatch_job(job_name)

    # Implement abstract methods
    def authenticate(self, **kwargs) -> bool:
        return True

    def search(
        self, query: str, type: str = "track", limit: int = 10
    ) -> list[EchosyncTrack]:
        return []

    def get_track(self, track_id: str) -> EchosyncTrack | None:
        return None

    def get_album(self, album_id: str) -> dict[str, Any] | None:
        return None

    def get_artist(self, artist_id: str) -> dict[str, Any] | None:
        return None

    def get_user_playlists(self, user_id: str | None = None) -> list[dict[str, Any]]:
        return []

    def get_playlist_tracks(self, playlist_id: str) -> list[EchosyncTrack]:
        return []

    def is_configured(self) -> bool:
        return bool(self._get_api_key())

    def get_logo_url(self) -> str:
        return "https://acoustid.org/static/logo.png"
