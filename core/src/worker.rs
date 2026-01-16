use pyo3::prelude::*;
use std::sync::{Arc, Mutex};
use std::collections::VecDeque;
use crate::structs::SoulSyncTrack;
use crate::library_manager::LibraryManager;

#[pyclass]
pub struct BackgroundWorker {
    queue: Arc<Mutex<VecDeque<SoulSyncTrack>>>,
    library_manager: Py<LibraryManager>,
}

#[pymethods]
impl BackgroundWorker {
    #[new]
    fn new(library_manager: Py<LibraryManager>) -> Self {
        BackgroundWorker {
            queue: Arc::new(Mutex::new(VecDeque::new())),
            library_manager,
        }
    }

    fn queue_track(&self, track: SoulSyncTrack) {
        let mut q = self.queue.lock().unwrap();
        q.push_back(track);
    }

    fn queue_depth(&self) -> usize {
        let q = self.queue.lock().unwrap();
        q.len()
    }

    fn process_queue(&self, py: Python<'_>, batch_size: usize) -> PyResult<usize> {
        let mut batch = Vec::with_capacity(batch_size);
        {
            let mut q = self.queue.lock().unwrap();
            for _ in 0..batch_size {
                if let Some(track) = q.pop_front() {
                    batch.push(track);
                } else {
                    break;
                }
            }
        }

        let count = batch.len();
        if count == 0 {
            return Ok(0);
        }

        let lm = self.library_manager.borrow(py);
        // process_batch now returns () because it is fire-and-forget
        lm.process_batch(batch)?;
        Ok(count)
    }
}
