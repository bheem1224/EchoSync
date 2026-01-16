use std::sync::Arc;
use async_trait::async_trait;
use serde::de::DeserializeOwned;
use tracing::{info, error, instrument};

use crate::structs::SoulSyncTrack;
use crate::config_manager::ConfigManager;
use crate::provider_cache::ProviderCache;
use crate::errors::SoulSyncError;

#[derive(Clone)]
pub struct ProviderContext {
    pub config: Arc<ConfigManager>,
    pub cache: Arc<ProviderCache>,
    pub provider_id: String,
}

impl ProviderContext {
    pub fn new(config: Arc<ConfigManager>, cache: Arc<ProviderCache>, provider_id: String) -> Self {
        ProviderContext {
            config,
            cache,
            provider_id,
        }
    }

    pub fn get_config<T: DeserializeOwned>(&self, key: &str) -> Result<Option<T>, Box<dyn std::error::Error + Send + Sync>> {
        self.config.get_config_value(key)
    }

    pub fn log_info(&self, message: &str) {
        info!(provider_id = %self.provider_id, "{}", message);
    }

    pub fn log_error(&self, message: &str) {
        error!(provider_id = %self.provider_id, "{}", message);
    }
}

pub struct Capabilities {
    pub can_search: bool,
    pub can_download: bool,
    pub can_sync: bool,
}

#[async_trait]
pub trait Provider: Send + Sync {
    fn name(&self) -> &str;
    
    fn capabilities(&self) -> Capabilities;

    #[instrument(skip(self, ctx), fields(provider_id = %ctx.provider_id, query = %query))]
    async fn search(&self, ctx: &ProviderContext, query: &str) -> Result<Vec<SoulSyncTrack>, SoulSyncError> {
        unimplemented!("Provider::search")
    }

    #[instrument(skip(self, ctx), fields(provider_id = %ctx.provider_id))]
    async fn download(&self, ctx: &ProviderContext, track: &SoulSyncTrack) -> Result<crate::download_manager::DownloadStatus, SoulSyncError> {
         Err(SoulSyncError::ProviderError("Download not implemented".to_string()))
    }
}

pub trait ProviderFactory: Send + Sync {
    fn id(&self) -> &str;
    fn description(&self) -> &str;
    fn new_provider(&self, ctx: ProviderContext) -> Box<dyn Provider>;
}
