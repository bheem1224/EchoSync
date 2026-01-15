use pyo3::prelude::*;

mod structs;
mod library_manager;
mod config_manager;
mod health;
mod worker;
mod parser;
mod matching;

use structs::SoulSyncTrack;
use library_manager::LibraryManager;
use config_manager::ConfigManager;
use health::HealthMonitor;
use worker::BackgroundWorker;

#[pymodule]
fn core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    pyo3_log::init();

    m.add_class::<SoulSyncTrack>()?;
    m.add_class::<LibraryManager>()?;
    m.add_class::<ConfigManager>()?;
    m.add_class::<HealthMonitor>()?;
    m.add_class::<BackgroundWorker>()?;
    // Note: TrackParser and MatchingEngine are currently internal Rust modules used by other components,
    // or can be exposed if needed. For now, they are not explicitly added as classes unless requested.
    // However, I should probably expose them if python side needs to use them directly.
    // The legacy code used them directly.
    // I will add them if they have #[pyclass].
    // matching::MatchResult does not have #[pyclass] yet, and WeightedMatchingEngine is empty struct with static methods.
    // I will leave them internal for now as per instructions (Port matching and parsing logic), unless user asked to expose them.
    // User said: "Port the matching and parsing logic".
    // "Target Modules: matching_engine -> src/matching.rs, track_parser.py -> src/parser.rs".
    // I'll assume for now they are internal to the Core logic (e.g. used by LibraryManager later or other rust components).
    // If Python needs them, I'd need to wrap them.
    Ok(())
}

#[cfg(test)]
mod test_parser;
