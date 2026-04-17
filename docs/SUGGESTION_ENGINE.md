# 🔮 The Suggestion Engine

The Suggestion Engine analyzes your listening habits and library state to generate dynamic discovery playlists.

## Core Principles

*   **Privacy First:** All analysis happens locally on your hardware. **We do not upload your listening history, ratings, or library data to the cloud.**
*   **Vibe Profiling:** The engine groups tracks by extracted acoustic features and user ratings.
*   **Consensus Algorithm:** It compares your highly-rated tracks against local historical listening data to build a consensus matrix of what you enjoy.

## Data Storage
User interactions (play counts, skips, ratings) are stored in the `user_track_states` and `user_ratings` tables within the `working.db` operational database.
*   Ratings are strictly normalized to a 0.0 to 10.0 scale.
*   "Ghost Tracks" (hard-deleted items) are flagged to ensure the discovery engine never suggests or downloads them again.

---

## 🪝 Plugin Hooks (v2.5.0)

*   `post_track_rated`: Trigger an action when a user rates a track (e.g., sync rating back to Plex/Jellyfin).
*   `skip_suggestion_matrix`: Bypass the internal consensus algorithm completely. A plugin can use this to inject suggestions from an offline Postgres dump of a third-party recommendation model or an external API like Last.fm.
