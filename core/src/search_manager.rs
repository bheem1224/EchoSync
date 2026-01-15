use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use crate::structs::SoulSyncTrack;
use crate::matching::MatchingEngine;
use std::cmp::Ordering;

#[pyclass]
pub struct SearchManager {
    match_threshold: f64,
}

#[pymethods]
impl SearchManager {
    #[new]
    #[pyo3(signature = (threshold=None))]
    pub fn new(threshold: Option<f64>) -> Self {
        Self {
            match_threshold: threshold.unwrap_or(0.8),
        }
    }

    pub fn select_best_match(
        &self,
        target: &SoulSyncTrack,
        candidates: Vec<SoulSyncTrack>,
    ) -> Option<SoulSyncTrack> {
        candidates
            .into_iter()
            .map(|candidate| {
                let score = MatchingEngine::compare(target, &candidate);
                (candidate, score)
            })
            .filter(|(_, score)| *score >= self.match_threshold)
            .max_by(|(_, score_a), (_, score_b)| {
                score_a.partial_cmp(score_b).unwrap_or(Ordering::Equal)
            })
            .map(|(candidate, _)| candidate)
    }

    pub fn filter_by_quality(
        &self,
        tracks: Vec<SoulSyncTrack>,
        profile: &Bound<'_, PyAny>,
    ) -> PyResult<Vec<SoulSyncTrack>> {
        let mut min_bitrate: Option<i32> = None;

        if let Ok(dict) = profile.downcast::<PyDict>() {
             if let Some(val) = dict.get_item("min_bitrate")? {
                 if !val.is_none() {
                     if let Ok(v) = val.extract::<i32>() {
                         min_bitrate = Some(v);
                     }
                 }
             }
        }

        let filtered = tracks
            .into_iter()
            .filter(|track| {
                if let Some(limit) = min_bitrate {
                    if let Some(br) = track.bitrate {
                         if br < limit {
                             return false;
                         }
                    } else {
                        // If track has no bitrate info, do we keep it?
                        // Usually safer to keep or strict to remove?
                        // "Filter out tracks that don't match basic bitrate requirements" implies if we don't know, it doesn't match?
                        // But for now, let's assume if it's missing we can't verify quality, so we might drop it?
                        // Or maybe we keep it.
                        // Let's go with strict for now: if limit is set, and bitrate is missing -> drop.
                        return false;
                    }
                }
                true
            })
            .collect();

        Ok(filtered)
    }
}
