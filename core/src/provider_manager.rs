use std::sync::Arc;
use dashmap::DashMap;
use crate::errors::SoulSyncError;
use crate::structs::SoulSyncTrack;
use crate::download_manager::DownloadStatus;
use std::panic::AssertUnwindSafe;
use futures::FutureExt;
use futures::future::BoxFuture;
use log::{error, info};

use crate::provider_trait::*;
use crate::provider_cache::ProviderCache;
use crate::config_manager::ConfigManager;

/// The Warden: Manages the lifecycle of providers, ensuring safety and stability.
pub struct ProviderManager {
    factories: DashMap<String, Box<dyn ProviderFactory>>,
    active_providers: DashMap<String, Arc<dyn Provider>>,
    config: Arc<ConfigManager>,
    cache: Arc<ProviderCache>,
}

impl ProviderManager {
    pub fn new(config: Arc<ConfigManager>, cache: Arc<ProviderCache>) -> Self {
        Self {
            factories: DashMap::new(),
            active_providers: DashMap::new(),
            config,
            cache,
        }
    }

    /// Registers a provider factory.
    pub fn register_factory(&self, factory: Box<dyn ProviderFactory>) {
        info!("Registering provider factory: {}", factory.id());
        self.factories.insert(factory.id().to_string(), factory);
    }

    /// Returns a list of all registered provider IDs.
    pub fn get_all_ids(&self) -> Vec<String> {
        self.factories.iter().map(|r| r.key().clone()).collect()
    }

    /// Returns a list of enabled provider IDs (based on config or default enabled).
    /// For now, assumes all registered factories imply availability,
    /// but in real logic we might check config.
    pub fn get_enabled_ids(&self) -> Vec<String> {
        // TODO: Filter by config enabled/disabled state
        self.get_all_ids()
    }

    /// Retrieves a provider instance, initializing it if necessary.
    /// Returns a reference to the provider if found and successfully initialized.
    async fn get_provider_instance(&self, id: &str) -> Result<Arc<dyn Provider>, SoulSyncError> {
        // 1. Fast path: check if active
        if let Some(p) = self.active_providers.get(id) {
            return Ok(p.value().clone());
        }

        // 2. Slow path: Instantiate
        // Check if factory exists
        let factory = self.factories.get(id)
            .ok_or_else(|| SoulSyncError::UnknownClient(format!("Provider ID '{}' not found in registry", id)))?;

        info!("Instantiating provider: {}", id);

        let ctx = ProviderContext {
            config: self.config.clone(),
            cache: self.cache.clone(),
        };

        // Instantiate (Synchronous factory call as per requirement, but likely fast)
        // We use AssertUnwindSafe here too just in case the factory panics
        let provider_result = std::panic::catch_unwind(AssertUnwindSafe(|| {
             factory.new_provider(ctx)
        }));

        match provider_result {
            Ok(provider) => {
                 // Convert Box<dyn Provider> to Arc<dyn Provider>
                 let arc_provider: Arc<dyn Provider> = Arc::from(provider);
                 self.active_providers.insert(id.to_string(), arc_provider.clone());
                 Ok(arc_provider)
            },
            Err(_) => {
                error!("Provider factory '{}' panicked during instantiation!", id);
                Err(SoulSyncError::ProviderError(format!("Provider '{}' crashed during startup", id)))
            }
        }
    }

    /// Safely calls an async method on a provider.
    ///
    /// Wraps the execution in `catch_unwind`. If the provider panics,
    /// it is removed from the active pool to prevent future instability.
    async fn call_provider_safe<F, T>(&self, provider_id: &str, f: F) -> Result<T, SoulSyncError>
    where
        for<'a> F: FnOnce(&'a dyn Provider) -> BoxFuture<'a, Result<T, SoulSyncError>> + Send,
        T: Send + 'static,
    {
        // Get the provider (cloned Arc, safe to hold across await)
        let provider = self.get_provider_instance(provider_id).await?;

        // Execute the future with panic protection
        let future = f(provider.as_ref());
        let result = AssertUnwindSafe(future).catch_unwind().await;

        match result {
            Ok(execution_result) => {
                // Normal execution (Success or regular Error)
                execution_result
            },
            Err(_) => {
                // Panic occurred!
                error!("CRITICAL: Provider '{}' panicked! Disabling instance.", provider_id);

                // Remove the poisoned provider
                self.active_providers.remove(provider_id);

                Err(SoulSyncError::ProviderError(format!("Provider '{}' crashed unexpectedly.", provider_id)))
            }
        }
    }

    // --- Public API ---

    pub async fn search_all(&self, query: &str) -> Vec<Result<Vec<SoulSyncTrack>, SoulSyncError>> {
        let providers = self.get_enabled_ids();
        let mut results = Vec::new();

        // Sequential or Concurrent?
        // For strict safety and simplicity in this iteration, we loop.
        // In a real scenario, we might want `join_all`.
        for id in providers {
            // Check capabilities first? (Need to instantiate to check capabilities? Or should Factory have capabilities?)
            // Requirement said Provider has capabilities. So we instantiate.

            // We clone ID and Query for the closure
            let q = query.to_string();
            let ctx = ProviderContext { config: self.config.clone(), cache: self.cache.clone() };

            let res = self.call_provider_safe(&id, |p| {
                let q_clone = q.clone();
                let ctx_clone = ctx.clone();
                async move {
                    if p.capabilities().can_search {
                        p.search(&ctx_clone, &q_clone).await
                    } else {
                        Ok(Vec::new()) // Skip
                    }
                }.boxed()
            }).await.and_then(|r| r);

            results.push(res);
        }

        results
    }

    pub async fn download(&self, provider_id: &str, track: &SoulSyncTrack) -> Result<DownloadStatus, SoulSyncError> {
        let ctx = ProviderContext { config: self.config.clone(), cache: self.cache.clone() };
        // We need to clone track because `track` ref can't be passed easily into async closure with lifetime constraints
        // unless we deal with higher-rank trait bounds carefully.
        // `SoulSyncTrack` is Clone, so cloning is safest.
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
        }).await.and_then(|r| r)
    }
}
