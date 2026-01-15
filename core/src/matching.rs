use pyo3::prelude::*;
use crate::structs::SoulSyncTrack;
use std::collections::HashSet;
use strsim::{jaro_winkler, levenshtein};
use once_cell::sync::Lazy;

// --- Constants (Weights) ---
#[allow(dead_code)]
const TITLE_WEIGHT: f64 = 0.6;
#[allow(dead_code)]
const ARTIST_WEIGHT: f64 = 0.3;
#[allow(dead_code)]
const ALBUM_WEIGHT: f64 = 0.1;
#[allow(dead_code)]
const DURATION_WEIGHT: f64 = 0.5; // Contribution to total score
#[allow(dead_code)]
const TEXT_WEIGHT: f64 = 0.5; // Contribution to total score
#[allow(dead_code)]
const QUALITY_BONUS: f64 = 0.05; // 5% bonus
#[allow(dead_code)]
const FINGERPRINT_WEIGHT: f64 = 1.0;

#[allow(dead_code)]
const DURATION_TOLERANCE_MS: i64 = 10000; // 10 seconds
#[allow(dead_code)]
const FUZZY_MATCH_THRESHOLD: f64 = 0.7;

#[allow(dead_code)]
const VERSION_MISMATCH_PENALTY: f64 = 0.5; // 50% penalty
#[allow(dead_code)]
const EDITION_MISMATCH_PENALTY: f64 = 0.3; // 30% penalty
#[allow(dead_code)]
const TEXT_MATCH_FALLBACK: f64 = 0.0;

#[allow(dead_code)]
static VERSION_KEYWORDS: Lazy<HashSet<&'static str>> = Lazy::new(|| {
    let mut s = HashSet::new();
    s.insert("remix"); s.insert("rmx"); s.insert("mix"); s.insert("edit");
    s.insert("extended"); s.insert("instrumental"); s.insert("acapella");
    s.insert("bootleg"); s.insert("cover"); s.insert("remaster");
    s.insert("remastered"); s.insert("original"); s.insert("club");
    s.insert("radio"); s.insert("house"); s.insert("deep");
    s.insert("progressive"); s.insert("version"); s.insert("ver");
    s.insert("alternative"); s.insert("alt"); s.insert("acoustic");
    s.insert("live");
    s
});

#[derive(Debug, Clone)]
pub struct MatchResult {
    pub confidence_score: f64, // 0.0 - 100.0
    pub passed_version_check: bool,
    pub passed_edition_check: bool,
    pub fuzzy_text_score: f64,
    pub duration_match_score: f64,
    pub quality_bonus_applied: f64,
    pub version_penalty_applied: f64,
    pub edition_penalty_applied: f64,
    pub reasoning: String,
}

pub struct WeightedMatchingEngine;

impl WeightedMatchingEngine {

    pub fn calculate_match(source: &SoulSyncTrack, candidate: &SoulSyncTrack) -> MatchResult {
        let mut score = 0.0;
        let mut max_possible_score = 0.0;
        let mut version_penalty = 0.0;
        let mut edition_penalty = 0.0;
        let mut quality_bonus = 0.0;
        let mut reasoning_parts = Vec::new();

        // 0. ISRC Match
        if let (Some(s_isrc), Some(c_isrc)) = (&source.isrc, &candidate.isrc) {
            if s_isrc.trim().to_uppercase() == c_isrc.trim().to_uppercase() {
                return MatchResult {
                    confidence_score: 100.0,
                    passed_version_check: true,
                    passed_edition_check: true,
                    fuzzy_text_score: 1.0,
                    duration_match_score: 1.0,
                    quality_bonus_applied: 0.0,
                    version_penalty_applied: 0.0,
                    edition_penalty_applied: 0.0,
                    reasoning: "ISRC match (identical recording - instant 100% confidence)".to_string(),
                };
            } else {
                reasoning_parts.push("ISRC available but no match".to_string());
            }
        }

        // 1. Version Check
        let (version_match, version_reason) = Self::check_version_match(source, candidate);
        if !version_match {
            version_penalty = VERSION_MISMATCH_PENALTY * 100.0;
            reasoning_parts.push(format!("Version mismatch: {} (-{:.1})", version_reason, version_penalty));
        } else {
            reasoning_parts.push(format!("Version match: {}", version_reason));
        }

        // 2. Edition Check
        let (edition_match, edition_reason) = Self::check_edition_match(source, candidate);
        if !edition_match {
            edition_penalty = EDITION_MISMATCH_PENALTY * 100.0;
             reasoning_parts.push(format!("Edition mismatch: {} (-{:.1})", edition_reason, edition_penalty));
        } else {
             reasoning_parts.push(format!("Edition match: {}", edition_reason));
        }

        // 3. Fuzzy Text Matching
        let fuzzy_score = Self::calculate_fuzzy_text_match(source, candidate);
        let text_contribution = fuzzy_score * TEXT_WEIGHT * 100.0;
        reasoning_parts.push(format!("Text match: {:.1}% x {:.1}% = {:.1} pts", fuzzy_score * 100.0, TEXT_WEIGHT * 100.0, text_contribution));

        if fuzzy_score < FUZZY_MATCH_THRESHOLD {
            reasoning_parts.push(format!("FAILED: Fuzzy score below threshold ({:.1}% < {:.1}%)", fuzzy_score * 100.0, FUZZY_MATCH_THRESHOLD * 100.0));
             return MatchResult {
                confidence_score: 0.0,
                passed_version_check: version_match,
                passed_edition_check: edition_match,
                fuzzy_text_score: fuzzy_score,
                duration_match_score: 0.0,
                quality_bonus_applied: 0.0,
                version_penalty_applied: version_penalty,
                edition_penalty_applied: edition_penalty,
                reasoning: reasoning_parts.join(" | "),
            };
        }
        score += text_contribution;
        max_possible_score += TEXT_WEIGHT * 100.0;

        // 4. Duration Matching
        let duration_score = Self::calculate_duration_match(source, candidate);
        let duration_contribution = duration_score * DURATION_WEIGHT * 100.0;
        reasoning_parts.push(format!("Duration match: {:.1}% x {:.1}% = {:.1} pts", duration_score * 100.0, DURATION_WEIGHT * 100.0, duration_contribution));

        score += duration_contribution;
        max_possible_score += DURATION_WEIGHT * 100.0;

        // 5. Quality Bonus
        if let Some(tags) = &candidate.quality_tags {
            if !tags.is_empty() {
                quality_bonus = QUALITY_BONUS * 100.0;
                score += quality_bonus;
                reasoning_parts.push(format!("Quality bonus: +{:.1} pts", quality_bonus));
            } else {
                 reasoning_parts.push("No quality tags".to_string());
            }
        } else {
             reasoning_parts.push("No quality tags".to_string());
        }
        max_possible_score += QUALITY_BONUS * 100.0;

        // Penalties
        let final_penalty = version_penalty + edition_penalty;
        score -= final_penalty;

        // Normalize
        let normalized_score = if max_possible_score > 0.0 {
            (score / max_possible_score) * 100.0
        } else {
            0.0
        };
        let final_score = normalized_score.clamp(0.0, 100.0);
        reasoning_parts.push(format!("FINAL SCORE: {:.1}/100", final_score));

        MatchResult {
            confidence_score: final_score,
            passed_version_check: version_match,
            passed_edition_check: edition_match,
            fuzzy_text_score: fuzzy_score,
            duration_match_score: duration_score,
            quality_bonus_applied: quality_bonus,
            version_penalty_applied: version_penalty,
            edition_penalty_applied: edition_penalty,
            reasoning: reasoning_parts.join(" | "),
        }
    }

    fn check_version_match(source: &SoulSyncTrack, candidate: &SoulSyncTrack) -> (bool, String) {
        if source.edition.is_none() && candidate.edition.is_none() {
            return (true, "Both have no version info".to_string());
        }
        if source.edition.is_none() {
             return (true, "Source has no version".to_string());
        }
        if candidate.edition.is_none() {
             return (true, "Candidate has no version".to_string());
        }

        let s_ver = source.edition.as_ref().unwrap().to_lowercase();
        let c_ver = candidate.edition.as_ref().unwrap().to_lowercase();

        if s_ver == c_ver {
            return (true, format!("Versions match: '{}'", s_ver));
        }

        let s_keys = Self::extract_version_keywords(&s_ver);
        let c_keys = Self::extract_version_keywords(&c_ver);

        if s_keys.is_empty() && c_keys.is_empty() {
            return (true, "Unrecognized version formats".to_string());
        }
        if s_keys.is_empty() || c_keys.is_empty() {
             return (false, format!("'{}' vs '{}'", s_ver, c_ver));
        }

        let intersection: Vec<_> = s_keys.intersection(&c_keys).collect();
        if !intersection.is_empty() {
            return (true, format!("Keywords match: {:?}", intersection));
        }

        if s_keys.contains("remix") != c_keys.contains("remix") {
            return (false, "One is remix, other is original".to_string());
        }

        (false, format!("Different versions: '{}' vs '{}'", s_ver, c_ver))
    }

    fn check_edition_match(source: &SoulSyncTrack, candidate: &SoulSyncTrack) -> (bool, String) {
        if let (Some(s_disc), Some(c_disc)) = (source.disc_number, candidate.disc_number) {
            if s_disc == c_disc {
                return (true, format!("Disc numbers match: {}", s_disc));
            } else {
                return (false, format!("Disc {} vs {}", s_disc, c_disc));
            }
        }
        (true, "No edition info".to_string())
    }

    fn calculate_fuzzy_text_match(source: &SoulSyncTrack, candidate: &SoulSyncTrack) -> f64 {
        let mut total_score = 0.0;
        let mut total_weight = 0.0;

        // Title
        let t1 = Self::normalize(&source.title);
        let t2 = Self::normalize(&candidate.title);
        if !t1.is_empty() && !t2.is_empty() {
            total_score += jaro_winkler(&t1, &t2) * TITLE_WEIGHT;
            total_weight += TITLE_WEIGHT;
        }

        // Artist
        let a1 = Self::normalize(&source.artist_name);
        let a2 = Self::normalize(&candidate.artist_name);
        if !a1.is_empty() && !a2.is_empty() {
            total_score += jaro_winkler(&a1, &a2) * ARTIST_WEIGHT;
            total_weight += ARTIST_WEIGHT;
        }

        // Album
        let al1 = Self::normalize(&source.album_title);
        let al2 = Self::normalize(&candidate.album_title);
        if !al1.is_empty() && !al2.is_empty() {
            total_score += jaro_winkler(&al1, &al2) * ALBUM_WEIGHT;
            total_weight += ALBUM_WEIGHT;
        }

        if total_weight == 0.0 {
            return TEXT_MATCH_FALLBACK;
        }

        total_score / total_weight
    }

    fn calculate_duration_match(source: &SoulSyncTrack, candidate: &SoulSyncTrack) -> f64 {
        if let (Some(d1), Some(d2)) = (source.duration, candidate.duration) {
            let diff = (d1 - d2).abs();
            if diff <= DURATION_TOLERANCE_MS {
                return 1.0 - (diff as f64 / DURATION_TOLERANCE_MS as f64) * 0.5;
            } else {
                return 0.0;
            }
        }
        1.0 // Assume match if duration missing
    }

    fn normalize(s: &str) -> String {
        s.to_lowercase().chars().filter(|c| c.is_alphanumeric() || c.is_whitespace()).collect::<String>()
    }

    fn extract_version_keywords(s: &str) -> HashSet<String> {
        let mut found = HashSet::new();
        for k in VERSION_KEYWORDS.iter() {
            if s.contains(k) {
                found.insert(k.to_string());
            }
        }
        found
    }
}
