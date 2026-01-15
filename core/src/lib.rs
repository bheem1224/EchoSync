use pyo3::prelude::*;

mod structs;
mod library_manager;
mod config_manager;

use structs::SoulSyncTrack;
use library_manager::LibraryManager;

#[pymodule]
fn core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    pyo3_log::init();

    m.add_class::<SoulSyncTrack>()?;
    m.add_class::<LibraryManager>()?;
    Ok(())
}
