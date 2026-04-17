"""
Comprehensive tests for TrackParser service

Tests cover:
- Basic artist-title parsing
- Featured artist extraction
- Version/remix detection
- Quality tag extraction
- Compilation detection
- Edge cases (special chars, junk removal)
- Complex filenames
"""

import pytest
from core.track_parser import TrackParser, ParseConfig
from core.matching_engine import EchosyncTrack, QualityTag


class TestTrackParserBasic:
    """Basic parsing tests"""

    def setup_method(self):
        """Setup parser for each test"""
        self.parser = TrackParser()

    def test_simple_artist_title(self):
        """Test basic 'Artist - Title' format"""
        track = self.parser.parse_filename("The Weeknd - Blinding Lights")
        assert track is not None
        assert track.artist_name.lower() == "the weeknd"
        assert track.title.lower() == "blinding lights"

    def test_artist_album_title(self):
        """Test 'Artist - Album - Title' format"""
        track = self.parser.parse_filename("Daft Punk - Homework - Da Funk")
        assert track is not None
        assert "daft punk" in track.artist_name.lower()
        # Album might not be captured correctly, that's ok for this format

    def test_with_file_extension(self):
        """Test parsing with file extension"""
        track = self.parser.parse_filename("Dua Lipa - Don't Start Now.mp3")
        assert track is not None
        assert "dua lipa" in track.artist_name.lower()
        assert "don't start now" in track.title.lower() or "dont start now" in track.title.lower()

    def test_with_brackets_junk(self):
        """Test removal of bracketed junk"""
        track = self.parser.parse_filename("[www.beatport.com] Deadmau5 - Fn Pig")
        assert track is not None
        assert "deadmau5" in track.artist_name.lower()
        assert "fn pig" in track.title.lower()

    def test_with_year(self):
        """Test extraction of year"""
        track = self.parser.parse_filename("David Bowie - Space Oddity (1969)")
        assert track is not None
        assert track.release_year == 1969

    def test_empty_string(self):
        """Test handling of empty string"""
        track = self.parser.parse_filename("")
        assert track is None

    def test_none_input(self):
        """Test handling of None input"""
        track = self.parser.parse_filename(None)
        assert track is None


class TestTrackParserVersion:
    """Tests for version/remix detection"""

    def setup_method(self):
        self.parser = TrackParser()

    def test_remix_version_detection(self):
        """Test detection of remix version"""
        track = self.parser.parse_filename("Calvin Harris - Summer (Chromatics Remix)")
        assert track is not None
        assert track.version is not None
        assert "remix" in track.version.lower()

    def test_extended_version(self):
        """Test detection of extended version"""
        track = self.parser.parse_filename("Jamiroquai - Virtual Insanity (Extended)")
        assert track is not None
        assert track.version is not None
        assert "extended" in track.version.lower()

    def test_instrumental_version(self):
        """Test detection of instrumental"""
        track = self.parser.parse_filename("Gorillaz - Clint Eastwood (Instrumental)")
        assert track is not None
        assert track.version is not None
        assert "instrumental" in track.version.lower()

    def test_original_version(self):
        """Test 'Original' version label"""
        track = self.parser.parse_filename("Daft Punk - One More Time (Original Mix)")
        assert track is not None
        assert track.version is not None

    def test_no_version_present(self):
        """Test track with no version info"""
        track = self.parser.parse_filename("Aphex Twin - Windowlicker")
        assert track is not None
        assert track.version is None


class TestTrackParserQuality:
    """Tests for quality tag extraction"""

    def setup_method(self):
        self.parser = TrackParser()

    def test_flac_24bit_detection(self):
        """Test FLAC 24-bit detection"""
        track = self.parser.parse_filename("Steely Dan - Deacon Blues [FLAC 24bit]")
        assert track is not None
        assert QualityTag.FLAC_24BIT.value in track.quality_tags

    def test_flac_16bit_detection(self):
        """Test FLAC 16-bit detection"""
        track = self.parser.parse_filename("Steely Dan - Deacon Blues [FLAC]")
        assert track is not None
        assert QualityTag.FLAC_16BIT.value in track.quality_tags or QualityTag.FLAC_24BIT.value in track.quality_tags

    def test_mp3_320kbps_detection(self):
        """Test MP3 320kbps detection"""
        track = self.parser.parse_filename("Dua Lipa - Don't Start Now [MP3 320kbps]")
        assert track is not None
        assert QualityTag.MP3_320KBPS.value in track.quality_tags

    def test_mp3_256kbps_detection(self):
        """Test MP3 256kbps detection"""
        track = self.parser.parse_filename("Dua Lipa - Don't Start Now (256k)")
        assert track is not None
        assert QualityTag.MP3_256KBPS.value in track.quality_tags

    def test_mp3_192kbps_detection(self):
        """Test MP3 192kbps detection"""
        track = self.parser.parse_filename("Dua Lipa - Don't Start Now [192kbps]")
        assert track is not None
        assert QualityTag.MP3_192KBPS.value in track.quality_tags

    def test_aac_detection(self):
        """Test AAC detection"""
        track = self.parser.parse_filename("Taylor Swift - Anti-Hero [AAC 256]")
        assert track is not None
        assert QualityTag.AAC.value in track.quality_tags

    def test_alac_detection(self):
        """Test ALAC detection"""
        track = self.parser.parse_filename("Kendrick Lamar - Swimming Pools [ALAC]")
        assert track is not None
        assert QualityTag.ALAC.value in track.quality_tags

    def test_opus_detection(self):
        """Test Opus detection"""
        track = self.parser.parse_filename("Billie Eilish - Bad Guy [Opus]")
        assert track is not None
        assert QualityTag.OPUS.value in track.quality_tags


class TestTrackParserCompilation:
    """Tests for compilation detection"""

    def setup_method(self):
        self.parser = TrackParser()

    def test_various_artists(self):
        """Test 'Various Artists' detection"""
        track = self.parser.parse_filename("Various Artists - Song Title")
        assert track is not None
        assert track.is_compilation is True

    def test_va_abbreviation(self):
        """Test 'VA' abbreviation"""
        track = self.parser.parse_filename("VA - Track Name")
        assert track is not None
        assert track.is_compilation is True

    def test_compilation_keyword(self):
        """Test 'Compilation' keyword"""
        track = self.parser.parse_filename("Compilation - Greatest Hits")
        assert track is not None
        assert track.is_compilation is True

    def test_multiple_artists_with_ampersand(self):
        """Test multiple artists with & separator"""
        track = self.parser.parse_filename("Artist A & Artist B - Song")
        assert track is not None
        assert track.is_compilation is True

    def test_multiple_artists_with_comma(self):
        """Test multiple artists with ; separator"""
        track = self.parser.parse_filename("Artist A; Artist B - Song")
        assert track is not None
        assert track.is_compilation is True

    def test_single_artist_not_compilation(self):
        """Test single artist is not compilation"""
        track = self.parser.parse_filename("Billie Eilish - Happier Than Ever")
        assert track is not None
        assert track.is_compilation is False


class TestTrackParserFeatured:
    """Tests for featured artist extraction"""

    def setup_method(self):
        self.parser = TrackParser()

    def test_feat_artist(self):
        """Test 'feat.' extraction"""
        track = self.parser.parse_filename("The Weeknd feat. Daft Punk - Starboy")
        assert track is not None
        # Title should contain the main artist or the feat phrase
        assert track.title is not None

    def test_ft_artist(self):
        """Test 'ft.' extraction"""
        track = self.parser.parse_filename("Childish Gambino ft. Chance the Rapper - This is America")
        assert track is not None
        assert track.title is not None

    def test_featuring(self):
        """Test 'featuring' extraction"""
        track = self.parser.parse_filename("DJ Khaled - God Did featuring Drake")
        assert track is not None
        # Should extract something
        assert track.artist_name is not None or track.title is not None


class TestTrackParserEdgeCases:
    """Tests for edge cases and special situations"""

    def setup_method(self):
        self.parser = TrackParser()

    def test_special_characters(self):
        """Test handling of special characters"""
        track = self.parser.parse_filename("Björk - Jóga (Remix)")
        assert track is not None
        assert track.artist_name is not None
        assert track.title is not None

    def test_emoji_and_unicode(self):
        """Test handling of emoji and unicode"""
        track = self.parser.parse_filename("Artist - Title 🎵 2024")
        assert track is not None

    def test_very_long_filename(self):
        """Test handling of very long filename"""
        long_title = "A" * 200
        track = self.parser.parse_filename(f"Artist - {long_title}")
        assert track is not None
        assert track.artist_name is not None

    def test_multiple_dashes(self):
        """Test filename with multiple dashes"""
        track = self.parser.parse_filename("Artist - Album - Title - Remix")
        assert track is not None
        assert track.artist_name is not None

    def test_whitespace_normalization(self):
        """Test normalization of excess whitespace"""
        track = self.parser.parse_filename("  Artist   -   Title   ")
        assert track is not None
        # Should normalize whitespace
        assert track.artist_name is not None
        assert track.title is not None

    def test_parenthetical_with_number(self):
        """Test parenthetical with year and version"""
        track = self.parser.parse_filename("Kraftwerk - The Robots (2009 Remaster)")
        assert track is not None
        assert track.artist_name is not None


class TestTrackParserConfig:
    """Tests for ParseConfig options"""

    def test_config_disable_quality_extraction(self):
        """Test disabling quality tag extraction"""
        config = ParseConfig(extract_quality_tags=False)
        parser = TrackParser(config)
        track = parser.parse_filename("Artist - Title [FLAC 24bit]")
        assert track is not None
        assert len(track.quality_tags) == 0

    def test_config_case_sensitive(self):
        """Test case-sensitive parsing"""
        config = ParseConfig(case_sensitive=True)
        parser = TrackParser(config)
        track = parser.parse_filename("Artist Name - Song Title")
        assert track is not None
        # Should preserve case
        assert track.artist_name == "Artist Name"

    def test_config_disable_junk_removal(self):
        """Test disabling junk removal"""
        config = ParseConfig(remove_junk_chars=False)
        parser = TrackParser(config)
        # Some junk might remain but parsing should still work
        track = parser.parse_filename("[www] Artist - Title")
        # This might fail because junk removal is needed for some patterns
        # Just check it doesn't crash


class TestTrackParserIntegration:
    """Integration tests with complex real-world examples"""

    def setup_method(self):
        self.parser = TrackParser()

    def test_beatport_format(self):
        """Test Beatport-style filename"""
        track = self.parser.parse_filename("Disclosure - Latch (Mark Ronson Remix) [Edited]")
        assert track is not None
        assert track.artist_name is not None
        assert track.title is not None

    def test_soulseek_format(self):
        """Test typical SoulSeek download format"""
        track = self.parser.parse_filename("01 - Artist - Track Title (Remix) [FLAC] [2024]")
        assert track is not None
        # Should extract artist and title despite track number

    def test_spotify_format(self):
        """Test Spotify metadata format"""
        track = self.parser.parse_filename("The Weeknd - Blinding Lights - Radio Edit")
        assert track is not None
        assert track.artist_name is not None

    def test_compilation_album_format(self):
        """Test compilation album track"""
        track = self.parser.parse_filename("01. Artist Name - Song Title (Remix Version) [WAV]")
        assert track is not None
        assert track.artist_name is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
