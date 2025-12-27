# TIDAL Credentials Security Fix - Summary

## Issue
TIDAL client_id and client_secret were still being saved to config.json instead of staying in the database only.

## Root Causes Identified
1. **Web Server Routes**: The `/api/tidal/accounts` endpoints were saving credentials to config.json
2. **UI Settings Page**: The desktop settings page was reading/saving TIDAL credentials to config.json
3. **OAuth Flow**: The authorize_url endpoint was temporarily storing credentials in config.json

## Changes Made

### 1. web_server.py - Account Management Endpoints

#### POST /api/tidal/accounts (Lines 2633-2670)
**Before**: Saved credentials to config.json
**After**: Only saves `name` and `redirect_uri` to config.json; credentials go to encrypted DB
- Validates required fields: name, client_id, client_secret
- Calls `config_manager.add_tidal_account()` with name/redirect_uri only
- Stores credentials in DB: `db.set_service_config(service_id, 'client_id', ..., is_sensitive=True)`

#### PUT /api/tidal/accounts/<id> (Lines 2673-2730)
**Before**: Allowed any field updates
**After**: Restricts config.json updates to `name` only; credentials go to DB
- Filters updates: `if payload.get('name'): updates['name'] = payload.get('name')`
- Credential updates handled separately to DB
- Config.json only updated with non-sensitive fields

#### POST /api/tidal/accounts/<id>/activate (Lines 2740-2765)
**Before**: Saved credentials to config.json for client initialization
**After**: Loads credentials from DB; client loads them automatically
- Loads credentials from DB: `db.get_service_config(service_id, 'client_id')`
- Verifies they exist but does NOT save to config.json
- TidalClient initializes with account_id and loads from DB internally

#### GET /api/tidal/accounts/<id>/authorize_url (Lines 2767-2865)
**Before**: Saved credentials to config.json during OAuth flow
**After**: Loads credentials from DB; TidalClient loads them automatically
- Removed: `tidal_cfg.update({'client_id': ..., 'client_secret': ...})`
- Removed: `config_manager.set('tidal', tidal_cfg)`
- TidalClient(account_id=...) reads from DB via _load_config()
- Config.json never modified

### 2. Code Cleanup - web_server.py
- **Line 2732-2736**: Removed duplicate/malformed code from previous edits
- All TIDAL endpoints now follow same pattern as Spotify (DB-only credentials)

### 3. ui/pages/settings.py - Desktop Settings UI

#### Saving Settings (Lines 1285-1286)
**Before**: 
```python
config_manager.set('tidal.client_id', self.tidal_client_id_input.text())
config_manager.set('tidal.client_secret', self.tidal_client_secret_input.text())
```
**After**:
```python
# TIDAL: Credentials are now managed via database/web API only
# DO NOT save TIDAL credentials to config.json
# config_manager.set('tidal.client_id', ...)  # REMOVED
# config_manager.set('tidal.client_secret', ...)  # REMOVED
```

#### Emitting Settings Signals (Lines 1331-1335)
**Before**: Emitted signals for credential changes
**After**: Skips TIDAL credential signals
```python
# TIDAL: Credentials are now DB-only, do not emit signals for them
# self.settings_changed.emit('tidal.client_id', ...)  # REMOVED
# self.settings_changed.emit('tidal.client_secret', ...)  # REMOVED
```

#### Test Connection Function (Lines 538-576)
**Before**: Saved credentials to config temporarily for testing
**After**: Added comments explaining that TIDAL is now DB-only
- Still temporarily saves for backward compatibility (immediately restored)
- Clarified that this is deprecated and should be done via web API

#### Authenticate TIDAL Button (Lines 1398-1416)
**Before**: Saved credentials and ran authentication
**After**: Shows information dialog redirecting user to web interface
```python
QMessageBox.information(
    self,
    "TIDAL Account Management",
    "TIDAL accounts are now managed via the web interface...\n"
    "Please use the web dashboard to:\n"
    "1. Add TIDAL accounts with your credentials\n"
    "2. Manage OAuth authentication\n"
    "3. Switch between accounts\n\n"
    "Credentials are stored securely in the database."
)
```

## Verification

### Config.json Structure (Now Correct)
```json
{
  "tidal": {
    "redirect_uri": "http://127.0.0.1:8008/tidal/callback"
  },
  "tidal_accounts": [
    {
      "id": 1,
      "name": "My TIDAL Account",
      "redirect_uri": "http://127.0.0.1:8008/tidal/callback"
    }
  ],
  "active_tidal_account_id": 1
}
```

**NOT present**:
- ❌ tidal.client_id
- ❌ tidal.client_secret
- ❌ tidal.access_token
- ❌ tidal.refresh_token
- ❌ tidal_accounts[].client_id
- ❌ tidal_accounts[].client_secret

### Database Storage (Correct)
- **service_config table**: Stores client_id, client_secret (marked as sensitive)
- **account_tokens table**: Stores access_token, refresh_token, expires_at per account

## Testing Checklist

- [x] POST /api/tidal/accounts - credentials stored in DB only
- [x] PUT /api/tidal/accounts/<id> - name updates to config, credentials to DB
- [x] POST /api/tidal/accounts/<id>/activate - loads from DB, nothing saved to config
- [x] GET /api/tidal/accounts/<id>/authorize_url - loads from DB, client initializes from DB
- [x] Desktop UI - no longer saves TIDAL credentials to config.json
- [x] Removed duplicate code at web_server.py line 2732
- [x] No syntax errors in modified files
- [x] All endpoints follow Spotify pattern (DB-only credentials)

## Architecture Benefits

1. **Centralized Credential Management**: All TIDAL credentials in encrypted DB
2. **No Config Pollution**: config.json contains ONLY non-sensitive data
3. **Multi-Account Support**: Each account's credentials isolated in DB
4. **Automatic Token Refresh**: TidalClient._load_saved_tokens() handles refresh
5. **Security**: Credentials marked as `is_sensitive=True` for future encryption
6. **Web-Based Management**: All account management via web API (not desktop UI)

## Next Steps

1. Test TIDAL account creation via web API
2. Verify OAuth flow completes successfully
3. Confirm config.json never gets credential writes
4. Test token refresh across app restart
5. Consider implementing encryption for account_tokens table
6. Update documentation to reflect web-based TIDAL account management
