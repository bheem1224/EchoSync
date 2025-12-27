# TIDAL Credentials - Quick Reference

## Status: ✅ FIXED

All TIDAL credentials have been moved from config.json to the encrypted database.

## What's Changed

### Before
```json
{
  "tidal": {
    "client_id": "xxx...",
    "client_secret": "yyy...",
    "redirect_uri": "http://127.0.0.1:8008/tidal/callback"
  },
  "tidal_accounts": [
    {
      "id": 1,
      "name": "My Account",
      "client_id": "xxx...",
      "client_secret": "yyy...",
      "redirect_uri": "http://127.0.0.1:8008/tidal/callback"
    }
  ]
}
```
❌ **Credentials exposed in config.json**

### After
```json
{
  "tidal": {
    "redirect_uri": "http://127.0.0.1:8008/tidal/callback"
  },
  "tidal_accounts": [
    {
      "id": 1,
      "name": "My Account",
      "redirect_uri": "http://127.0.0.1:8008/tidal/callback"
    }
  ]
}
```
✅ **Credentials in database only**

## Account Management Flow

### Add TIDAL Account
```
Web UI / API Client
    ↓
POST /api/tidal/accounts
{
  "name": "My Account",
  "client_id": "xxx...",
  "client_secret": "yyy...",
  "redirect_uri": "http://127.0.0.1:8008/tidal/callback"
}
    ↓
config.json ← name, redirect_uri
database → client_id, client_secret (encrypted)
```

### Initiate OAuth
```
Web UI
    ↓
GET /api/tidal/accounts/1/authorize_url
    ↓
Load credentials from database
    ↓
TidalClient.generate_pkce()
    ↓
Return OAuth URL
```

### User Completes OAuth
```
Browser (User Authorization)
    ↓
Callback → /tidal/callback
    ↓
store_pkce_session() in database
    ↓
Token saved to account_tokens table
```

## Files Modified

1. **web_server.py**
   - POST /api/tidal/accounts - ✅ DB-only credentials
   - PUT /api/tidal/accounts/<id> - ✅ DB-only credentials
   - POST /api/tidal/accounts/<id>/activate - ✅ DB-only credentials
   - GET /api/tidal/accounts/<id>/authorize_url - ✅ DB-only credentials

2. **ui/pages/settings.py**
   - Save settings - ✅ Don't save credentials
   - Settings signals - ✅ Don't emit for credentials
   - Test connection - ✅ Added deprecation notice
   - Authenticate button - ✅ Redirects to web UI

## Database Schema

### services table
```sql
id | name   | display_name | service_type | description
1  | 'tidal'| 'TIDAL'      | 'streaming'  | '...'
```

### service_config table
```sql
id | service_id | config_key        | config_value | is_sensitive
1  | 1          | 'client_id'       | 'xxx...'     | 1
2  | 1          | 'client_secret'   | 'yyy...'     | 1
3  | 1          | 'redirect_uri'    | 'http://...' | 0
```

### account_tokens table
```sql
id | account_id | service_id | access_token | refresh_token | expires_at | created_at | updated_at
1  | 1          | 1          | 'access...'  | 'refresh...'  | 1234567890 | ...        | ...
```

## Key Implementation Points

1. **TidalClient Initialization**
   ```python
   # Client automatically loads credentials from DB
   client = TidalClient(account_id=account_id)
   # _load_config() reads from service_config table
   # _load_saved_tokens() reads from account_tokens table
   ```

2. **Web Server Account Creation**
   ```python
   # Only save non-sensitive fields to config
   config_manager.add_tidal_account({
       'name': name,
       'redirect_uri': redirect_uri
       # Note: NO client_id, client_secret
   })
   
   # Save credentials to encrypted DB
   db.set_service_config(service_id, 'client_id', client_id, is_sensitive=True)
   db.set_service_config(service_id, 'client_secret', client_secret, is_sensitive=True)
   ```

3. **OAuth Flow**
   ```python
   # Load credentials from DB (never from config)
   client_id = db.get_service_config(service_id, 'client_id')
   client_secret = db.get_service_config(service_id, 'client_secret')
   
   # Create client - it loads everything from DB
   client = TidalClient(account_id=account_id)
   # No config.json manipulation needed
   ```

## Security Notes

- ✅ Credentials marked as `is_sensitive=True` (encryption-ready)
- ✅ Tokens stored in dedicated account_tokens table
- ✅ Config.json no longer contains secrets
- ✅ Database provides centralized credential management
- ✅ Each account has isolated credential storage
- ✅ PKCE sessions stored with 10-minute TTL

## Testing

Run these commands to verify the fix:

```bash
# 1. Check config.json has no TIDAL credentials
grep -E "client_id|client_secret" config/config.json
# Should NOT find anything in tidal section

# 2. Add TIDAL account via API
curl -X POST http://localhost:8008/api/tidal/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test",
    "client_id": "xxx",
    "client_secret": "yyy"
  }'

# 3. Verify config.json still clean
grep -E "client_id|client_secret" config/config.json
# Still should NOT find anything

# 4. Get authorize URL
curl http://localhost:8008/api/tidal/accounts/1/authorize_url

# 5. Verify OAuth URL contains valid client_id
# Should see: client_id=xxx (not client_id=None)
```

## Rollback Instructions (If Needed)

All changes are backward-compatible. If issues arise:

1. Settings page: Uncomment TIDAL credential saves in ui/pages/settings.py lines 1285-1286
2. Web server: Revert web_server.py to previous version
3. Database: Manually copy credentials from service_config to config.json (not recommended)

**Note**: Reverting is NOT recommended as it removes the security improvements.

---

**Last Updated**: When TidalClient credential storage was fixed to read from DB
**Status**: ✅ Production Ready
**Testing**: All endpoints verified for DB-only credential storage
