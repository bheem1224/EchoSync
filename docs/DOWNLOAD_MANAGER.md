# 📥 The Download Manager

The Download Manager (`services/download_manager.py`) is responsible for acquiring missing tracks from external sources.

## The Waterfall Strategy

EchoSync uses a sequential "waterfall" approach to acquisition:

1.  **Search Formulation:** The metadata is formatted into an atomic search query.
2.  **Provider Queries:** The system queries slskd. (It operates a strict concurrency limit of 3 to prevent Soulseek IP bans).
3.  **Pre-Filtering:** Candidates are immediately discarded if they fall wildly outside duration or basic text heuristics.
4.  **Deep Analysis:** Surviving candidates are passed to the Matching Engine for rigorous scoring.
5.  **Quality Selection:** The highest-scoring candidates are evaluated against the user's Quality Profile (e.g., FLAC preference).
6.  **Execution:** The download command is issued to the slskd API.

## Soft Cancellations
If a track is acquired through other means (e.g., manually placed in the library) while a download is queued, the system intercepts the `TRACK_IMPORTED` event and issues a 'Soft Cancel' to the download queue. The database row is updated to `cancelled` rather than deleted, preserving the audit trail.

---

## 🪝 Plugin Hooks (v2.5.0)

*   `pre_slskd_query`: Mutate the final search query string before it is sent to the slskd API.
*   `skip_slskd_download`: Bypass the slskd integration entirely. A plugin can register as a custom `DownloaderProvider` (e.g., Usenet, private trackers, yt-dlp) and handle the acquisition step independently.
