use moka::future::Cache;
use std::time::Duration;
use crate::structs::SoulSyncTrack;

/// A thread-safe, async cache for provider search results.
/// 
/// Keys are a tuple of (ProviderID, QueryString).
/// Values are a list of tracks.
/// 
/// Uses `moka` for high-performance concurrent access with TTL eviction.
#[derive(Clone)]
pub struct ProviderCache {
    inner: Cache<(String, String), Vec<SoulSyncTrack>>,
}

impl ProviderCache {
    /// Create a new cache with a default Time-To-Live (TTL).
    pub fn new(ttl_minutes: u64) -> Self {
        Self {
            inner: Cache::builder()
                // Max capacity (items), not bytes. Adjust as needed.
                .max_capacity(10_000) 
                // Evict items after they haven't been used for X time
                .time_to_idle(Duration::from_secs(ttl_minutes * 60))
                .build(),
        }
    }

    /// Retrieve results for a specific provider and query.
    pub async fn get(&self, provider_id: &str, query: &str) -> Option<Vec<SoulSyncTrack>> {
        let key = (provider_id.to_string(), query.to_string());
        self.inner.get(&key).await
    }

    /// Store results in the cache.
    pub async fn put(&self, provider_id: &str, query: &str, tracks: Vec<SoulSyncTrack>) {
        let key = (provider_id.to_string(), query.to_string());
        self.inner.insert(key, tracks).await;
    }

    /// Clear all items from the cache.
    pub async fn clear(&self) {
        self.inner.invalidate_all();
    }
}

// Default implementation for easy instantiation
impl Default for ProviderCache {
    fn default() -> Self {
        // Default to 60 minutes TTL
        Self::new(60)
    }
}