use pyo3::exceptions::{PyIOError, PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use thiserror::Error;

/// Custom Rust error type covering I/O, Database, and Parsing failures.
#[derive(Error, Debug)]
pub enum EchoSyncError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Database error: {0}")]
    Database(#[from] rusqlite::Error),

    #[error("Parsing error: {0}")]
    Parse(String),

    #[error("Internal error: {0}")]
    Internal(String),
}

/// Convert EchoSyncError to Python PyErr exception across the FFI boundary.
impl From<EchoSyncError> for PyErr {
    fn from(err: EchoSyncError) -> PyErr {
        match err {
            EchoSyncError::Io(e) => PyIOError::new_err(e.to_string()),
            EchoSyncError::Database(e) => PyRuntimeError::new_err(format!("Database error: {}", e)),
            EchoSyncError::Parse(e) => PyValueError::new_err(e),
            EchoSyncError::Internal(e) => PyRuntimeError::new_err(e),
        }
    }
}

pub type Result<T> = std::result::Result<T, EchoSyncError>;
