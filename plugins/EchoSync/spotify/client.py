import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

try:
    from spotipy.cache_handler import CacheHandler
except Exception:
    CacheHandler = object
import time
from collections.abc import Iterator
from typing import Any

from core.caching.plugin_cache import plugin_cache
from core.db.echo_sync_track import EchosyncTrack
from core.nexus_framework.plugin_loader import PluginRegistry
from core.nexus_framework.plugin_SDK import (
    MetadataRichness,
    PlaylistSupport,
    ProviderCapabilities,
    SearchCapabilities,
    SyncServiceProvider,
)
from core.tiered_logger import get_logger

logger = get_logger("spotify_client")


class ConfigCacheHandler(CacheHandler):
    """Spotipy CacheHandler that persists tokens into ConfigManager for the active Spotify account."""

    def __init__(self, account_id: int | None):
        self.account_id = account_id
        logger.debug(f"Initialized ConfigCacheHandler for account {account_id}")

    def _resolve_account_id(self) -> int | None:
        if self.account_id is not None:
            return self.account_id
        try:
            from core.account_manager import AccountManager

            accounts = AccountManager.list_accounts("spotify")
        except Exception:
            accounts = []
        if not accounts:
            try:
                from core.file_handling.storage import get_storage_service

                accounts = get_storage_service().list_accounts("spotify")
            except Exception:
                accounts = []
        active_account = next(
            (
                acc
                for acc in accounts
                if acc.get("is_active")
                or acc.get("authenticated")
                or acc.get("is_authenticated")
            ),
            None,
        )
        if not active_account and accounts:
            active_account = accounts[0]
        if active_account:
            self.account_id = active_account.get("id") or active_account.get(
                "account_id"
            )
        return self.account_id

    def get_cached_token(self):
        """Load cached token from storage database.

        Returns a dict with access_token, refresh_token, expires_at, and scope if available,
        or None if no token is stored.
        """
        try:
            target_account_id = self._resolve_account_id()
            if not target_account_id:
                return None

            from database.config_database import get_config_database

            db = get_config_database()
            token_data = db.get_account_token(target_account_id)

            if not token_data:
                try:
                    from core.nexus_framework.plugin_SDK import sdk

                    token_data = sdk.accounts.get_token(target_account_id)
                except Exception:
                    token_data = None

            if not token_data:
                logger.debug(
                    f"No token data found in storage for account {target_account_id}"
                )
                return None

            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_at = token_data.get("expires_at")
            scope = token_data.get(
                "scope",
                "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email playlist-modify-public playlist-modify-private",
            )

            if access_token == "REDACTED":
                access_token = None
            if refresh_token == "REDACTED":
                refresh_token = None

            logger.debug(
                f"Loaded token data for account {target_account_id}: access={bool(access_token)}, "
                f"refresh={bool(refresh_token)}, expires={expires_at}, scope={scope}"
            )

            if not access_token and not refresh_token:
                return None

            # Return full token info - Spotipy will handle refresh if needed
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at or 0,
                "scope": scope,
                "token_type": "Bearer",
            }
        except Exception as e:
            logger.error(
                f"Error loading cached Spotify token for account {self.account_id}: {e}",
                exc_info=True,
            )
            return None

    def save_token_to_cache(self, token_info):
        """Save token to storage database.

        This is called by Spotipy after getting a new token or refreshing.
        Ensures both access_token and refresh_token are persisted.
        """
        try:
            target_account_id = self._resolve_account_id()
            if not target_account_id:
                logger.warning("No account_id specified; cannot save Spotify tokens")
                return

            if not token_info:
                logger.warning(
                    f"No token_info provided to save for account {target_account_id}"
                )
                return

            from database.config_database import get_config_database

            db = get_config_database()

            access_token = token_info.get("access_token")
            refresh_token = token_info.get("refresh_token")
            expires_at = token_info.get("expires_at")
            scope = token_info.get(
                "scope",
                "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email playlist-modify-public playlist-modify-private",
            )

            if not access_token:
                logger.warning(
                    f"No access_token in token_info for account {target_account_id}"
                )
                return

            # If no refresh token provided, try to preserve existing one
            if not refresh_token:
                existing_token = db.get_account_token(target_account_id)
                if (
                    existing_token
                    and existing_token.get("refresh_token")
                    and existing_token.get("refresh_token") != "REDACTED"
                ):
                    refresh_token = existing_token.get("refresh_token")
                    logger.debug(
                        f"Preserving existing refresh_token for account {target_account_id}"
                    )

            logger.debug(
                f"Saving token for account {target_account_id}: access={bool(access_token)}, refresh={bool(refresh_token)}, expires={expires_at}"
            )

            success = db.save_account_token(
                account_id=target_account_id,
                access_token=access_token,
                refresh_token=refresh_token if refresh_token else None,
                token_type="Bearer",
                expires_at=expires_at,
                scope=scope,
            )

            if success:
                logger.info(
                    f"Successfully persisted Spotify tokens for account {target_account_id}"
                )
                try:
                    db.mark_account_authenticated(target_account_id)
                    db.toggle_account_active(target_account_id, True)
                except Exception as e:
                    logger.debug(f"Failed to mark account as authenticated: {e}")
            else:
                logger.error(
                    f"Failed to save Spotify tokens for account {target_account_id}"
                )
        except Exception as e:
            logger.error(
                f"Error saving Spotify token to cache for account {self.account_id}: {e}"
            )


class CallbackBypassCacheHandler(CacheHandler):
    """Cache handler used only during OAuth callback code exchange.

    It intentionally bypasses normal cached-token retrieval so Spotipy is forced
    to exchange the incoming authorization code and return fresh token_info.
    """

    def get_cached_token(self):
        return None

    def save_token_to_cache(self, token_info):
        return


class SpotifyClient(SyncServiceProvider):
    name = "EchoSync.spotify"
    category = "provider"
    supports_downloads = False
    supports_isrc_lookup = True
    rate_limit = 5.0  # 5 requests/second rate limit
    capabilities = ProviderCapabilities(
        name="spotify",
        supports_playlists=PlaylistSupport.READ_WRITE,
        search=SearchCapabilities(
            tracks=True, artists=True, albums=True, playlists=True
        ),
        metadata=MetadataRichness.HIGH,
        supports_cover_art=True,
        supports_lyrics=False,
        supports_user_auth=True,
        supports_library_scan=False,
        supports_streaming=True,
        supports_downloads=False,
        supports_metadata_fetch=True,
        supports_isrc_lookup=True,
        playlist_algorithms=["spotify_mood", "spotify_energy", "spotify_newness"],
    )

    def __init__(self, account_id: int | None = None):
        super().__init__()  # Initialize PluginBase which sets up rate-limited HTTP client
        self.sp: spotipy.Spotify | None = None
        self.user_id: str | None = None
        self.account_id: int | None = account_id

        # Auto-detect active account if not provided
        if self.account_id is None:
            self._resolve_account_id()

        # Initialize the cache manager
        try:
            from .cache_manager import SpotifyCacheManager

            self.cache_manager = SpotifyCacheManager(sdk=self.sdk)
        except Exception as e:
            logger.error(f"Failed to initialize SpotifyCacheManager: {e}")
            self.cache_manager = None

        self._setup_client()
        PluginRegistry.register(SpotifyClient)
        self._register_health_check()

    def _register_health_check(self):
        """Register periodic health check for Spotify API."""
        if not self.is_configured():
            return

        from core.health_check import HealthCheckResult

        def spotify_health_check() -> HealthCheckResult:
            try:
                if not self.sp:
                    return HealthCheckResult(
                        service_name="spotify",
                        status="unhealthy",
                        message="Spotify client not initialized",
                    )

                # Check authentication status WITHOUT triggering browser popup
                # Use token cache check instead of API call
                if not self.is_authenticated():
                    # Check if it failed because the refresh token was missing or revoked
                    auth_manager = getattr(self.sp, "auth_manager", None)
                    cached_token = (
                        auth_manager.cache_handler.get_cached_token()
                        if auth_manager and getattr(auth_manager, "cache_handler", None)
                        else None
                    )
                    if cached_token and cached_token.get("refresh_token"):
                        msg = "Spotify refresh token failed - please re-authenticate"
                    else:
                        msg = "Spotify token missing - please authenticate"

                    return HealthCheckResult(
                        service_name="spotify", status="unhealthy", message=msg
                    )

                return HealthCheckResult(
                    service_name="spotify",
                    status="healthy",
                    message="Spotify token is valid",
                )
            except Exception as e:
                return HealthCheckResult(
                    service_name="spotify",
                    status="unhealthy",
                    message=f"Spotify health check error: {e!s}",
                )

        self.sdk.health.register(spotify_health_check, interval_seconds=300)

    def _resolve_account_id(self) -> int | None:
        """Resolve active or default Spotify account ID if none set."""
        if self.account_id is not None:
            return self.account_id

        accounts = []
        try:
            from core.account_manager import AccountManager

            accounts = AccountManager.list_accounts("spotify")
        except Exception:
            accounts = []
        if not accounts:
            try:
                from core.file_handling.storage import get_storage_service

                accounts = get_storage_service().list_accounts("spotify")
            except Exception:
                accounts = []

        if not accounts:
            return None

        # Check for explicit active account ID from config if that account exists
        try:
            active_id = self.sdk.config.get("active_spotify_account_id")
            if active_id is not None:
                matching = next(
                    (
                        acc
                        for acc in accounts
                        if (acc.get("id") or acc.get("account_id")) == active_id
                    ),
                    None,
                )
                if matching:
                    self.account_id = active_id
                    return self.account_id
        except Exception:
            pass

        active_account = next(
            (
                acc
                for acc in accounts
                if acc.get("is_active")
                or acc.get("authenticated")
                or acc.get("is_authenticated")
            ),
            None,
        )
        if not active_account and accounts:
            active_account = accounts[0]

        if active_account:
            self.account_id = active_account.get("id") or active_account.get(
                "account_id"
            )
            logger.info(f"Defaulting to Spotify account: {self.account_id}")

        return self.account_id

    def _setup_client(self):
        try:
            self._resolve_account_id()
            creds = {"client_id": None, "client_secret": None, "redirect_uri": None}

            # 0. Check unified ConfigManager service credentials
            try:
                from core.settings import config_manager

                service_creds = config_manager.get_service_credentials("spotify") or {}
                if service_creds.get("client_id"):
                    creds["client_id"] = service_creds["client_id"]
                if service_creds.get("client_secret"):
                    creds["client_secret"] = service_creds["client_secret"]
                if service_creds.get("redirect_uri"):
                    creds["redirect_uri"] = service_creds["redirect_uri"]
            except Exception:
                pass

            # 1. Check account object if account_id is provided
            if self.account_id is not None:
                try:
                    from core.account_manager import AccountManager

                    account = AccountManager.get_account("spotify", self.account_id)
                    if account:
                        creds["client_id"] = (
                            account.get("client_id") or creds["client_id"]
                        )
                        creds["client_secret"] = (
                            account.get("client_secret") or creds["client_secret"]
                        )
                        creds["redirect_uri"] = (
                            account.get("redirect_uri") or creds["redirect_uri"]
                        )
                except Exception:
                    pass

            # 2. Check Plugin SDK config & secrets namespace
            if not creds["client_id"]:
                try:
                    creds["client_id"] = self.sdk.config.get("client_id") or None
                except Exception:
                    pass
            if not creds["client_secret"]:
                try:
                    creds["client_secret"] = (
                        self.sdk.secrets.get("client_secret") or None
                    )
                except Exception:
                    pass
            if not creds["redirect_uri"]:
                try:
                    creds["redirect_uri"] = self.sdk.config.get("redirect_uri") or None
                except Exception:
                    pass

            # 3. Check Database service_config (canonical ID 2391116200, EchoSync.Spotify, Spotify, spotify)
            try:
                from database.config_database import get_config_database

                db = get_config_database()
                for lookup_key in [
                    2391116200,
                    "EchoSync.Spotify",
                    "EchoSync.spotify",
                    "Spotify",
                    "spotify",
                ]:
                    if creds["client_id"] and creds["client_secret"]:
                        break
                    svc_id = db.get_service_id(lookup_key)
                    if svc_id:
                        if not creds["client_id"]:
                            creds["client_id"] = db.get_service_config(
                                svc_id, "client_id"
                            )
                        if not creds["client_secret"]:
                            creds["client_secret"] = db.get_service_config(
                                svc_id, "client_secret"
                            )
                        if not creds["redirect_uri"]:
                            creds["redirect_uri"] = db.get_service_config(
                                svc_id, "redirect_uri"
                            )
            except Exception:
                pass

            # 4. Fallback to legacy storage service / AccountManager
            try:
                from core.account_manager import AccountManager

                if not creds["client_id"]:
                    creds["client_id"] = AccountManager.get_service_config(
                        "spotify", "client_id"
                    )
                if not creds["client_secret"]:
                    creds["client_secret"] = AccountManager.get_service_config(
                        "spotify", "client_secret"
                    )
                if not creds["redirect_uri"]:
                    creds["redirect_uri"] = AccountManager.get_service_config(
                        "spotify", "redirect_uri"
                    )
            except Exception:
                pass

            if not creds["client_id"] or not creds["client_secret"]:
                logger.debug(
                    f"Spotify credentials not configured (account_id={self.account_id})"
                )
                return

            if not creds["redirect_uri"]:
                from core.network_utils import get_lan_ip

                creds["redirect_uri"] = (
                    f"https://{get_lan_ip()}:5001/api/oauth/callback/plugins/spotify"
                )

            # Initialize cache handler and pre-load token to inspect auth state
            self.cache_handler = ConfigCacheHandler(self.account_id)
            preloaded_token = self.cache_handler.get_cached_token()

            if preloaded_token or self.account_id is not None:
                # User OAuth flow
                default_scope = (
                    "user-library-read user-read-private playlist-read-private "
                    "playlist-read-collaborative user-read-email playlist-modify-public "
                    "playlist-modify-private"
                )
                if preloaded_token and preloaded_token.get("scope"):
                    scope = preloaded_token.get("scope")
                    logger.debug(
                        f"Using existing cached scope for account {self.account_id}: {scope}"
                    )
                else:
                    scope = default_scope

                auth_manager = SpotifyOAuth(
                    client_id=creds["client_id"],
                    client_secret=creds["client_secret"],
                    redirect_uri=creds["redirect_uri"],
                    scope=scope,
                    cache_handler=self.cache_handler,
                    show_dialog=False,
                    open_browser=False,
                )

                # optionally refresh token if expired/refreshable
                try:
                    cached = auth_manager.cache_handler.get_cached_token()
                    if cached and cached.get("access_token"):
                        logger.info(
                            f"Using valid cached access token for Spotify account {self.account_id}"
                        )
                    elif cached and cached.get("refresh_token"):
                        logger.debug(
                            f"Refresh token found for account {self.account_id}, attempting silent refresh"
                        )
                        try:
                            new_token = auth_manager.refresh_access_token(
                                cached.get("refresh_token")
                            )
                            if new_token and new_token.get("access_token"):
                                logger.info(
                                    f"Successfully refreshed Spotify token for account {self.account_id}"
                                )
                            else:
                                logger.warning(
                                    f"Refresh token refresh returned no access token for account {self.account_id}"
                                )
                        except Exception as e:
                            logger.warning(
                                f"Failed to refresh Spotify token for account {self.account_id}: {e}"
                            )
                    else:
                        logger.debug(
                            f"Cached token invalid/absent for account {self.account_id} (after validation). "
                            f"Raw token info: {cached}. User authentication required."
                        )
                except Exception as e:
                    logger.debug(f"Error checking/refreshing cached token: {e}")

                self.sp = spotipy.Spotify(auth_manager=auth_manager)
                logger.info("Spotify client initialized successfully with OAuth")
            else:
                # Client credentials fallback flow for public catalog access
                client_credentials_manager = SpotifyClientCredentials(
                    client_id=creds["client_id"], client_secret=creds["client_secret"]
                )
                self.sp = spotipy.Spotify(
                    client_credentials_manager=client_credentials_manager
                )
                logger.info(
                    "Spotify client initialized successfully with Client Credentials flow"
                )

            self.user_id = None

        except Exception as e:
            logger.error(f"Failed to initialize Spotify client: {e}")
            self.sp = None

    def authenticate(self, **kwargs) -> bool:
        return self.is_authenticated()

    def ensure_authenticated(self) -> bool:
        """Ensure client is configured and authenticated, attempting resolution if uninitialized."""
        if self.is_authenticated():
            return True
        self._setup_client()
        return self.is_authenticated()

    def is_authenticated(self) -> bool:
        """Check if currently authenticated with Spotify.

        Returns True if valid token exists (not expired and can call API).
        Returns False if token is invalid, expired, or missing.
        Does NOT attempt to open browser or trigger auth flow.
        """
        if self.sp is None:
            logger.debug("Spotify client not initialized")
            return False
        try:
            # 1. Check if client credentials manager is configured
            if getattr(self.sp, "client_credentials_manager", None) is not None:
                return True

            # 2. Check OAuth auth manager
            auth_manager = getattr(self.sp, "auth_manager", None)
            if not auth_manager:
                return False

            cached_token = (
                auth_manager.cache_handler.get_cached_token()
                if getattr(auth_manager, "cache_handler", None)
                else None
            )
            if not cached_token:
                return False

            # Check if token exists and is not expired
            access_token = cached_token.get("access_token")
            expires_at = cached_token.get("expires_at", 0)

            if not access_token:
                return False

            # Check if token is expired (with 60 second buffer)
            import time

            if time.time() > (expires_at - 60):
                logger.debug(
                    f"Spotify token expired or expiring soon for account {self.account_id}. Attempting auto-refresh..."
                )
                refresh_token = cached_token.get("refresh_token")
                if refresh_token:
                    try:
                        new_token = auth_manager.refresh_access_token(refresh_token)
                        if new_token and new_token.get("access_token"):
                            logger.info(
                                f"Silently refreshed Spotify token for account {self.account_id}"
                            )
                            return True
                        else:
                            logger.warning(
                                f"Auto-refresh failed for account {self.account_id}: no access token returned"
                            )
                            return False
                    except Exception as e:
                        logger.warning(
                            f"Auto-refresh failed for account {self.account_id}: {e}"
                        )
                        return False
                else:
                    logger.debug(
                        f"No refresh token available for account {self.account_id}"
                    )
                    return False

            return True
        except Exception as e:
            logger.debug(f"Error checking Spotify authentication: {e}")
            return False

    def handle_oauth_callback(self, args: dict[str, str]) -> Any:
        """Handle the OAuth callback redirect from the Spotify authorization page."""
        from flask import jsonify, redirect
        from spotipy.oauth2 import SpotifyOAuth

        from core.file_handling.storage import get_storage_service

        try:
            code = args.get("code")
            state = args.get("state")  # account_id
            error = args.get("error")

            if error:
                error_description = args.get("error_description", error)
                logger.error(f"Spotify OAuth error: {error_description}")
                html = f"<html><body style='font-family: Arial, sans-serif;'><h2>Spotify Authentication Failed</h2><p><strong>Error:</strong> {error_description}</p><p>Please try again or check your Spotify app settings.</p></body></html>"
                return html, 400, {"Content-Type": "text/html"}

            if not code:
                logger.error("OAuth callback missing code parameter")
                return jsonify({"error": "Missing authorization code"}), 400

            if not state:
                logger.error("OAuth callback missing state parameter (account id)")
                return jsonify({"error": "Missing state parameter (account ID)"}), 400

            try:
                account_id = int(state)
            except (ValueError, TypeError):
                account_id = None
            from core.file_handling.storage import get_storage_service

            storage = get_storage_service()
            client_id = storage.get_service_config("spotify", "client_id")
            client_secret = storage.get_service_config("spotify", "client_secret")
            redirect_uri = self.get_oauth_redirect_uri()

            if not client_id or not client_secret:
                return jsonify(
                    {"error": "Spotify client_id/client_secret not configured"}
                ), 400

            auth_manager = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,  # Decrypted by get_service_config
                redirect_uri=redirect_uri,
                scope="user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email playlist-modify-public playlist-modify-private",
                cache_handler=CallbackBypassCacheHandler(),
            )

            try:
                token_info = auth_manager.get_access_token(code, as_dict=True)
            except TypeError:
                token_info = auth_manager.get_access_token(code)

            if not token_info:
                return jsonify({"error": "Failed to exchange code for token"}), 400

            access_token = token_info.get("access_token")
            refresh_token = token_info.get("refresh_token")
            expires_at = token_info.get("expires_at")
            scope = (
                token_info.get("scope")
                or "user-library-read user-read-private playlist-read-private playlist-read-collaborative user-read-email playlist-modify-public playlist-modify-private"
            )

            if not account_id:
                account_id = storage.ensure_account(
                    "spotify", account_name=f"spotify_{int(time.time())}"
                )

            try:
                storage.save_account_token(
                    account_id, access_token, refresh_token, "Bearer", expires_at, scope
                )
                storage.mark_account_authenticated(account_id)
            except Exception as e:
                logger.error(f"Failed to persist tokens to config.db: {e}")

            try:
                storage.toggle_account_active(account_id, True)
            except Exception:
                pass

            # Generate redirect URL using Flask request context
            from flask import request as flask_request

            ui_base = storage.get_service_config("webui", "base_url")
            if ui_base:
                ui_redirect = ui_base.rstrip("/") + "/settings/music-services"
            else:
                # Use actual request host instead of hardcoded localhost
                scheme = flask_request.scheme
                host = flask_request.host
                ui_redirect = f"{scheme}://{host}/settings/music-services"
            return redirect(ui_redirect)

        except Exception as e:
            logger.error(f"Spotify callback error: {e}", exc_info=True)
            error_html = "<html><body style='font-family: Arial, sans-serif;'><h2>Spotify Authentication Failed</h2><p>An unexpected error occurred during Spotify authentication. Please try again.</p></body></html>"
            return error_html, 500, {"Content-Type": "text/html"}

    def is_configured(self) -> bool:
        if self.sp is not None:
            return True

        # Check SDK config/secrets
        try:
            if self.sdk.config.get("client_id") and self.sdk.secrets.get(
                "client_secret"
            ):
                return True
        except Exception:
            pass

        # Check DB service_config
        try:
            from database.config_database import get_config_database

            db = get_config_database()
            for lookup_key in [
                2391116200,
                "EchoSync.Spotify",
                "EchoSync.spotify",
                "Spotify",
                "spotify",
            ]:
                svc_id = db.get_service_id(lookup_key)
                if (
                    svc_id
                    and db.get_service_config(svc_id, "client_id")
                    and db.get_service_config(svc_id, "client_secret")
                ):
                    return True
        except Exception:
            pass

        # Check storage if we can potentially configure it
        from core.file_handling.storage import get_storage_service

        storage = get_storage_service()
        return bool(
            storage.get_service_config("spotify", "client_id")
            and storage.get_service_config("spotify", "client_secret")
        )

    def get_logo_url(self) -> str:
        return "/static/img/spotify_logo.png"

    def _ensure_user_id(self) -> bool:
        if self.user_id is None and self.sp is not None:
            try:
                user_info = self.sp.current_user()
                self.user_id = user_info["id"]
                return True
            except Exception as e:
                logger.error(f"Failed to fetch user info: {e}")
                return False
        return self.user_id is not None

    def _convert_track(
        self, spotify_track_data: dict[str, Any]
    ) -> EchosyncTrack | None:
        """Convert Spotify track data to EchosyncTrack."""
        if not spotify_track_data or not spotify_track_data.get("name"):
            return None

        try:
            # Extract basic fields
            raw_title = spotify_track_data.get("name")

            # Artist handling
            artists = spotify_track_data.get("artists", [])
            artist_name = artists[0].get("name") if artists else "Unknown Artist"

            # Album handling
            album = spotify_track_data.get("album", {})
            album_title = album.get("name") or ""
            release_date = album.get("release_date", "")
            release_year = (
                int(release_date[:4])
                if release_date and len(release_date) >= 4
                else None
            )

            # IDs
            track_id = spotify_track_data.get("id")
            isrc = None
            external_ids = spotify_track_data.get("external_ids", {})
            if external_ids:
                isrc = external_ids.get("isrc")

            return self.create_echo_sync_track(
                title=raw_title,
                artist=artist_name,
                album=album_title,
                duration_ms=spotify_track_data.get("duration_ms"),
                track_number=spotify_track_data.get("track_number"),
                disc_number=spotify_track_data.get("disc_number"),
                year=release_year,
                isrc=isrc,
                provider_id=track_id,
                source="EchoSync.spotify",
                popularity=spotify_track_data.get("popularity"),
                preview_url=spotify_track_data.get("preview_url"),
            )
        except Exception as e:
            logger.error(f"Error converting Spotify track: {e}")
            return None

    # ==========================================
    # PluginBase Implementations
    # ==========================================

    def search(
        self, query: str, type: str = "track", limit: int = 10
    ) -> list[EchosyncTrack]:
        if not self.is_authenticated():
            return []

        try:
            results = self.sp.search(q=query, type=type, limit=limit)
            tracks = []

            if type == "track" and "tracks" in results:
                for item in results["tracks"]["items"]:
                    track = self._convert_track(item)
                    if track:
                        tracks.append(track)

            return tracks
        except Exception as e:
            logger.error(f"Error searching Spotify: {e}")
            return []

    def search_by_isrc(self, isrc: str) -> EchosyncTrack | None:
        """Implement PluginBase.search_by_isrc via Spotify's ISRC filter query.

        Uses the ``isrc:<code>`` qualifier supported by the Spotify search endpoint.
        Returns a single ``EchosyncTrack`` on an exact match, ``None`` otherwise.
        """
        if not isrc:
            return None

        if not self.ensure_authenticated():
            logger.debug(
                "search_by_isrc: Spotify not authenticated and client credentials unavailable, skipping."
            )
            return None

        canonical = str(isrc).strip().upper().replace("-", "")
        q = f"isrc:{canonical}"

        try:
            results = self.sp.search(q=q, type="track", limit=1)
            items = ((results or {}).get("tracks") or {}).get("items") or []
            if not items:
                return None
            track = self._convert_track(items[0])
            if track:
                if not isinstance(track.identifiers, dict):
                    track.identifiers = {}
                track.identifiers["source"] = "EchoSync.spotify"
                track.isrc = canonical
            return track
        except Exception as exc:
            logger.warning("Spotify search_by_isrc(%s) failed: %s", canonical, exc)
            return None

    @plugin_cache(ttl_seconds=2592000)
    def _raw_track(self, track_id: str) -> dict[str, Any] | None:
        """Cached raw Spotipy track payload.  Decoupled from get_track so the
        JSON-serialisable dict survives the plugin_cache SQLite round-trip."""
        if not self.is_authenticated():
            return None
        try:
            return self.sp.track(track_id)
        except Exception as e:
            logger.error(f"Error fetching raw track {track_id}: {e}")
            return None

    def get_track(self, track_id: str) -> EchosyncTrack | None:
        raw = self._raw_track(track_id)
        return self._convert_track(raw) if raw else None

    # Alias for Provider protocol compatibility if needed,
    # though PluginBase uses get_track
    def get_track_by_id(self, item_id: str) -> EchosyncTrack | None:
        return self.get_track(item_id)

    @plugin_cache(ttl_seconds=2592000)
    def get_album(self, album_id: str) -> dict[str, Any] | None:
        if not self.is_authenticated():
            return None
        try:
            return self.sp.album(album_id)
        except Exception as e:
            logger.error(f"Error getting album {album_id}: {e}")
            return None

    @plugin_cache(ttl_seconds=2592000)
    def get_artist(self, artist_id: str) -> dict[str, Any] | None:
        if not self.is_authenticated():
            return None
        try:
            return self.sp.artist(artist_id)
        except Exception as e:
            logger.error(f"Error getting artist {artist_id}: {e}")
            return None

    def get_artist_details(self, artist_id: str) -> dict[str, Any]:
        """Protocol requirement alias."""
        res = self.get_artist(artist_id)
        return res if res else {}

    # ==========================================
    # SyncServiceProvider Implementations
    # ==========================================

    def get_user_playlists(
        self, user_id: str | None = None
    ) -> Iterator[dict[str, Any]]:
        """
        Yield user playlists page by page to conserve memory, including Liked Songs.
        """
        if not self.is_authenticated():
            return

        if not self._ensure_user_id():
            return

        try:
            # Yield "Liked Songs" collection as the first pseudo-playlist
            try:
                saved = self.sp.current_user_saved_tracks(limit=1)
                total_liked = saved.get("total", 0) if saved else 0
                yield {
                    "id": "liked-songs",
                    "name": "Liked Songs",
                    "description": "Your Spotify Liked Songs collection",
                    "track_count": total_liked,
                    "owner": self.user_id or "Spotify",
                    "public": False,
                    "collaborative": False,
                    "snapshot_id": None,
                }
            except Exception as le:
                logger.debug(f"Could not fetch liked songs count: {le}")

            # Use generator to yield playlists
            results = self.sp.current_user_playlists(limit=50)
            while results:
                for item in results["items"]:
                    yield {
                        "id": item["id"],
                        "name": item["name"],
                        "description": item.get("description"),
                        "track_count": item["tracks"]["total"],
                        "owner": item["owner"]["display_name"],
                        "public": item.get("public"),
                        "collaborative": item.get("collaborative"),
                        "snapshot_id": item.get("snapshot_id"),
                    }
                # Check for next page
                if results["next"]:
                    results = self.sp.next(results)
                else:
                    break
        except Exception as e:
            logger.error(f"Error getting user playlists: {e}")
            return

    def get_playlist_tracks(
        self, playlist_id: str, force_refresh: bool = False
    ) -> list[EchosyncTrack]:
        """Return the tracks for *playlist_id*.

        When *force_refresh* is False (default, used by the background job), the
        method returns cached tracks immediately if the playlist is already cached,
        avoiding an API call entirely.  The background throttle job is responsible
        for deciding when to refresh stale playlists.

        When *force_refresh* is True (used by on-demand UI requests), the method
        always hits the Spotify API, re-caches the result, and returns fresh data.
        """
        if not self.is_authenticated():
            return []

        # Handle Liked Songs (Saved Tracks)
        if playlist_id in ("liked-songs", "saved-tracks", "collection:tracks"):
            if not force_refresh and self.cache_manager:
                cached = self.cache_manager.get_cached_tracks("liked-songs")
                if cached is not None:
                    logger.debug(
                        f"Serving Liked Songs from cache ({len(cached)} tracks)."
                    )
                    return cached

            tracks = []
            try:
                results = self.sp.current_user_saved_tracks(limit=50)
                while results:
                    for item in results.get("items", []):
                        if item.get("track") and item["track"].get("id"):
                            track = self._convert_track(item["track"])
                            if track:
                                tracks.append(track)
                    results = self.sp.next(results) if results.get("next") else None

                if tracks and self.cache_manager:
                    self.cache_manager.save_playlist(
                        {
                            "id": "liked-songs",
                            "name": "Liked Songs",
                            "description": "Your Spotify Liked Songs collection",
                            "tracks": {
                                "items": [{"track": t.to_dict()} for t in tracks],
                                "total": len(tracks),
                            },
                            "owner": {"display_name": self.user_id or "Spotify"},
                        }
                    )
                return tracks
            except Exception as e:
                logger.error(f"Error getting Spotify Liked Songs tracks: {e}")
                return []

        # Serve from cache unless the caller explicitly wants a fresh fetch.
        if not force_refresh and self.cache_manager:
            cached = self.cache_manager.get_cached_tracks(playlist_id)
            if cached is not None:
                logger.debug(
                    f"Serving playlist {playlist_id} from cache ({len(cached)} tracks)."
                )
                return cached

        tracks = []
        try:
            # First fetch the full playlist details to cache it
            playlist_details = self.sp.playlist(playlist_id)
            if playlist_details and self.cache_manager:
                self.cache_manager.save_playlist(playlist_details)

            results = self.sp.playlist_tracks(playlist_id, limit=100)
            while results:
                for item in results["items"]:
                    if item.get("track") and item["track"].get("id"):
                        track = self._convert_track(item["track"])
                        if track:
                            tracks.append(track)
                results = self.sp.next(results) if results["next"] else None
            return tracks
        except Exception as e:
            logger.error(f"Error getting playlist tracks: {e}")
            return []

    def sync_playlist(self, playlist_id: str, target_provider: str) -> bool:
        """
        Sync a Spotify playlist TO another provider.
        (Implementation depends on how we access the target provider instance)
        """
        logger.info(
            f"Sync requested for Spotify playlist {playlist_id} to {target_provider}"
        )
        # In a real implementation, we would:
        # 1. Fetch tracks from Spotify playlist
        # 2. Get target provider instance from Registry
        # 3. Search/Match tracks on target
        # 4. Create playlist on target
        # 5. Add tracks to target

        # For now, we stub this as False or basic logging, as the core sync engine
        # usually handles the orchestration. If the provider itself must do it:

        try:
            from core.nexus_framework.plugin_loader import (
                PluginRegistry,
            )

            target = PluginRegistry.create_instance(target_provider)
            if not target:
                logger.error(f"Target provider {target_provider} not found")
                return False

            # Logic would go here. For now, returning False to indicate not fully implemented
            # or relying on external sync engine.
            return False
        except Exception as e:
            logger.error(f"Error syncing playlist: {e}")
            return False

    # ==========================================
    # Write Capabilities (Spotify as Target)
    # ==========================================

    def create_playlist(
        self, name: str, description: str = "", public: bool = False
    ) -> str | None:
        """Create a new playlist on Spotify and return its ID."""
        if not self.is_authenticated() or not self._ensure_user_id():
            return None

        try:
            playlist = self.sp.user_playlist_create(
                user=self.user_id, name=name, public=public, description=description
            )
            return playlist["id"]
        except Exception as e:
            logger.error(f"Error creating playlist '{name}': {e}")
            return None

    def add_tracks_to_playlist(self, playlist_id: str, track_uris: list[str]) -> bool:
        """Add tracks to a Spotify playlist or Liked Songs."""
        if not self.is_authenticated():
            return False

        if playlist_id in ("liked-songs", "saved-tracks", "collection:tracks"):
            try:
                ids = [u.split(":")[-1] for u in track_uris if u]
                for i in range(0, len(ids), 50):
                    batch = ids[i : i + 50]
                    self.sp.current_user_saved_tracks_add(tracks=batch)
                return True
            except Exception as e:
                logger.error(f"Error adding tracks to Liked Songs: {e}")
                return False

        try:
            # Spotify allows max 100 tracks per request
            for i in range(0, len(track_uris), 100):
                batch = track_uris[i : i + 100]
                self.sp.playlist_add_items(playlist_id, batch)
            return True
        except Exception as e:
            logger.error(f"Error adding tracks to playlist {playlist_id}: {e}")
            return False

    def search_and_get_uri(self, track: EchosyncTrack) -> str | None:
        """
        Helper to find a Spotify URI for a EchosyncTrack.
        Useful when Spotify is the target.
        """
        query = f"track:{track.title} artist:{track.artist_name}"
        results = self.search(query, limit=1)
        if results:
            # We need the URI, but search returns EchosyncTrack.
            # We stored the ID in identifiers.
            found = results[0]
            # Retrieve ID from identifiers
            # identifiers structure: {'plugin_source': 'spotify', 'plugin_item_id': '...'}
            # or dict if normalized. EchosyncTrack normalizes to dict in post_init.

            # Safe retrieval
            if isinstance(found.identifiers, dict):
                tid = found.identifiers.get("spotify")
            elif isinstance(found.identifiers, list):
                # fallback search in list
                tid = next(
                    (
                        x["plugin_item_id"]
                        for x in found.identifiers
                        if x["plugin_source"] == "spotify"
                    ),
                    None,
                )
            else:
                tid = None

            if tid:
                return f"spotify:track:{tid}"
        return None
