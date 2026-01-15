use thiserror::Error;
use pyo3::prelude::*;
use pyo3::create_exception;
use pyo3::exceptions::{PyException, PyRuntimeError, PyValueError, PyConnectionError};

create_exception!(core, PySoulSyncError, PyException);

#[derive(Error, Debug)]
pub enum SoulSyncError {
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

impl From<SoulSyncError> for PyErr {
    fn from(err: SoulSyncError) -> PyErr {
        match err {
            SoulSyncError::DatabaseError(e) => PyRuntimeError::new_err(format!("Database Error: {}", e)),
            SoulSyncError::ConfigError(e) => PyValueError::new_err(format!("Config Error: {}", e)),
            SoulSyncError::NetworkError(e) => PyConnectionError::new_err(format!("Network Error: {}", e)),
            SoulSyncError::IoError(e) => PyRuntimeError::new_err(format!("IO Error: {}", e)),
            SoulSyncError::LimitExceeded(e) => PySoulSyncError::new_err(format!("Limit Exceeded: {}", e)),
            SoulSyncError::ProviderError(e) => PySoulSyncError::new_err(format!("Provider Error: {}", e)),
            SoulSyncError::UnknownClient(e) => PySoulSyncError::new_err(format!("Unknown Client: {}", e)),
            SoulSyncError::Other(e) => PySoulSyncError::new_err(format!("Unexpected Error: {}", e)),
        }
    }
}
