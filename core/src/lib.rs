use pyo3::prelude::*;

mod structs;
mod library_manager;
mod config_manager;
mod health;
mod worker;
mod matching;
mod search_manager;
pub mod errors;
pub mod provider_trait;
mod logging;
mod limiter;
mod scheduler;
mod wishlist;

use structs::SoulSyncTrack;
use library_manager::LibraryManager;
use config_manager::ConfigManager;
use health::HealthMonitor;
use worker::BackgroundWorker;
use search_manager::SearchManager;
use logging::TieredLogger;
use limiter::RateLimiter;
use scheduler::Scheduler;
use wishlist::WishlistManager;

#[pymodule]
fn core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    pyo3_log::init();

    m.add_class::<SoulSyncTrack>()?;
    m.add_class::<LibraryManager>()?;
    m.add_class::<ConfigManager>()?;
    m.add_class::<HealthMonitor>()?;
    m.add_class::<BackgroundWorker>()?;
    m.add_class::<SearchManager>()?;
    m.add_class::<TieredLogger>()?;
    m.add_class::<RateLimiter>()?;
    m.add_class::<Scheduler>()?;
    m.add_class::<WishlistManager>()?;
    Ok(())
}
