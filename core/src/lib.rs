use pyo3::prelude::*;
use std::sync::Arc;

pub mod structs;
pub mod library_manager;
pub mod scanner_service;
pub mod importer_service;
pub mod provider_trait;
pub mod provider_manager;
pub mod provider_cache;
pub mod config_manager;
pub mod errors;
pub mod download_manager;
pub mod parser;
pub mod matching;
pub mod limiter;
pub mod search_manager;
pub mod post_processor;
pub mod logging;
pub mod health;
pub mod wishlist;
pub mod worker;
pub mod scheduler;

// Removed path_helper as it does not exist in Rust source

use crate::structs::{SoulSyncTrack, Artist, Album, ReleaseGroup};
use crate::library_manager::LibraryManager;
use crate::scanner_service::ScannerService;
use crate::importer_service::ImporterService;
use crate::provider_manager::ProviderManager;
use crate::config_manager::ConfigManager;
use crate::provider_cache::ProviderCache;

#[pymodule]
fn soulsync_core(py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Initialize logging
    pyo3_log::init();

    // Register Structs
    m.add_class::<SoulSyncTrack>()?;
    m.add_class::<Artist>()?;
    m.add_class::<Album>()?;
    m.add_class::<ReleaseGroup>()?;
    m.add_class::<SoulSyncTrack>()?;
    m.add_class::<LibraryManager>()?;

    // Register Services
    m.add_class::<LibraryManager>()?;
    m.add_class::<ScannerService>()?;
    m.add_class::<ImporterService>()?;
    m.add_class::<ProviderManager>()?;
    m.add_class::<ConfigManager>()?;

    Ok(())
}
