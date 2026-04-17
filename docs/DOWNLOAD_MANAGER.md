# 📥 The Download Manager

The Download Manager (`services/download_manager.py`) is the central orchestrator responsible for acquiring missing tracks from external sources.

## Event-Driven Architecture

The Download Manager is decoupled from the frontend and core Sync components. It listens to the global Event Bus for the `DOWNLOAD_INTENT` payload (typically published by the `SyncService` or Suggestion engine) and asynchronously queues the `EchosyncTrack` metadata for acquisition.

## The Provider-Agnostic Waterfall Strategy

EchoSync uses a sequential "waterfall" approach to acquisition that is completely provider-agnostic. It does not hardcode integrations to slskd; instead, it dynamically queries the `ProviderRegistry` for active Downloader clients.

1.  **Registry Discovery:** Queries the `ProviderRegistry` for any enabled plugins that declare the `supports_downloads` capability.
2.  **Search Formulation:** Generates atomic search strategies (e.g., Artist+Title, Album+Title).
3.  **Waterfall Querying:** It iterates through the active providers based on user-defined priority. For each provider, the generated queries are executed.
4.  **Provider Capabilities Check (Query vs. Filter):** The system adapts to the provider. If the plugin defines `supports_pre_filtering = True`, the system delegates basic filtering to the plugin. If not, the Download Manager pulls the raw candidate lists and performs the text/duration gating itself.
5.  **Deep Analysis:** Surviving candidates across all strategies are passed to the `WeightedMatchingEngine` for rigorous text and duration scoring.
6.  **Quality Selection:** The highest-scoring candidates across all queried providers are evaluated against the Global Quality Profile.
7.  **Execution:** The download command is issued to the winning provider.

## Global Quality Profiles

Quality profiles are standardized JSON schemas that apply across all Downloader plugins. They define:
*   **Format Allowlist:** (e.g., strictly `flac` or fallback to `mp3`).
*   **File Size Bounds:** Minimum and maximum allowed bytes.
*   **Bitrate & Bit Depth:** Minimum allowed Kbps or bits per sample (e.g., 16-bit vs 24-bit).
*   **Duration Tolerance:** Allowed variance in milliseconds from the target streaming duration.

## Soft Cancellations
If a track is acquired through other means (e.g., manually placed in the library) while a download is queued, the system intercepts the `TRACK_IMPORTED` event and issues a 'Soft Cancel' to the active download. The database row is updated to `cancelled` rather than physically deleted, preserving the audit trail.

---

## 🪝 Plugin Hooks (v2.5.0)

For each standard query strategy formulated by the system, there is a skip hook.

*   `skip_query_strategy_artist_title`: Completely bypass the internal query formatting for the Artist+Title strategy.
*   `skip_query_strategy_album_title`: Completely bypass the internal query formatting for the Album+Title strategy.
*   `skip_query_strategy_strict_duration`: Completely bypass the internal query formatting for the strict duration constraint strategy.

**Custom Query Injection:**
Plugins (like our internal CJK Language Pack plugin) can use pre/post hooks to inject entirely new query strategies (e.g., translating Kanji to Pinyin and adding it to the waterfall array) before the queries are dispatched to the providers.
