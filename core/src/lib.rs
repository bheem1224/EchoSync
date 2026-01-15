use pyo3::prelude::*;

mod structs;
mod library_manager;
mod config_manager;
mod health;
mod worker;
mod matching;
mod search_manager;

use structs::SoulSyncTrack;
use library_manager::LibraryManager;
use config_manager::ConfigManager;
use health::HealthMonitor;
use worker::BackgroundWorker;
use search_manager::SearchManager;

#[pymodule]
fn core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    pyo3_log::init();

    m.add_class::<SoulSyncTrack>()?;
    m.add_class::<LibraryManager>()?;
    m.add_class::<ConfigManager>()?;
    m.add_class::<HealthMonitor>()?;
    m.add_class::<BackgroundWorker>()?;
    m.add_class::<SearchManager>()?;
    Ok(())
}
