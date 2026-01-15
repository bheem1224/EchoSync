use pyo3::prelude::*;
use log::{info, warn, error, debug};

#[pyclass]
pub struct TieredLogger {
    source: String,
}

#[pymethods]
impl TieredLogger {
    #[new]
    fn new(source: String) -> Self {
        TieredLogger { source }
    }

    fn info(&self, message: String) {
        info!("[{}] {}", self.source, message);
    }

    fn warning(&self, message: String) {
        warn!("[{}] {}", self.source, message);
    }

    fn error(&self, message: String) {
        error!("[{}] {}", self.source, message);
    }

    fn debug(&self, message: String) {
        debug!("[{}] {}", self.source, message);
    }
}
