use pyo3::prelude::*;

mod structs;
mod library_manager;
mod config_manager;
mod health;
mod worker;
mod parser;
mod matching;
mod search_manager;
pub mod errors;
pub mod provider_trait;
mod logging;
mod limiter;
mod scheduler;
mod wishlist;
mod download_manager;
mod post_processor;
mod scanner_service;
mod importer_service;

use structs::{SoulSyncTrack, Artist, Album, ReleaseGroup};
use library_manager::LibraryManager;
use config_manager::ConfigManager;
use health::HealthMonitor;
use worker::BackgroundWorker;
use search_manager::SearchManager;
use logging::TieredLogger;
use limiter::RateLimiter;
use scheduler::Scheduler;
use wishlist::WishlistManager;
use errors::PySoulSyncError;
use parser::TrackParser;
use download_manager::{DownloadManager, DownloadStatus, DownloadItem};
use post_processor::PostProcessor;
use scanner_service::ScannerService;
use importer_service::ImporterService;

#[pymodule]
fn core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    pyo3_log::init();

    m.add_class::<SoulSyncTrack>()?;
    m.add_class::<Artist>()?;
    m.add_class::<Album>()?;
    m.add_class::<ReleaseGroup>()?;

    m.add_class::<LibraryManager>()?;
    m.add_class::<ConfigManager>()?;
    m.add_class::<HealthMonitor>()?;
    m.add_class::<BackgroundWorker>()?;
    m.add_class::<SearchManager>()?;
    m.add_class::<TieredLogger>()?;
    m.add_class::<RateLimiter>()?;
    m.add_class::<Scheduler>()?;
    m.add_class::<WishlistManager>()?;
    m.add_class::<TrackParser>()?;
    m.add_class::<DownloadManager>()?;
    m.add_class::<DownloadStatus>()?;
    m.add_class::<DownloadItem>()?;

    m.add_class::<PostProcessor>()?;
    m.add_class::<ScannerService>()?;
    m.add_class::<ImporterService>()?;

    // Register the custom exception as "SoulSyncError"
    m.add("SoulSyncError", m.py().get_type::<PySoulSyncError>())?;

    Ok(())
}

#[cfg(test)]
mod test_parser;
pub mod provider_manager;
