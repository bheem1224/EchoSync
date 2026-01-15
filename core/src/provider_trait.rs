use crate::structs::SoulSyncTrack;
use crate::errors::SoulSyncError;

pub trait MusicProvider: Send + Sync {
    fn name(&self) -> &str;
    fn search(&self, query: &str) -> Result<Vec<SoulSyncTrack>, SoulSyncError>;
    fn get_track(&self, id: &str) -> Result<SoulSyncTrack, SoulSyncError>;
    fn get_artist_top_tracks(&self, artist_id: &str) -> Result<Vec<SoulSyncTrack>, SoulSyncError>;
}
