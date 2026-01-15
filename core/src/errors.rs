use thiserror::Error;
use pyo3::prelude::*;
use pyo3::create_exception;
use pyo3::exceptions::{PyException, PyRuntimeError, PyValueError, PyConnectionError};

create_exception!(core, SoulSyncError, PyException);

#[derive(Error, Debug)]
pub enum SoulSyncErrorEnum {
    #[error("Database error: {0}")]
    DatabaseError(#[from] rusqlite::Error),

    #[error("Configuration error: {0}")]
    ConfigError(String),

    #[error("Network error: {0}")]
    NetworkError(#[from] reqwest::Error),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Limit exceeded: {0}")]
    LimitExceeded(String),

    #[error("Provider error: {0}")]
    ProviderError(String),

    #[error("Unknown client: {0}")]
    UnknownClient(String),

    #[error("Other error: {0}")]
    Other(String),
}

impl From<SoulSyncErrorEnum> for PyErr {
    fn from(err: SoulSyncErrorEnum) -> PyErr {
        match err {
            // Map DatabaseError to SoulSyncError (or keep RuntimeError if preferred, but user requested custom class)
            // Ideally, we might want subclasses like SoulSyncDatabaseError, but for now we map to the base custom error
            // OR we map to standard Python exceptions where they make sense, and SoulSyncError for domain errors.
            // Let's stick to the previous mapping but maybe wrap generic errors in SoulSyncError?
            // Actually, the user asked to "ensure SoulSyncError is exposed".
            // Let's use SoulSyncError for domain-specific things or generic fallbacks.
            SoulSyncErrorEnum::DatabaseError(e) => PyRuntimeError::new_err(format!("Database Error: {}", e)),
            SoulSyncErrorEnum::ConfigError(e) => PyValueError::new_err(format!("Config Error: {}", e)),
            SoulSyncErrorEnum::NetworkError(e) => PyConnectionError::new_err(format!("Network Error: {}", e)),
            SoulSyncErrorEnum::IoError(e) => PyRuntimeError::new_err(format!("IO Error: {}", e)),
            SoulSyncErrorEnum::LimitExceeded(e) => SoulSyncError::new_err(format!("Limit Exceeded: {}", e)),
            SoulSyncErrorEnum::ProviderError(e) => SoulSyncError::new_err(format!("Provider Error: {}", e)),
            SoulSyncErrorEnum::Other(e) => SoulSyncError::new_err(format!("Unexpected Error: {}", e)),
            SoulSyncErrorEnum::UnknownClient(e) => SoulSyncError::new_err(format!("Unknown Client: {}", e)),
        }
    }
}
