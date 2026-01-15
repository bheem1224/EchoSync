use pyo3::prelude::*;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum SoulSyncError {
    #[error("Database error: {0}")]
    DatabaseError(String),

    #[error("Network error: {0}")]
    NetworkError(String),

    #[error("Download error: {0}")]
    DownloadError(String),

    #[error("Provider error: {0}")]
    ProviderError(String),

    #[error("Unknown client: {0}")]
    UnknownClient(String),

    #[error("Other error: {0}")]
    Other(String),
}

// Implement From<SoulSyncError> for PyErr
impl From<SoulSyncError> for PyErr {
    fn from(err: SoulSyncError) -> PyErr {
        match err {
            SoulSyncError::DatabaseError(msg) => pyo3::exceptions::PyIOError::new_err(msg),
            SoulSyncError::NetworkError(msg) => pyo3::exceptions::PyConnectionError::new_err(msg),
            _ => pyo3::exceptions::PyRuntimeError::new_err(err.to_string()),
        }
    }
}
