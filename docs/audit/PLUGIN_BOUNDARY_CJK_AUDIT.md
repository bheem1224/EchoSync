# EchoSync Nexus Plugin Framework & Boundary Audit
**Focus:** Architectural Boundaries, Permission Enforcement, SDK Capabilities, and CJK Language Pack Integration  
**Date:** 2026-09-12  
**Status:** Ground Truth Audit Complete

---

## Executive Summary

This document presents the definitive architectural audit of EchoSync's Nexus plugin framework, permission enforcement layer, and SDK capabilities. It specifically addresses how plugins—exemplified by `plugins/EchoSync/cjk_language_pack`—interact with core databases (`music.db`, `working.db`), external networks via `RequestManager`, and the user-consent lifecycle during privilege escalation.

All findings are grounded strictly in codebase inspection; zero identifiers or mechanisms are speculated.

---

## 1. Plugin Permissions & Manifest Declarations

### 1.1 Capability vs Security Permissions
EchoSync distinguishes between **functional capabilities** (what pipeline hook/role a plugin fulfills) and **security permissions** (what system resources a plugin is permitted to access).

#### Functional Capabilities (`core/enums.py:L4-L19`)
Plugins declare functional capabilities in their `manifest.json` under `"capabilities"` or within Python via `Capability(Enum)`:
```python
class Capability(Enum):
    RESOLVE_FINGERPRINT = "resolve_fingerprint"
    FETCH_METADATA      = "fetch_metadata"
    TAG_FILES           = "tag_files"
    STREAM_AUDIO        = "stream_audio"
    SYNC_LIBRARY        = "sync_library"
    FETCH_BY_ISRC       = "fetch_by_isrc"
    CLIENT_PREFILTER    = "client_prefilter"
```

#### Security Permissions (`manifest.json` & `core/nexus_framework/`)
Enforced by the plugin loader and AST security scanner (`core/nexus_framework/plugin_loader.py`):

| Permission Key | Type | Ground Truth Source | Enforcement Mechanism |
| :--- | :--- | :--- | :--- |
| `privileged` / `permissions.privileged_mode` | `bool` | `core/nexus_framework/plugin_store.py:L1207-L1217`<br>`plugin_loader.py:L1044` | When `False` (default), `PluginSecurityScanner` (`plugin_loader.py:L337-L340`) rejects AST nodes importing `database`, `subprocess`, `ctypes`, or accessing restricted OS APIs. When `True`, elevated imports are permitted. |
| `network_domains` | `list[str]` | `core/nexus_framework/plugin_SDK.py:L510-L528` | Enforced at runtime by `_NetworkSDKFacade._check_allowlist(url)`. Non-matching hostnames throw `PermissionError`. |
| `wasm_fs_access` | `list[str]` | `core/nexus_framework/plugin_store.py:L908-L914` | Directory path mounts for WebAssembly/isolated sandbox execution environments. |
| `verified_source` | `str` | `core/nexus_framework/plugin_loader.py:L1040-L1043` | Set to `"official"` or when author is `"EchoSync"`; exempts the package from static AST heuristic rejection during local ingestion. |

### 1.2 Granularity of Database Permissions
- **No row-level or table-level permission flags exist** in the manifest or the plugin loader.
- Security enforcement for databases occurs through **physical path attachment** and **SQLite connection modes**, not declarative access control lists (ACLs).

---

## 2. Database Write Boundaries & SQLite Gateway

### 2.1 The Read-Only Invariant for `music.db`
The plugin database gateway is implemented in `core/nexus_framework/plugin_SDK.py:L768-L776` within `get_database_connection(write_access=False)`:

```python
# core/nexus_framework/plugin_SDK.py:L768-L776
if write_access:
    # working.db is attached as read-write, but music.db is ALWAYS read-only
    conn.execute("ATTACH DATABASE 'file:/data/music.db?mode=ro' AS music_lib")
    conn.execute("ATTACH DATABASE 'file:/data/working.db?mode=rw' AS working")
else:
    conn.execute("ATTACH DATABASE 'file:/data/music.db?mode=ro' AS music_lib")
    conn.execute("ATTACH DATABASE 'file:/data/working.db?mode=ro' AS working")
```

**Architectural Law:**
Direct raw SQL writes (`INSERT`, `UPDATE`, `DELETE`) to `/data/music.db` from plugins are **physically prevented** by SQLite runtime connection flags (`mode=ro`). Any plugin attempting to write directly to `music.db` or `artist_aliases` via a raw connection will trigger:
`sqlite3.OperationalError: attempt to write a readonly database`.

### 2.2 Available SDK Database Interfaces
`_SDK` (`core/nexus_framework/plugin_SDK.py:L633-L644`) provides two database handles:
1. `sdk.db.get_plugin_session()`:
   Delegates to `working_db.get_provider_storage(self.plugin_id).session_scope()`. This provides an isolated SQLAlchemy session inside `working.db` scoped to `plugin_storage_<plugin_id>`. It has **no access** to core library tables (`tracks`, `artists`, `artist_aliases`).
2. `sdk.models` (`_PluginModelFacade`, `core/nexus_framework/plugin_SDK.py:L979-L1025`):
   Exposes core ORM classes (`Track`, `Album`, `Artist`, `Genre`, `LocalMedia`).
   *Crucial Detail:* Neither `ArtistAlias` nor `TrackAlias` is exported by `_PluginModelFacade`.
3. **No Direct Write Helper:** There are no convenience methods like `sdk.save_artist_alias()` or `sdk.execute_write()` on `_SDK`.

### 2.3 The Valid Pathways for Storing Entity Aliases
To persist aliases (e.g. Romanized/Kanji artist aliases) without violating database isolation, two valid architectural pathways exist:

#### Pathway A: Canonical Decoupled Proposal (`resolve_entity_aliases` hook)
1. Plugin registers the hook: `resolve_entity_aliases(context: AliasResolutionContext) -> list[EntityAliasProposal]`
2. Schema reference (`core/metadata/schemas.py:L13-L26`):
   ```python
   @dataclass(slots=True)
   class EntityAliasProposal:
       entity_type: str        # "artist" | "album" | "track"
       entity_id: str          # UUID or MusicBrainz GID
       alias_name: str         # Transliterated / localized string
       alias_type: str         # "romaji", "kanji", "kana", "pinyin", "hangul"
       language_code: str      # "ja", "zh", "ko"
       script: str             # "Latn", "Jpan", "Hani"
       source: str             # "cjk_language_pack"
       confidence: float       # 0.0 - 1.0
   ```
3. Core persistence layer (`core/database/repositories/track_repo.py:L1101-L1215`):
   `TrackRepository.upsert_entity_aliases(session, proposals)` executes inside the core transaction, writing directly to `music.db` with validation and deduplication.

#### Pathway B: In-Pipeline ORM Session Attachment (`post_metadata_enrichment` hook)
During automated ingestion, `plugins/EchoSync/cjk_language_pack/__init__.py:L523-L570` receives the live `track_obj` ORM instance:
```python
from sqlalchemy.orm import object_session
session = object_session(track_obj)
if session:
    # Attach alias to track_obj.artist.aliases collection
```

#### Defect in Existing `plugins/EchoSync/cjk_language_pack/plugin.py:L320-L385`:
`plugin.py` attempts:
```python
engine = sdk.get_database_connection(write_access=True)
# INSERT INTO artist_aliases ...
```
This fails immediately because `artist_aliases` resides in `music_lib` (`music.db`), which is attached strictly with `mode=ro`.

---

## 3. Outbound Network Access & RequestManager Gateway

### 3.1 Network SDK Architecture
Plugins do not instantiate `httpx` or `requests` directly (blocked by `PluginSecurityScanner`). Instead, plugins interact with external APIs via `self.http` (on `PluginBase`) or `sdk.network` (`_NetworkSDKFacade`, `core/nexus_framework/plugin_SDK.py:L485-L550`).

### 3.2 Domain Allowlist Enforcement
Every call to `sdk.network.get()`, `.post()`, `.put()`, or `.delete()` executes `_check_allowlist(url)`:
```python
# core/nexus_framework/plugin_SDK.py:L510-L528
def _check_allowlist(self, url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.split(":")[0].lower()
    allowed = [d.lower() for d in self.manifest.get("network_domains", [])]
    
    for pattern in allowed:
        if pattern.startswith("*."):
            base = pattern[2:]
            if domain == base or domain.endswith("." + base):
                return
        elif domain == pattern:
            return
            
    raise PermissionError(
        f"Network access to '{domain}' blocked. Domain not in 'network_domains' allowlist."
    )
```

### 3.3 Core RequestManager Delegation & Rate Limiting
Once the allowlist check passes, `_NetworkSDKFacade` delegates to the singleton `RequestManager` (`core/request_manager.py:L58`):
- **Provider-Scoped Limits:** Initialized as `RequestManager(provider=self.plugin_id)`.
- **Default Policy (`RateLimitConfig`, `core/request_manager.py:L42`):**
  - Standard rate limit: `1.0 req/s`
  - Max retries: `3`
  - Exponential backoff: `0.5s` minimum to `8.0s` maximum with jitter.
- **MusicBrainz Integration Requirement:**
  For the CJK pack to query MusicBrainz, its `manifest.json` must explicitly declare:
  ```json
  "network_domains": [
      "musicbrainz.org",
      "*.musicbrainz.org"
  ]
  ```

---

## 4. Dynamic User Consent & Permission Elevation

### 4.1 Privilege Escalation Detection
The upgrade lifecycle is handled by `core/nexus_framework/plugin_store.py:L860-L925` in `update_plugin(plugin_id, package_path, force_consent=False)`.

The engine loads existing permissions from `config.db` (`services` table) and compares them with the new archive's `manifest.json`:
1. **Privileged Mode Check (`plugin_store.py:L880-L895`):**
   ```python
   if new_privileged and not old_privileged:
       escalations.append({
           "type": "privileged_mode",
           "reason": "Plugin requests privileged system access (unrestricted imports & subprocess)"
       })
   ```
2. **Network Domain Expansion (`plugin_store.py:L896-L907`):**
   ```python
   new_domains = set(new_manifest.get("network_domains", [])) - set(old_manifest.get("network_domains", []))
   if new_domains:
       escalations.append({
           "type": "network_domains",
           "added": list(new_domains),
           "reason": f"Plugin requests access to new external domains: {', '.join(new_domains)}"
       })
   ```
3. **Escalation Rejection:**
   If `escalations` is non-empty and `force_consent is False`, `update_plugin` raises `PrivilegeEscalationError(escalations)`.

### 4.2 Web Route Exception Mapping (`web/routes/plugins.py`)
In `web/routes/plugins.py:L265-L275` (`/system/plugins/install`) and `L332-L342` (`/system/plugins/update`):
```python
except PrivilegeEscalationError as e:
    return JSONResponse(
        status_code=403,
        content={
            "status": "error",
            "code": "PRIVILEGE_ESCALATION_REQUIRED",
            "requires_consent": True,
            "escalations": e.escalations,
            "message": "This update requires elevated permissions."
        }
    )
```

### 4.3 Frontend User Consent Modal (`webui/`)
1. **Trigger (`webui/src/routes/settings/plugin-store/+page.svelte:L138-L155`):**
   When an update or install call receives an HTTP 403 with `requires_consent: true`, it sets `consentModalPayload = response.data` and displays `PluginConsentModal.svelte`.
2. **Component (`webui/src/lib/components/modals/PluginConsentModal.svelte:L1-L80`):**
   - Renders a warning header explaining that the update requests elevated privileges.
   - Dynamically renders cards:
     - **Privileged Mode Warning:** Explains file-system and system-level capabilities.
     - **Network Domains List:** Displays badge tags for each newly requested external host.
     - **Filesystem Mounts:** Displays newly requested WASM storage paths.
3. **User Confirmation (`Accept Risk & Update`):**
   Re-submits the request with query parameter `?force_consent=true`:
   `POST /system/plugins/update?plugin_id=...&force_consent=true`.
   The backend records the updated permissions in `config.db` and finishes unpacking.

---

## 5. Summary Matrix & Audit Conclusions

| Question | Architectural Reality | Action Required for CJK Language Pack |
| :--- | :--- | :--- |
| **Exact Permissions Required** | `"capabilities": ["fetch_metadata"]`<br>`"network_domains": ["musicbrainz.org", "*.musicbrainz.org"]` | Update `manifest.json` with explicit domains; remove attempts to declare non-existent granular DB permissions. |
| **Direct Write to `music.db`** | **Impossible by design.** `get_database_connection` hardcodes `mode=ro` on `music.db`. | Refactor CJK alias persistence to return `EntityAliasProposal` via `resolve_entity_aliases` hook. |
| **Outbound Requests to MusicBrainz** | Allowed via `sdk.network.get()` / `self.http.get()` when domain is allowlisted. | Route all HTTP calls through SDK network facade to inherit RequestManager rate-limiting (1.0 req/s). |
| **Dynamic Consent Flow** | Fully implemented in backend (`plugin_store.py`), API (`plugins.py`), and UI (`PluginConsentModal.svelte`). | Upgrading CJK pack with newly declared `network_domains` will automatically trigger the existing consent dialog. |

---
*Audit completed by Antigravity Core Architectural Agent.*

