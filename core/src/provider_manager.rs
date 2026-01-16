// Explicit Import Block
use crate::provider_trait::{Provider, ProviderFactory, ProviderContext, Capabilities};
use crate::provider_cache::ProviderCache;
use crate::structs::SoulSyncTrack;
use crate::errors::SoulSyncError;
use crate::download_manager::DownloadStatus;
use crate::config_manager::ConfigManager;
use std::sync::Arc;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3_async_runtimes::tokio::future_into_py;
use futures::future::{BoxFuture, FutureExt};
use dashmap::DashMap;
use log::{error, info};
use std::panic::AssertUnwindSafe;

/// The Warden: Manages the lifecycle of providers, ensuring safety and stability.
#[pyclass]
#[derive(Clone)]
pub struct ProviderManager {
    factories: Arc<DashMap<String, Box<dyn ProviderFactory>>>,
    active_providers: Arc<DashMap<String, Arc<dyn Provider>>>,
    config: Arc<ConfigManager>,
    cache: Arc<ProviderCache>,
}

#[pymethods]
impl ProviderManager {
    /// Search for tracks across all enabled providers.
    /// Returns a list of results (list of lists of tracks).
    #[pyo3(name = "search")]
    fn search_py<'a>(&self, py: Python<'a>, query: String) -> PyResult<Bound<'a, PyAny>> {
        let this = self.clone();
        future_into_py(py, async move {
            let results: Vec<Result<Vec<SoulSyncTrack>, SoulSyncError>> = this.search_all(&query).await;

            // Flatten results to a single list of tracks for Python convenience
            let mut flat_tracks: Vec<SoulSyncTrack> = Vec::new();
            for res in results {
                if let Ok(tracks) = res {
                    flat_tracks.extend(tracks);
                }
            }
            Ok(flat_tracks)
        })
    }

    /// Get capabilities of a specific provider.
    fn get_capabilities(&self, py: Python<'_>, provider_id: String) -> PyResult<PyObject> {
        // If active, get from instance
        if let Some(provider) = self.active_providers.get(&provider_id) {
            let caps = provider.capabilities();
            return Ok(capabilities_to_dict(py, &caps)?);
        }

        // If not active, try to instantiate momentarily (sync) to check caps
        if let Some(factory_ref) = self.factories.get(&provider_id) {
             // Create a temporary context
             let ctx = ProviderContext {
                config: self.config.clone(),
                cache: self.cache.clone(),
                provider_id: provider_id.clone(),
             };

             let factory = factory_ref.value();
             // Safe instantiation
             let provider_result = std::panic::catch_unwind(AssertUnwindSafe(|| {
                 factory.new_provider(ctx)
             }));

             match provider_result {
                 Ok(p) => {
                     let caps = p.capabilities();
                     Ok(capabilities_to_dict(py, &caps)?)
                 },
                 Err(_) => {
                      Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Provider {} crashed during capability check", provider_id)))
                 }
             }
        } else {
             Err(PyErr::new::<pyo3::exceptions::PyLookupError, _>(format!("Provider {} not found", provider_id)))
        }
    }

    #[pyo3(name = "download")]
    fn download_py<'a>(&self, py: Python<'a>, provider_id: String, track: SoulSyncTrack) -> PyResult<Bound<'a, PyAny>> {
        let this = self.clone();
        future_into_py(py, async move {
            match this.download(&provider_id, &track).await {
                Ok(status) => {
                    Ok(status)
                },
                Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Download failed: {}", e)))
            }
        })
    }
}

// Helper
fn capabilities_to_dict(py: Python, caps: &Capabilities) -> PyResult<PyObject> {
    let dict = PyDict::new(py);
    dict.set_item("can_search", caps.can_search)?;
    dict.set_item("can_download", caps.can_download)?;
    dict.set_item("can_sync", caps.can_sync)?;
    Ok(dict.into())
}

impl ProviderManager {
    pub fn new(config: Arc<ConfigManager>, cache: Arc<ProviderCache>) -> Self {
        Self {
            factories: Arc::new(DashMap::new()),
            active_providers: Arc::new(DashMap::new()),
            config,
            cache,
        }
    }

    pub fn register_factory(&self, factory: Box<dyn ProviderFactory>) {
        info!("Registering provider factory: {}", factory.id());
        self.factories.insert(factory.id().to_string(), factory);
    }

    pub fn get_all_ids(&self) -> Vec<String> {
        self.factories.iter().map(|r| r.key().clone()).collect()
    }

    pub fn get_enabled_ids(&self) -> Vec<String> {
        self.get_all_ids()
    }

    async fn get_provider_instance(&self, id: &str) -> Result<Arc<dyn Provider>, SoulSyncError> {
        if let Some(p) = self.active_providers.get(id) {
            return Ok(p.value().clone());
        }

        let ctx = ProviderContext {
            config: self.config.clone(),
            cache: self.cache.clone(),
            provider_id: id.to_string(),
        };

        // Sync instantiation block
        // Explicitly type annotation to fix E0282
        let provider_arc: Arc<dyn Provider> = {
            let factory_ref = self.factories.get(id)
                .ok_or_else(|| SoulSyncError::UnknownClient(format!("Provider ID '{}' not found", id)))?;

            let factory = factory_ref.value();

            let provider_result = std::panic::catch_unwind(AssertUnwindSafe(|| {
                 factory.new_provider(ctx)
            }));

            match provider_result {
                Ok(provider) => Arc::from(provider),
                Err(_) => {
                    error!("Provider factory '{}' panicked during instantiation!", id);
                    return Err(SoulSyncError::ProviderError(format!("Provider '{}' crashed during startup", id)));
                }
            }
        };

        self.active_providers.insert(id.to_string(), provider_arc.clone());
        Ok(provider_arc)
    }

    async fn call_provider_safe<F, T>(&self, provider_id: &str, f: F) -> Result<T, SoulSyncError>
    where
        for<'a> F: FnOnce(&'a dyn Provider) -> BoxFuture<'a, Result<T, SoulSyncError>> + Send,
        T: Send + 'static,
    {
        let provider = self.get_provider_instance(provider_id).await?;
        let future = f(provider.as_ref());
        let result = AssertUnwindSafe(future).catch_unwind().await;

        match result {
            Ok(execution_result) => execution_result,
            Err(_) => {
                error!("CRITICAL: Provider '{}' panicked! Disabling instance.", provider_id);
                self.active_providers.remove(provider_id);
                Err(SoulSyncError::ProviderError(format!("Provider '{}' crashed unexpectedly.", provider_id)))
            }
        }
    }

    pub async fn search_all(&self, query: &str) -> Vec<Result<Vec<SoulSyncTrack>, SoulSyncError>> {
        let providers = self.get_enabled_ids();
        let mut results = Vec::new();

        for id in providers {
            let q = query.to_string();
            let ctx = ProviderContext {
                config: self.config.clone(),
                cache: self.cache.clone(),
                provider_id: id.clone()
            };

            // Explicitly annotate 'res' type to help inference
            let res: Result<Vec<SoulSyncTrack>, SoulSyncError> = self.call_provider_safe(&id, |p| {
                let q_clone = q.clone();
                let ctx_clone = ctx.clone();
                async move {
                    if p.capabilities().can_search {
                         p.search(&ctx_clone, &q_clone).await
                    } else {
                        Ok(Vec::new())
                    }
                }.boxed()
            }).await.and_then(|r| Ok(r));

            results.push(res);
        }

        results
    }

    pub async fn download(&self, provider_id: &str, track: &SoulSyncTrack) -> Result<DownloadStatus, SoulSyncError> {
        let ctx = ProviderContext {
            config: self.config.clone(),
            cache: self.cache.clone(),
            provider_id: provider_id.to_string()
        };
        let t = track.clone();

        self.call_provider_safe(provider_id, |p| {
            let ctx_clone = ctx.clone();
            let t_clone = t.clone();
            async move {
                if !p.capabilities().can_download {
                    return Err(SoulSyncError::ProviderError("Provider does not support download".to_string()));
                }
                p.download(&ctx_clone, &t_clone).await
            }.boxed()
        }).await.and_then(|r| Ok(r))
    }
}
