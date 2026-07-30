/// Progress message struct sent over MPSC channel from Rayon worker threads to Python FFI dispatcher.
#[derive(Debug, Clone)]
pub struct ProgressMsg {
    pub processed: usize,
    pub total: usize,
    pub status: String,
}

/// Scanner module for high-throughput directory scanning routines.
pub struct DirectoryScanner;

impl DirectoryScanner {
    pub fn new() -> Self {
        DirectoryScanner
    }
}
