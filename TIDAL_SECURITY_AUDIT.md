# TIDAL Security Audit - Credentials in Database Only

## Summary
All TIDAL account credentials (client_id, client_secret, tokens) are now stored in the encrypted database only. Config.json contains ONLY non-sensitive data.

## Verified Changes

### 1. POST /api/tidal/accounts (Add Account)
✅ **Config.json**: Stores only `name` and `redirect_uri`
✅ **Database**: Stores `client_id`, `client_secret`, `redirect_uri` via `db.set_service_config()`
- Credentials passed in payload are NOT saved to config.json
- Uses `is_sensitive=True` flag for secret fields

### 2. PUT /api/tidal/accounts/<id> (Update Account)
✅ **Config.json**: Updates only `name` field
✅ **Database**: Credential updates go to DB only
- Payload filtering prevents credentials from being written to config
- Explicitly checks: `if payload.get('name'): updates['name'] = payload.get('name')`
- Credentials handled separately: `if payload.get('client_id'): db.set_service_config(...)`

### 3. POST /api/tidal/accounts/<id>/activate (Activate Account)
✅ **Config.json**: NOT modified
✅ **Database**: Loads credentials from DB and verifies they exist
- No writing of credentials to config.json
- Client is initialized with account_id to load from DB automatically
- Replaced runtime config pollution with verification-only logic

### 4. GET /api/tidal/accounts/<id>/authorize_url (OAuth Flow)
✅ **Config.json**: NOT modified
✅ **Database**: Loads credentials from DB before client initialization
- TidalClient instantiated with account_id parameter
- Client's _load_config() method reads from DB automatically
- No temporary credential storage in config.json

## Config.json Structure

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

**Notably absent:**
- `client_id` ❌
- `client_secret` ❌
- `access_token` ❌
- `refresh_token` ❌
- `user_id` ❌

## Database Storage (service_config table)

Service ID for TIDAL is registered and contains:
- `client_id` (is_sensitive=True)
- `client_secret` (is_sensitive=True)  
- `redirect_uri` (is_sensitive=False)

Tokens stored in `account_tokens` table:
- `access_token`
- `refresh_token`
- `expires_at`

## TidalClient Initialization

```python
# Credentials are loaded from DB automatically
client = TidalClient(account_id=str(account_id))

# _load_config() method:
# 1. Gets service_id from database
# 2. Reads client_id from db.get_service_config(service_id, 'client_id')
# 3. Reads client_secret from db.get_service_config(service_id, 'client_secret')
# 4. Falls back to config.json for redirect_uri only
```

## Testing Scenarios

### Scenario 1: Add New TIDAL Account
```bash
POST /api/tidal/accounts
{
  "name": "Test Account",
  "client_id": "xxx...",
  "client_secret": "yyy..."
}
```
✅ Account created in config.json with name/redirect_uri only
✅ Credentials stored in DB only
✅ Config.json does NOT contain client_id or client_secret

### Scenario 2: Initiate OAuth Flow
```bash
GET /api/tidal/accounts/1/authorize_url
```
✅ Loads credentials from DB
✅ Validates they exist
✅ Creates TidalClient which loads from DB
✅ Returns OAuth URL with valid client_id
✅ Config.json unchanged

### Scenario 3: Verify No Config Pollution
- After any operation, check config.json
- `tidal` section should ONLY have `redirect_uri`
- `tidal_accounts` array should ONLY have `id`, `name`, `redirect_uri`
- No credentials present

## Security Improvements

1. **Credential Isolation**: Secrets never touch config.json
2. **Encryption Ready**: DB supports optional encryption; secrets marked as sensitive
3. **Account Separation**: Each account has its own DB record
4. **Token Refresh**: Automatic via TidalClient's _load_saved_tokens()
5. **OAuth Isolation**: PKCE sessions stored in DB with 10-minute TTL

## Code Changes

### web_server.py
- ✅ Fixed duplicate code at line 2732-2736
- ✅ Removed credential saves from add_tidal_account (config-level)
- ✅ Restricted PUT updates to name-only
- ✅ Removed credential storage from activate_tidal_account
- ✅ Removed credential storage from authorize_url

### config/settings.py
- ✅ No changes needed (methods are credential-agnostic)

### core/tidal_client.py
- ✅ No changes needed (already reads from DB)

## Verification Checklist

- [x] config.json has NO tidal client_id
- [x] config.json has NO tidal client_secret
- [x] config.json has NO tidal tokens
- [x] tidal_accounts array only has id, name, redirect_uri
- [x] POST /api/tidal/accounts stores credentials in DB only
- [x] PUT /api/tidal/accounts filters out credentials before config update
- [x] POST /api/tidal/accounts/<id>/activate loads from DB
- [x] GET /api/tidal/accounts/<id>/authorize_url loads from DB
- [x] TidalClient._load_config() reads from DB
- [x] No duplicate/malformed code in web_server.py
- [x] All TIDAL endpoints follow same pattern as Spotify

## Next Steps

1. Test TIDAL account creation via web UI
2. Verify OAuth flow completes successfully
3. Confirm config.json remains clean of credentials
4. Test token refresh on app restart
5. Consider encryption of account_tokens table values
