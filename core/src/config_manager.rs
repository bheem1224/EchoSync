use pyo3::prelude::*;
use rusqlite::{params, Connection, OptionalExtension};
use std::fs;
use std::path::{Path, PathBuf};
use std::env;
use std::sync::Mutex; // Not strictly needed if we don't have interior mutability that requires sync across threads for these fields, but generic PyClass usually implies strict thread safety. Actually, PyClass struct fields are immutable by default unless Mutex used.
// But here, paths and key are set at creation and immutable.
use aes_gcm::{
    aead::{Aead, KeyInit, OsRng, AeadCore},
    Aes256Gcm, Nonce
};
use sha2::{Sha256, Digest};
use base64::prelude::*;
use serde_json::Value;
use pythonize::pythonize;
use rand::RngCore;
use log::{info, warn};

#[pyclass]
pub struct ConfigManager {
    config_dir: PathBuf,
    data_dir: PathBuf,
    log_dir: PathBuf,
    key: [u8; 32],
}

#[pymethods]
impl ConfigManager {
    #[new]
    fn new() -> PyResult<Self> {
        // A. Path Resolution
        let config_dir = resolve_path("SOULSYNC_CONFIG_DIR", "config");
        let data_dir = resolve_path("SOULSYNC_DATA_DIR", "data");
        let log_dir = if let Ok(p) = env::var("SOULSYNC_LOG_DIR") {
            PathBuf::from(p)
        } else {
            data_dir.join("logs")
        };

        // Ensure directories exist
        fs::create_dir_all(&config_dir)?;
        fs::create_dir_all(&data_dir)?;
        fs::create_dir_all(&log_dir)?;

        // B. Master Key Bootstrap (Hybrid Fallback)
        let master_key = if let Ok(k) = env::var("MASTER_KEY") {
             if !k.is_empty() {
                 k
             } else {
                 bootstrap_key(&config_dir)?
             }
        } else {
             bootstrap_key(&config_dir)?
        };

        // Derive 32-byte key
        let mut hasher = Sha256::new();
        hasher.update(master_key.as_bytes());
        let result = hasher.finalize();
        let mut key = [0u8; 32];
        key.copy_from_slice(&result);

        // Initialize DB table
        let db_path = data_dir.join("music_library.db");
        let conn = Connection::open(&db_path).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to open DB at {:?}: {}", db_path, e))
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
            config_dir,
            data_dir,
            log_dir,
            key,
        })
    }

    fn get_config_dir(&self) -> String {
        self.config_dir.to_string_lossy().to_string()
    }

    fn get_data_dir(&self) -> String {
        self.data_dir.to_string_lossy().to_string()
    }

    fn get_log_dir(&self) -> String {
        self.log_dir.to_string_lossy().to_string()
    }

    fn get_setting(&self, py: Python<'_>, key: String) -> PyResult<Option<PyObject>> {
        let config_file = self.config_dir.join("config.json");
        if !config_file.exists() {
            return Ok(None);
        }

        let content = fs::read_to_string(&config_file)?;
        let v: Value = serde_json::from_str(&content).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to parse JSON: {}", e))
        })?;

        // Extract field. Support dot notation?
        // The previous implementation supported simple keys. Let's start with simple keys.
        // If the key exists in the JSON object
        if let Some(val) = v.get(&key) {
             let py_obj = pythonize(py, val).map_err(|e| {
                 PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to pythonize value: {}", e))
             })?;
             Ok(Some(py_obj.unbind()))
        } else {
            Ok(None)
        }
    }

    fn set_secret(&self, provider_id: String, key: String, value: String) -> PyResult<()> {
        let cipher = Aes256Gcm::new(&self.key.into());
        let nonce = Aes256Gcm::generate_nonce(&mut OsRng); // 96-bits

        let ciphertext = cipher.encrypt(&nonce, value.as_bytes())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Encryption failed: {}", e)))?;

        // Combine Nonce + Ciphertext
        let mut combined = nonce.to_vec();
        combined.extend_from_slice(&ciphertext);

        let stored_value = BASE64_STANDARD.encode(combined);
        let db_path = self.data_dir.join("music_library.db");

        let conn = Connection::open(&db_path).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to open DB: {}", e))
        })?;

        conn.execute(
            "INSERT OR REPLACE INTO provider_settings (provider_id, key, value) VALUES (?1, ?2, ?3)",
            params![provider_id, key, stored_value],
        ).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("DB write failed: {}", e)))?;

        Ok(())
    }

    fn get_secret(&self, provider_id: String, key: String) -> PyResult<String> {
        let db_path = self.data_dir.join("music_library.db");
        let conn = Connection::open(&db_path).map_err(|e| {
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

fn bootstrap_key(config_dir: &Path) -> PyResult<String> {
    let key_file = config_dir.join("master.key");

    // Check file
    if key_file.exists() {
        let key = fs::read_to_string(&key_file).map_err(|e| {
             PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to read master.key: {}", e))
        })?;
        let trimmed = key.trim().to_string();
        if !trimmed.is_empty() {
            return Ok(trimmed);
        }
    }

    // Generate new
    let mut key_bytes = [0u8; 32];
    OsRng.fill_bytes(&mut key_bytes);
    let new_key = BASE64_STANDARD.encode(key_bytes);

    // Write to file
    fs::write(&key_file, &new_key).map_err(|e| {
         PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to write master.key: {}", e))
    })?;

    warn!("⚠️ MASTER_KEY not found! Generated new master.key in {:?}. For higher security, move this value to the MASTER_KEY env var and delete the file.", key_file);
    println!("⚠️ MASTER_KEY not found! Generated new master.key in {:?}. For higher security, move this value to the MASTER_KEY env var and delete the file.", key_file);

    Ok(new_key)
}

// Helper for path resolution
fn resolve_path(env_var: &str, default: &str) -> PathBuf {
    if let Ok(p) = env::var(env_var) {
        let path = PathBuf::from(p);
        if path.is_absolute() {
            path
        } else {
            // If relative, make it absolute relative to CWD
            if let Ok(cwd) = env::current_dir() {
                cwd.join(path)
            } else {
                path
            }
        }
    } else {
        let path = PathBuf::from(default);
        if let Ok(cwd) = env::current_dir() {
            cwd.join(path)
        } else {
            path
        }
    }
}

// Static helper to expose get_database_path for LibraryManager
// We must mirror logic used in new() for data_dir
pub fn get_database_path() -> PathBuf {
    let data_dir = resolve_path("SOULSYNC_DATA_DIR", "data");
    data_dir.join("music_library.db")
}
