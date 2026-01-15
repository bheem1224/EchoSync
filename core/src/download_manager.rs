use pyo3::prelude::*;
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use crate::structs::SoulSyncTrack;
use crate::errors::SoulSyncError;

// -----------------------------------------------------------------------------
// Structs (DownloadStatus)
// -----------------------------------------------------------------------------

#[pyclass]
#[derive(Clone, Debug)]
pub struct DownloadStatus {
    #[pyo3(get)]
    pub state: String,       // "Queued", "Downloading", "Completed", "Failed"
    #[pyo3(get)]
    pub progress: f32,       // 0.0 to 100.0
    #[pyo3(get)]
    pub error: Option<String>,
}

#[pymethods]
impl DownloadStatus {
    #[new]
    pub fn new(state: String, progress: f32, error: Option<String>) -> Self {
        Self { state, progress, error }
    }
}

// -----------------------------------------------------------------------------
// Traits
// -----------------------------------------------------------------------------

/// The interface for external download clients (e.g., qBittorrent, Slskd).
/// This trait is strictly blocking, as per architecture requirements.
pub trait DownloadClient: Send + Sync {
    /// Returns the unique name of this client (e.g., "qbittorrent", "slskd").
    fn name(&self) -> &str;

    /// Starts a download for the given track.
    /// Returns an external ID (e.g., Torrent Hash, Slskd Transfer ID).
    /// The track object is expected to contain necessary info (e.g. magnet link in identifiers).
    fn start_download(&self, track: &SoulSyncTrack) -> Result<String, SoulSyncError>;

    /// Gets the status of a download by its external ID.
    fn get_status(&self, external_id: &str) -> Result<DownloadStatus, SoulSyncError>;

    /// Gets the local filesystem path of the completed download.
    fn get_download_path(&self, external_id: &str) -> Result<PathBuf, SoulSyncError>;
}

// -----------------------------------------------------------------------------
// Structs
// -----------------------------------------------------------------------------

#[derive(Clone)]
struct DownloadContext {
    track: SoulSyncTrack,
    client_name: String,
    external_id: String,
}

#[pyclass]
#[derive(Clone)]
pub struct DownloadItem {
    #[pyo3(get)]
    pub track: SoulSyncTrack,
    #[pyo3(get)]
    pub status: DownloadStatus,
    #[pyo3(get)]
    pub client_name: String,
    #[pyo3(get)]
    pub external_id: String,
}

#[pymethods]
impl DownloadItem {
    fn __repr__(&self) -> String {
        format!("<DownloadItem title='{}' status={:?}>", self.track.title, self.status)
    }
}

// -----------------------------------------------------------------------------
// DownloadManager
// -----------------------------------------------------------------------------

#[pyclass]
pub struct DownloadManager {
    // We use Arc<Mutex<...>> for interior mutability across thread boundaries if needed,
    // though PyClass usually implies single ownership unless cloned.
    // However, since we might register clients from different contexts, internal mutability is safer.
    clients: Arc<Mutex<HashMap<String, Box<dyn DownloadClient>>>>,

    // Active downloads map: External ID -> DownloadContext
    active_downloads: Arc<Mutex<HashMap<String, DownloadContext>>>,
}

#[pymethods]
impl DownloadManager {
    #[new]
    fn new() -> Self {
        DownloadManager {
            clients: Arc::new(Mutex::new(HashMap::new())),
            active_downloads: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Adds a download to the manager.
    ///
    /// # Arguments
    /// * `track` - The track metadata (must include necessary identifiers/magnet).
    /// * `client_name` - The name of the registered client to use.
    fn add_download(&self, track: SoulSyncTrack, client_name: String) -> PyResult<String> {
        let clients = self.clients.lock().map_err(|e| SoulSyncError::Other(e.to_string()))?;

        let client = clients.get(&client_name)
            .ok_or_else(|| SoulSyncError::UnknownClient(client_name.clone()))?;

        // Start the download via the client
        let external_id = client.start_download(&track)?;

        // Store context
        let context = DownloadContext {
            track,
            client_name: client_name.clone(),
            external_id: external_id.clone(),
        };

        let mut downloads = self.active_downloads.lock().map_err(|e| SoulSyncError::Other(e.to_string()))?;
        downloads.insert(external_id.clone(), context);

        Ok(external_id)
    }

    /// The orchestration tick. Should be called periodically.
    /// Returns a list of newly completed DownloadItems.
    fn tick(&self) -> PyResult<Vec<DownloadItem>> {
        let mut completed_items = Vec::new();

        // We need to lock both maps.
        // To avoid deadlocks, locking order doesn't matter much here as we only hold them briefly,
        // but let's be careful.
        let clients_guard = self.clients.lock().map_err(|e| SoulSyncError::Other(e.to_string()))?;
        let mut downloads_guard = self.active_downloads.lock().map_err(|e| SoulSyncError::Other(e.to_string()))?;

        // We need to collect keys to iterate to avoid borrowing issues while modifying
        let keys: Vec<String> = downloads_guard.keys().cloned().collect();
        let mut ids_to_remove = Vec::new();

        for ext_id in keys {
            if let Some(ctx) = downloads_guard.get_mut(&ext_id) {
                if let Some(client) = clients_guard.get(&ctx.client_name) {
                    match client.get_status(&ext_id) {
                        Ok(status) => {
                            if status.state == "Completed" {
                                // Download finished!
                                // 1. Get final path (optional, maybe update track?)
                                if let Ok(path) = client.get_download_path(&ext_id) {
                                    ctx.track.file_path = Some(path.to_string_lossy().to_string());
                                }

                                // 2. Add to return list
                                completed_items.push(DownloadItem {
                                    track: ctx.track.clone(),
                                    status: status.clone(),
                                    client_name: ctx.client_name.clone(),
                                    external_id: ext_id.clone(),
                                });

                                // 3. Mark for removal from active list
                                ids_to_remove.push(ext_id.clone());
                            } else if status.state == "Failed" {
                                // If failed, do we remove? Or keep it?
                                // Prompt says "Completion... return/emit".
                                // Use case: if failed, we probably want to notify.
                                completed_items.push(DownloadItem {
                                    track: ctx.track.clone(),
                                    status: status.clone(),
                                    client_name: ctx.client_name.clone(),
                                    external_id: ext_id.clone(),
                                });
                                ids_to_remove.push(ext_id.clone());
                            }
                        },
                        Err(e) => {
                            // Error checking status
                            // Actually, let's treat it as a failure so we don't get stuck.
                            let fail_status = DownloadStatus::new("Failed".to_string(), 0.0, Some(e.to_string()));
                            completed_items.push(DownloadItem {
                                track: ctx.track.clone(),
                                status: fail_status,
                                client_name: ctx.client_name.clone(),
                                external_id: ext_id.clone(),
                            });
                            ids_to_remove.push(ext_id.clone());
                        }
                    }
                } else {
                    // Client missing? Should not happen.
                    ids_to_remove.push(ext_id.clone());
                }
            }
        }

        // Cleanup completed/failed downloads from active list
        for id in ids_to_remove {
            downloads_guard.remove(&id);
        }

        Ok(completed_items)
    }

    fn list_active(&self) -> PyResult<Vec<DownloadItem>> {
        let downloads_guard = self.active_downloads.lock().map_err(|e| SoulSyncError::Other(e.to_string()))?;
        let clients_guard = self.clients.lock().map_err(|e| SoulSyncError::Other(e.to_string()))?;

        let mut result = Vec::new();
        for (ext_id, ctx) in downloads_guard.iter() {

             let status = if let Some(client) = clients_guard.get(&ctx.client_name) {
                 client.get_status(ext_id).unwrap_or(DownloadStatus::new("Failed".to_string(), 0.0, Some("Check failed".to_string())))
             } else {
                 DownloadStatus::new("Failed".to_string(), 0.0, Some("Client missing".to_string()))
             };

             result.push(DownloadItem {
                 track: ctx.track.clone(),
                 status,
                 client_name: ctx.client_name.clone(),
                 external_id: ext_id.clone(),
             });
        }
        Ok(result)
    }
}

// Rust-side registration helper (not exposed to Python directly unless we wrap it)
impl DownloadManager {
    pub fn register_client(&self, client: Box<dyn DownloadClient>) -> Result<(), SoulSyncError> {
        let mut clients = self.clients.lock().map_err(|e| SoulSyncError::Other(e.to_string()))?;
        clients.insert(client.name().to_string(), client);
        Ok(())
    }
}
