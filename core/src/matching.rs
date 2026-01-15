use crate::structs::SoulSyncTrack;

pub struct MatchingEngine;

impl MatchingEngine {
    pub fn compare(target: &SoulSyncTrack, candidate: &SoulSyncTrack) -> f64 {
        // stub implementation for compilation
        if target.raw_title == candidate.raw_title {
            1.0
        } else {
            0.5
        }
    }
}
