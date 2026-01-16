#[cfg(test)]
mod tests {
    use crate::parser::TrackParser;
    use crate::matching::MatchingEngine;
    use crate::structs::SoulSyncTrack;
    use std::collections::HashMap;

    #[test]
    fn test_parser_cleaning() {
        // [320kbps] at end might be removed by remove_quality_markers, leaving [], which remove_junk should handle
        let title = "My Song (Radio Edit) [320kbps]";
        let metadata = TrackParser::clean_metadata(title, "Artist", "Album");
        assert_eq!(metadata.title, "My Song");
        assert_eq!(metadata.edition, Some("Radio Edit".to_string()));
        assert!(metadata.quality_tags.contains(&"MP3_320KBPS".to_string()));
    }

    #[test]
    fn test_filename_parsing() {
        let filename = "Artist - Song Title (Remix).mp3";
        let metadata = TrackParser::parse_filename(filename); // No unwrap, now returns struct
        assert_eq!(metadata.artist, "Artist");
        assert_eq!(metadata.title, "Song Title");
        assert_eq!(metadata.edition, Some("Remix".to_string()));
    }

    #[test]
    fn test_filename_parsing_fallback() {
        // Use [FLAC] for quality tag test as discussed in plan
        let filename = "Just A Title (Live) [FLAC].flac";
        let metadata = TrackParser::parse_filename(filename);
        assert_eq!(metadata.title, "Just A Title");
        assert_eq!(metadata.artist, "Unknown");
        assert_eq!(metadata.edition, Some("Live".to_string()));
        assert!(metadata.quality_tags.contains(&"FLAC_16BIT".to_string()) || metadata.quality_tags.contains(&"FLAC_24BIT".to_string()));
    }

    #[test]
    fn test_matching_engine() {
        let source_title = "My Song";
        let source_artist = "My Artist";
        let source = SoulSyncTrack {
             raw_title: source_title.to_string(),
             artist_name: source_artist.to_string(),
             album_title: "Album".to_string(),
             title: source_title.to_string(),
             edition: None,
             sort_title: None,
             display_title: source_title.to_string(),
             artist_sort_name: None,
             album_sort_title: None,
             album_type: None,
             album_release_group_id: None,
             duration: Some(180000),
             track_number: None,
             disc_number: None,
             bitrate: None,
             file_path: None,
             file_format: None,
             release_year: None,
             added_at: None,
             sample_rate: None,
             bit_depth: None,
             file_size_bytes: None,
             musicbrainz_id: None,
             isrc: None,
             acoustid_id: None,
             mb_release_id: None,
             original_release_date: None,
             fingerprint: None,
             quality_tags: None,
             identifiers: HashMap::new(),
        };

        let candidate_title = "My Song (Radio Edit)";
        let candidate = SoulSyncTrack {
             raw_title: candidate_title.to_string(),
             artist_name: source_artist.to_string(),
             album_title: "Album".to_string(),
             title: "My Song".to_string(),
             edition: Some("Radio Edit".to_string()),
             sort_title: None,
             display_title: candidate_title.to_string(),
             artist_sort_name: None,
             album_sort_title: None,
             album_type: None,
             album_release_group_id: None,
             duration: Some(181000), // Within 10s tolerance
             track_number: None,
             disc_number: None,
             bitrate: None,
             file_path: None,
             file_format: None,
             release_year: None,
             added_at: None,
             sample_rate: None,
             bit_depth: None,
             file_size_bytes: None,
             musicbrainz_id: None,
             isrc: None,
             acoustid_id: None,
             mb_release_id: None,
             original_release_date: None,
             fingerprint: None,
             quality_tags: Some(vec!["MP3_320KBPS".to_string()]),
             identifiers: HashMap::new(),
        };

        let result = MatchingEngine::calculate_match(&source, &candidate);
        println!("Match Result: {:?}", result);
        assert!(result.passed_version_check);
        assert!(result.confidence_score > 90.0);
    }
}
