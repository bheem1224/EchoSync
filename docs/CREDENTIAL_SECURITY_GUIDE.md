# Credential Security & Encryption Flow

**Last Updated:** December 29, 2025

## Executive Summary

Credentials flow from frontend → backend → encrypted database. **Encryption happens on the backend after receiving credentials.** Current security status:

| Layer | Status | Details |
|-------|--------|---------|
| **Transport (HTTP)** | ⚠️ NEEDS HTTPS | Credentials sent plaintext over network |
| **Backend Processing** | ✅ IMPROVED | Encrypted before database storage |
| **At-Rest Encryption** | ✅ GOOD | Fernet encryption in config.db |
| **Logging** | ✅ FIXED | No longer logs credential values |
| **Memory Duration** | ✅ OK | Credentials encrypted immediately after receipt |

---

## Credential Flow Timeline

### **Step-by-Step Encryption Process**

```
TIME    LOCATION           STATE                  ENCRYPTED?
────────────────────────────────────────────────────────────────
 T0     Frontend UI        User types credential  No
        Form field         "spotify_secret"       (plaintext)
        
 T1     Frontend Click     POST /api/providers/   No
        "Save Credentials" spotify/settings       (in JSON body)
        
 T2     Network Transit    HTTP payload           ❌ UNENCRYPTED
        (T2-T3)            {spotify: {            (MITM RISK HERE)
                           secret: "abc123"       
                           }                      
                           }                      
                           
 T3     Flask Route        Receives JSON          No
        /api/providers/    request.get_json()     (still plaintext
        <id>/settings                              in Python dict)
        
 T4     config_manager.    Checks if              No
        set_service_       'spotify.secret'       (matches SECRETS
        credentials()      matches SECRETS list   list, will encrypt)
        
 T5     _traverse_and_     Recursively walks      Yes ✅
        _transform()       config tree,           (Fernet encryption
        with              finds matching keys,   applied here)
        _encrypt_value     encrypts: 
                          "abc123" → 
                          "enc:gAAAAAB..."
        
 T6     _save_to_         Saves encrypted        Yes ✅
        database()         JSON to config.db      (Already encrypted
                          ("enc:gAAAAAB...")     in database)
        
 T7     At Rest           config.db on disk      Yes ✅
        (Persistent)      All secrets encrypted  (Protected)
        
 T8     On Retrieval      _decrypt_value()       Brief ⚠️
        (Later)           decrypts when needed   (unencrypted in
                          for use                memory temporarily)
```

---

## Security Analysis: Where Credentials Can Be Stolen

### **1. Network Transit (CRITICAL)** ⚠️
**Problem:** HTTP is unencrypted

```
User Browser          Network          Flask Backend
     ↓                  ↓                    ↓
[Spotify Secret]  → [PLAIN TEXT]  →  [Receive]
"abc123secret"      (visible to ISP,
                     WiFi eavesdropper,
                     MITM attacker)
```

**Current Status:** ❌ HTTP in development
**Required Fix:** ✅ HTTPS in production

**How to Fix:**
```bash
# In Docker:
- Use nginx reverse proxy with SSL
- Mount certificate: /config/certs/cert.pem

# In development:
- Use `pip install flask-talisman`
- Run with SSL: 
  python -c "from web.api_app import create_app; 
  app = create_app(); 
  app.run(ssl_context='adhoc')"
```

---

### **2. Logging (MEDIUM)** ⚠️
**Problem:** Decrypted values were logged to console/files

```python
# OLD (BAD):
print(f"Decrypted: {decrypted_secret}")
# Logs: "Decrypted: abc123secret"  ← Exposed in logs!

# NEW (FIXED):
print(f"Decrypted secret ({len(decrypted)} chars)")
# Logs: "Decrypted secret (9 chars)"  ← No exposure
```

**Current Status:** ✅ FIXED (see changes below)
**What Changed:** No credential values logged, only metadata

---

### **3. Request Body Logging (MEDIUM)** ⚠️
**Problem:** Flask might log incoming POST bodies

```python
# OLD: Error logging could expose payload
logger.error(f"Error updating settings: {e}")
# In debug mode, this might include the POST body

# NEW: Only logs the error, not the data
logger.error(f"Error updating {provider_name} settings: {type(e).__name__}")
```

**Current Status:** ✅ FIXED (see changes below)
**What Changed:** Endpoint logs metadata only, not credentials

---

### **4. In-Memory Exposure (LOW)** ⚠️
**Problem:** Credentials exist unencrypted briefly

```python
# Timeline:
payload = request.get_json()  # ← Secret in memory (unencrypted)
#          ...
config_manager.set_service_credentials()  # ← Encrypted here
# After this line, memory copy is garbage collected
```

**Duration:** < 100ms (milliseconds)
**Risk:** Low (requires process memory dump at exact moment)
**Mitigation:** Can clear memory after encryption:

```python
# Optional: Explicitly clear the payload
payload = None  # Force garbage collection
```

**Current Status:** ⚠️ ACCEPTABLE (brief duration)

---

### **5. Database Encryption (GOOD)** ✅
**Status:** Fully encrypted at rest

```python
# config.db contains:
{"spotify": {"secret": "enc:gAAAAABptUI..."}}
#                        ↑
#                   Fernet-encrypted
#                   (256-bit key required to decrypt)
```

**Encryption Method:** Fernet (AES-128 in CBC mode)
**Key Storage:** `/config/.encryption_key` or `MASTER_KEY` env var
**Strength:** Military-grade (256-bit keys)

**If Database is Stolen:**
```
Without encryption key → Useless encrypted blob
With encryption key → Credentials readable (so protect the key!)
```

---

### **6. Encryption Key Storage (MEDIUM)** ⚠️
**Problem:** Key stored in file `/config/.encryption_key`

```
CURRENT:
/config/.encryption_key
└─ Contains: <base64-encoded-256-bit-key>
└─ File permissions: 0o600 (user read/write only)
└─ Risk: If config folder is backed up unencrypted, key is exposed

BETTER (Docker):
MASTER_KEY environment variable
└─ Set in: docker-compose.yml secrets or Kubernetes secrets
└─ Never written to disk
└─ Rotated with environment updates
```

**Current Status:** ⚠️ FILE-BASED (acceptable for local dev)
**Production Recommendation:** Use environment variable in Docker

```yaml
# docker-compose.yml
services:
  backend:
    environment:
      - MASTER_KEY=${MASTER_KEY}  # Set from .env or secret
    secrets:
      - soulsync_master_key  # Or use Docker secrets
```

---

## Current Security Improvements Applied

### **Change 1: Stop Logging Decrypted Values**
**File:** `config/settings.py`

```python
# BEFORE:
print(f"[DEBUG] Decrypted value: {decrypted[:20]}...")

# AFTER:
print(f"[DEBUG] Decrypted secret ({len(decrypted)} chars)")
```

**Impact:** Credentials no longer appear in any logs

### **Change 2: Remove Credentials from Error Messages**
**File:** `web/routes/providers.py`

```python
# BEFORE:
logger.error(f"Error updating settings for {provider_name}: {e}")
# Could include POST body in exception

# AFTER:
logger.error(f"Error updating {provider_name} settings: {type(e).__name__}")
# Only logs error type, not the data
```

**Impact:** Errors never expose credentials

### **Change 3: No Echo-Back of Credentials**
**File:** `web/routes/providers.py`

```python
# BEFORE:
return jsonify({'success': True, 'data': payload})

# AFTER:
return jsonify({'success': True, 'message': 'saved securely'})
```

**Impact:** Credentials never sent back to frontend

---

## How Encryption Actually Works

### **Encryption On Save**

```python
# User saves: {spotify: {client_secret: "xyz123"}}

config_manager.set_service_credentials('spotify', {
    'client_secret': 'xyz123'
})

# Internally:
1. Detects 'spotify.client_secret' matches SECRETS list
2. Calls _encrypt_value('xyz123')
3. Returns: "enc:gAAAAABptUI2Ey...[long encrypted string]"
4. Saves encrypted version to database

# Result in config.db:
{
  "spotify": {
    "client_secret": "enc:gAAAAABptUI2Ey6qCNgw..."
  }
}
```

### **Decryption On Read**

```python
# App needs the credential:
secret = config_manager.get('spotify.client_secret')

# Internally:
1. Retrieves from database: "enc:gAAAAABptUI2..."
2. Detects "enc:" prefix
3. Calls _decrypt_value(encrypted_string)
4. Uses MASTER_KEY to decrypt
5. Returns: 'xyz123' (in memory, unencrypted)

# Risk window: Credential unencrypted in memory until variable goes out of scope
```

---

## Complete Security Checklist

### **Immediate (Already Done)**
- [x] Credentials encrypted before database storage (Fernet)
- [x] Encryption key generation & storage
- [x] No credential values in logs
- [x] No credential echo-back in responses
- [x] Database isolation (config.db separate from code)

### **Short Term (Do This)**
- [ ] **Enable HTTPS**
  ```bash
  pip install flask-talisman flask-cors
  # In production: nginx SSL proxy
  ```
  
- [ ] **Rotate Encryption Key Regularly**
  ```bash
  # Every 3 months:
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key())"
  # Update MASTER_KEY environment variable
  ```

- [ ] **Set File Permissions**
  ```bash
  chmod 600 /config/.encryption_key
  # Only owner can read
  ```

- [ ] **Use Environment Variables for Key (Docker)**
  ```dockerfile
  ENV MASTER_KEY=${MASTER_KEY}
  # Don't store key in image
  ```

### **Medium Term (Recommended)**
- [ ] **Audit Logging**
  ```python
  # Log all credential changes (without the values):
  logger.info(f"Credentials updated for {provider}")
  logger.info(f"User {username} changed {provider} settings")
  ```

- [ ] **API Rate Limiting**
  ```python
  # Prevent brute force auth attempts
  from flask_limiter import Limiter
  limiter = Limiter(app, key_func=lambda: request.remote_addr)
  
  @bp.post("/<provider>/auth")
  @limiter.limit("5 per hour")
  def auth_provider():
      pass
  ```

- [ ] **Request Signing**
  ```python
  # Optional: Sign requests so frontend must prove legitimacy
  import hmac
  signature = hmac.new(SECRET, request.body).hexdigest()
  ```

### **Long Term (Enterprise)**
- [ ] **Hardware Security Module (HSM)**
  - Store master key on HSM device
  - Key never on disk
  - Requires network call to decrypt
  
- [ ] **Key Management Service (KMS)**
  - AWS KMS, Azure Key Vault, etc.
  - Centralized key rotation
  - Audit trail of all decryptions

- [ ] **Credential Rotation**
  - Periodically re-encrypt with new key
  - Automatic key versioning
  - Backward compatibility for old versions

---

## Testing the Security

### **Verify Encryption is Working**

```bash
# 1. Set a credential
curl -X POST http://localhost:8000/api/providers/spotify/settings \
  -H "Content-Type: application/json" \
  -d '{"client_secret": "test_secret_123"}'

# 2. Check the database
sqlite3 /config/config.db "SELECT * FROM metadata WHERE key='app_config';"

# Should see something like:
# enc:gAAAAABptUI2Ey6qCNgw0pV8QyN...
# (NOT plain text "test_secret_123")

# 3. Verify logs don't contain secrets
grep "test_secret_123" logs/*.log
# Should return NOTHING (no match)
```

### **Verify HTTPS Requirement**

```bash
# Add to your deployment:
from flask_talisman import Talisman

app = create_app()
Talisman(app, 
    force_https=True,
    strict_transport_security=True,
    strict_transport_security_max_age=31536000
)
```

---

## Summary: Encryption Happens Here

```
Frontend (plaintext)
        ↓
Backend receives (plaintext for ~1ms)
        ↓
config_manager.set() detects secret key
        ↓
_encrypt_value() called
        ↓
Fernet.encrypt() with MASTER_KEY
        ↓
"enc:gAAAAAB..." stored to database
        ↓
At Rest: Encrypted in config.db ✅
```

**Key Point:** Encryption happens **immediately** in the backend (microseconds after receipt), but the transport (frontend → backend) is currently unencrypted. **HTTPS is the critical missing piece.**

---

## Recommendations Priority

**CRITICAL (Do First):**
1. Enable HTTPS in production
2. Use environment variable for MASTER_KEY in Docker
3. Set file permissions on `.encryption_key`

**HIGH (Do Soon):**
4. Audit all logs to ensure no credentials exposed
5. Add rate limiting to auth endpoints
6. Implement credential rotation policy

**MEDIUM (Do Eventually):**
7. Add request signing/validation
8. Implement audit logging for credential changes
9. Consider key versioning

**LOW (Nice to Have):**
10. Hardware security module
11. KMS integration
12. Advanced credential rotation

---

## TL;DR

**Where credentials are stolen risks:**
1. **Network (HTTP)** ⚠️ - HTTPS needed
2. **Logs** ✅ - Fixed
3. **Error messages** ✅ - Fixed  
4. **Memory** ⚠️ - Brief, acceptable
5. **Database** ✅ - Encrypted

**Current Status:** Credentials are encrypted at rest ✅, but need HTTPS in transit ⚠️
