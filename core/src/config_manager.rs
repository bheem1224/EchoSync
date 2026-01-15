use aes_gcm::aead::AeadCore;
use pyo3::prelude::*;
use rusqlite::{params, Connection, OptionalExtension};
use std::fs;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use aes_gcm::{
    aead::{Aead, KeyInit, OsRng},
    Aes256Gcm, Nonce // Or Aes128Gcm
};
use sha2::{Sha256, Digest};
use base64::prelude::*;
use serde_json::Value;

#[pyclass]
pub struct ConfigManager {
    config_path: PathBuf,
    db_path: PathBuf,
    key: [u8; 32],
    // We keep a connection for secrets? Or open on demand?
    // SQLite is light, opening on demand is fine, but keeping it is better for performance if frequent.
    // However, for secrets, frequency is low.
    // Let's keep it simple and open on demand or reuse if we want.
    // Given the prompt "Secure Storage", let's use a mutex-protected connection or just path.
    // Prompt says "State: It must hold the config.json path and the config.db path."
    // It doesn't strictly say it holds a connection.
}

#[pymethods]
impl ConfigManager {
    #[new]
    fn new(config_path: String, db_path: String, master_key: String) -> PyResult<Self> {
        let cp = PathBuf::from(config_path);
        let dp = PathBuf::from(db_path);

        // Derive 32-byte key from master_key string using SHA256
        let mut hasher = Sha256::new();
        hasher.update(master_key.as_bytes());
        let result = hasher.finalize();
        let mut key = [0u8; 32];
        key.copy_from_slice(&result);

        // Initialize DB table
        if let Some(parent) = dp.parent() {
            fs::create_dir_all(parent)?;
        }
        let conn = Connection::open(&dp).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to open config DB: {}", e))
        })?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS provider_settings (
                provider_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL, -- Encrypted (IV + Ciphertext)
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (provider_id, key)
            )",
            [],
        ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to init table: {}", e)))?;

        Ok(ConfigManager {
            config_path: cp,
            db_path: dp,
            key,
        })
    }

    fn get_setting(&self, key: String) -> PyResult<Option<String>> {
        if !self.config_path.exists() {
            return Ok(None);
        }

        let content = fs::read_to_string(&self.config_path)?;
        let v: Value = serde_json::from_str(&content).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to parse JSON: {}", e))
        })?;

        // Support dot notation? Prompt says "get_setting(key: String)".
        // Assuming top level or simple key.
        // Let's support simple top-level for now.
        if let Some(val) = v.get(&key) {
             if let Some(s) = val.as_str() {
                 Ok(Some(s.to_string()))
             } else {
                 Ok(Some(val.to_string()))
             }
        } else {
            Ok(None)
        }
    }

    fn set_secret(&self, provider_id: String, key: String, value: String) -> PyResult<()> {
        let cipher = Aes256Gcm::new(&self.key.into());
        let nonce = Aes256Gcm::generate_nonce(&mut OsRng); // 96-bits; unique per message

        let ciphertext = cipher.encrypt(&nonce, value.as_bytes())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Encryption failed: {}", e)))?;

        // Combine Nonce + Ciphertext
        let mut combined = nonce.to_vec();
        combined.extend_from_slice(&ciphertext);

        let stored_value = BASE64_STANDARD.encode(combined);

        let conn = Connection::open(&self.db_path).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to open DB: {}", e))
        })?;

        conn.execute(
            "INSERT OR REPLACE INTO provider_settings (provider_id, key, value) VALUES (?1, ?2, ?3)",
            params![provider_id, key, stored_value],
        ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("DB write failed: {}", e)))?;

        Ok(())
    }

    fn get_secret(&self, provider_id: String, key: String) -> PyResult<String> {
        let conn = Connection::open(&self.db_path).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to open DB: {}", e))
        })?;

        let stored_value: Option<String> = conn.query_row(
            "SELECT value FROM provider_settings WHERE provider_id = ?1 AND key = ?2",
            params![provider_id, key],
            |row| row.get(0),
        ).optional().map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("DB read failed: {}", e)))?;

        if let Some(b64_val) = stored_value {
            let combined = BASE64_STANDARD.decode(b64_val).map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Base64 decode failed: {}", e))
            })?;

            if combined.len() < 12 {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid secret data length"));
            }

            let (nonce_bytes, ciphertext_bytes) = combined.split_at(12);
            let nonce = aes_gcm::Nonce::from_slice(nonce_bytes);
            let cipher = Aes256Gcm::new(&self.key.into());

            let plaintext_bytes = cipher.decrypt(nonce, ciphertext_bytes)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Decryption failed: {}", e)))?;

            let plaintext = String::from_utf8(plaintext_bytes).map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid UTF-8: {}", e))
            })?;

            Ok(plaintext)
        } else {
            Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>("Secret not found"))
        }
    }
}

// Static helper to expose get_database_path for LibraryManager
pub fn get_database_path() -> PathBuf {
    if let Ok(p) = std::env::var("SOULSYNC_DATA_DIR") {
        PathBuf::from(p).join("music_library.db")
    } else {
        PathBuf::from("data").join("music_library.db")
    }
}
