"""
TrackParser Service - Converts raw filenames/strings into SoulSyncTrack objects

This service handles:
1. Regex-based parsing of artist/title/version information
2. Quality tag extraction (FLAC, MP3 bitrates, etc.)
3. Compilation detection
4. Version/remix detection
5. Junk character removal and normalization
6. Audio fingerprint generation from local files
"""

import re
from typing import Optional, List, Dict, Set
from dataclasses import dataclass
from pathlib import Path
from core.matching_engine.soul_sync_track import SoulSyncTrack, QualityTag
from core.matching_engine.fingerprinting import FingerprintGenerator, FingerprintCache


@dataclass
class ParseConfig:
    """Configuration for track parsing behavior"""
    remove_junk_chars: bool = True
    extract_quality_tags: bool = True
    detect_compilation: bool = True
    detect_version: bool = True
    normalize_text: bool = True
    case_sensitive: bool = False


class TrackParser:
    """Parser for converting raw filename/string input into SoulSyncTrack objects"""

    # Regex patterns for common filename formats
    PATTERNS = {
        # Artist - Title format (most common)
        'artist_title': re.compile(
            r'^(?P<artist>[^-]+?)\s*[-–]\s*(?P<title>.+?)(?:\s*\((?P<version>[^)]+)\))?$',
            re.IGNORECASE
        ),

        # Artist - Album - Title (Beatport/formal release)
        'artist_album_title': re.compile(
            r'^(?P<artist>[^-]+?)\s*[-–]\s*(?P<album>[^-]+?)\s*[-–]\s*(?P<title>.+?)(?:\s*\((?P<version>[^)]+)\))?$',
            re.IGNORECASE
        ),

        # Title (feat. Artist) format
        'feat_artist': re.compile(
            r'(?P<title>.+?)\s+(?:feat\.?|ft\.?|featuring)\s+(?P<feat_artist>.+?)(?:\s*\((?P<version>[^)]+)\))?$',
            re.IGNORECASE
        ),

        # Remix/Version detection
        'version': re.compile(
            r'\b(?:remix|rmx|mix|version|ver\.?|edit|extended|instrumental|acapella|remix|bootleg|cover|remaster|remastered|remix|mix|version|original|club|radio|house|deep|progressive)\b',
            re.IGNORECASE
        ),

        # Compilation artist detection
        'compilation': re.compile(
            r'\b(?:various|various artists|va|compilation|comp|multi-artist|soundtrack|ost|[Vv]arious [Aa]rtists?)\b',
            re.IGNORECASE
        ),

        # Quality tag patterns
        'quality_flac': re.compile(r'\bFLAC\b|\b(?:24[-_]?bit|16[-_]?bit|lossless)\b', re.IGNORECASE),
        'quality_mp3_320': re.compile(r'\b(?:320|MP3[-_]?320|320kbps|320k)\b', re.IGNORECASE),
        'quality_mp3_256': re.compile(r'\b(?:256|MP3[-_]?256|256kbps|256k)\b', re.IGNORECASE),
        'quality_mp3_192': re.compile(r'\b(?:192|MP3[-_]?192|192kbps|192k)\b', re.IGNORECASE),
        'quality_aac': re.compile(r'\b(?:AAC|M4A|iTunes|256 AAC|AAC[-_]?256)\b', re.IGNORECASE),
        'quality_alac': re.compile(r'\bALAC\b', re.IGNORECASE),
        'quality_ogg': re.compile(r'\b(?:OGG|Vorbis|OGG[-_]?V)\b', re.IGNORECASE),
        'quality_opus': re.compile(r'\bOpus\b', re.IGNORECASE),
        'quality_wma': re.compile(r'\bWMA\b', re.IGNORECASE),

        # Bitrate patterns
        'bitrate': re.compile(r'\b(\d{2,3})\s*(?:kbps|k)\b', re.IGNORECASE),

        # Duration patterns (MM:SS or HH:MM:SS format)
        'duration': re.compile(r'\b(?:(\d{1,2}):(\d{2}):(\d{2})|(\d{1,2}):(\d{2}))\b'),

        # Junk patterns to remove
        'junk': re.compile(
            r'\b(?:www\d+|320|192|256|FLAC|MP3|AAC|OGG|WAV|m4a|flac|mp3|aac|ogg|wav)[\.\s]*$|'
            r'^\[.*?\]|'  # [brackets]
            r'{.*?}|'     # {braces}
            r'<.*?>|'     # <angle brackets>
            r'_+|'         # underscores
            r'~.*?~',     # ~tildes~
            re.IGNORECASE
        ),

        # Artist aliases (e.g., "Feat." variations)
        'feat_separators': re.compile(
            r'\s+(?:featuring|feat\.?|ft\.?|with|feat|f\.?)\s+',
            re.IGNORECASE
        ),

        # Disk/Track number patterns
        'track_number': re.compile(r'^(?:(?P<disc>\d+)[.-])?(?P<track>\d{1,2})[\s.-]', re.IGNORECASE),

        # Year patterns
        'year': re.compile(r'\((?P<year>19\d{2}|20\d{2})\)|\[(?P<year_bracket>19\d{2}|20\d{2})\]', re.IGNORECASE),

        # Parenthetical content (version/edition info)
        'parenthetical': re.compile(r'\s*\(([^)]+)\)\s*', re.IGNORECASE),
    }

    def __init__(self, config: Optional[ParseConfig] = None):
        """Initialize parser with optional configuration"""
        self.config = config or ParseConfig()
        self.fingerprint_cache: Optional[FingerprintCache] = None

    def set_fingerprint_cache(self, database_path: str):
        """Set the database path for fingerprint caching"""
        self.fingerprint_cache = FingerprintCache(database_path)

    def parse_filename(self, raw_string: str) -> Optional[SoulSyncTrack]:
        """
        Parse a raw filename/string into a SoulSyncTrack object

        Args:
            raw_string: Raw filename or track description

        Returns:
            SoulSyncTrack object if parsing succeeds, None otherwise
        """
        if not raw_string or not isinstance(raw_string, str):
            return None

        # Clean input
        working_string = raw_string.strip()
        if not working_string:
            return None

        # Extract year early (don't remove yet)
        year = self._extract_year(working_string)

        # Extract track/disk numbers
        track_number, disc_number = self._extract_track_numbers(working_string)

        # Extract quality tags BEFORE removing junk (since junk removal removes brackets)
        quality_tags = []
        if self.config.extract_quality_tags:
            quality_tags = self._extract_quality_tags(working_string)
            # Remove quality info for cleaner parsing
            working_string = self._remove_quality_markers(working_string)

        # Remove junk before parsing
        if self.config.remove_junk_chars:
            working_string = self._remove_junk(working_string)

        # Extract version/remix info
        version = None
        if self.config.detect_version:
            version = self._extract_version(working_string)
            # Remove version parentheticals but keep version string
            working_string = self._remove_parenthetical_versions(working_string)

        # Try different parsing patterns
        parsed_data = self._try_parse_patterns(working_string)
        if not parsed_data:
            return None

        # Detect if compilation
        is_compilation = False
        if self.config.detect_compilation:
            is_compilation = self._is_compilation(parsed_data.get('artist', ''))

        # Normalize text if requested
        if self.config.normalize_text:
            parsed_data = self._normalize_parsed_data(parsed_data)

        # Build SoulSyncTrack
        try:
            track = SoulSyncTrack(
                raw_title=parsed_data.get('title', ''),
                artist_name=parsed_data.get('artist', ''),
                album_title=parsed_data.get('album', ''),
                edition=None,
                release_year=year,
                track_number=track_number,
                disc_number=disc_number,
                quality_tags=quality_tags,
                is_compilation=is_compilation,
                version=version,
            )

            return track

        except Exception as e:
            print(f"Error creating SoulSyncTrack: {e}")
            return None

    def _try_parse_patterns(self, working_string: str) -> Optional[Dict[str, str]]:
        """Try each parsing pattern in order"""
        # Remove file extensions
        clean_string = re.sub(r'\.(mp3|flac|m4a|aac|ogg|wav|wma)$', '', working_string, flags=re.IGNORECASE)

        # Try artist-album-title pattern first
        match = self.PATTERNS['artist_album_title'].search(clean_string)
        if match:
            return match.groupdict()

        # Try artist-title pattern
        match = self.PATTERNS['artist_title'].search(clean_string)
        if match:
            return match.groupdict()

        # Try feat artist pattern
        match = self.PATTERNS['feat_artist'].search(clean_string)
        if match:
            data = match.groupdict()
            # Feat artist becomes featured artist (not main artist)
            return data

        return None

    def _extract_quality_tags(self, text: str) -> List[str]:
        """Extract quality tags from text"""
        tags = []

        if self.PATTERNS['quality_flac'].search(text):
            # Distinguish 24bit vs 16bit FLAC
            if re.search(r'\b24[-_]?bit\b', text, re.IGNORECASE):
                tags.append(QualityTag.FLAC_24BIT.value)
            else:
                tags.append(QualityTag.FLAC_16BIT.value)

        elif self.PATTERNS['quality_aac'].search(text):
            tags.append(QualityTag.AAC.value)
        elif self.PATTERNS['quality_alac'].search(text):
            tags.append(QualityTag.ALAC.value)
        elif self.PATTERNS['quality_mp3_320'].search(text):
            tags.append(QualityTag.MP3_320KBPS.value)
        elif self.PATTERNS['quality_mp3_256'].search(text):
            tags.append(QualityTag.MP3_256KBPS.value)
        elif self.PATTERNS['quality_mp3_192'].search(text):
            tags.append(QualityTag.MP3_192KBPS.value)
        elif self.PATTERNS['quality_ogg'].search(text):
            tags.append(QualityTag.OGG_VORBIS.value)
        elif self.PATTERNS['quality_opus'].search(text):
            tags.append(QualityTag.OPUS.value)

        return tags

    def _remove_quality_markers(self, text: str) -> str:
        """Remove quality markers from text"""
        text = re.sub(r'\b(?:FLAC|MP3|AAC|OGG|ALAC|Opus|WMA)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(?:24[-_]?bit|16[-_]?bit|lossless|320kbps|256kbps|192kbps|320k|256k|192k)\b', '', text, flags=re.IGNORECASE)
        return text.strip()

    def _extract_version(self, text: str) -> Optional[str]:
        """Extract version/remix information"""
        # Look for parenthetical first (highest priority)
        match = self.PATTERNS['parenthetical'].search(text)
        if match:
            version_candidate = match.group(1).strip()
            if self.PATTERNS['version'].search(version_candidate):
                return version_candidate

        # Look for inline version keywords
        match = self.PATTERNS['version'].search(text)
        if match:
            # Extract the phrase around the match
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            phrase = text[start:end].strip()
            # Clean up the phrase
            phrase = re.sub(r'[()[\]{}<>]', '', phrase)
            return phrase if len(phrase) < 100 else None

        return None

    def _remove_parenthetical_versions(self, text: str) -> str:
        """Remove parenthetical content that contains version keywords"""
        def replace_if_version(match):
            content = match.group(1)
            if self.PATTERNS['version'].search(content):
                return ''  # Remove this parenthetical
            return match.group(0)  # Keep it

        return self.PATTERNS['parenthetical'].sub(replace_if_version, text)

    def _extract_year(self, text: str) -> Optional[int]:
        """Extract year from text"""
        match = self.PATTERNS['year'].search(text)
        if match:
            year_str = match.group('year') or match.group('year_bracket')
            try:
                return int(year_str)
            except (ValueError, TypeError):
                pass
        return None

    def _extract_track_numbers(self, text: str) -> tuple[Optional[int], Optional[int]]:
        """Extract track and disc numbers"""
        match = self.PATTERNS['track_number'].search(text)
        if match:
            disc = match.group('disc')
            track = match.group('track')
            return (int(track) if track else None, int(disc) if disc else None)
        return None, None

    def _is_compilation(self, artist: str) -> bool:
        """Detect if this is a compilation (multiple artists)"""
        if not artist:
            return False

        # Check compilation keywords
        if self.PATTERNS['compilation'].search(artist):
            return True

        # Check for multiple artist separators (;, &, feat., etc.)
        if re.search(r'[;&]|feat\.|ft\.|and|with', artist, re.IGNORECASE):
            return True

        return False

    def _remove_junk(self, text: str) -> str:
        """Remove junk characters and markers"""
        # Remove common junk patterns
        text = re.sub(r'\[.*?\]', '', text)  # [brackets]
        text = re.sub(r'{.*?}', '', text)    # {braces}
        text = re.sub(r'<.*?>', '', text)    # <angle brackets>
        text = re.sub(r'_+', ' ', text)      # underscores to spaces
        text = re.sub(r'~.*?~', '', text)    # ~tildes~

        # Remove common extensions/markers at end
        text = re.sub(r'\s*(?:www\d+|320|192|256)[\.\s]*$', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(?:mp3|flac|m4a|aac|ogg|wav|wma)$', '', text, flags=re.IGNORECASE)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _normalize_parsed_data(self, data: Dict[str, str]) -> Dict[str, str]:
        """Normalize parsed data (case, whitespace, etc.)"""
        for key in ('artist', 'title', 'album', 'version'):
            if key in data and data[key]:
                # Normalize whitespace
                data[key] = ' '.join(data[key].split())
                # Title case for artist and album, keep title as-is
                if key == 'artist':
                    data[key] = data[key].title() if not self.config.case_sensitive else data[key]
                elif key == 'album':
                    data[key] = data[key].title() if not self.config.case_sensitive else data[key]

        return data


def parse_track(raw_string: str, config: Optional[ParseConfig] = None) -> Optional[SoulSyncTrack]:
    """Convenience function to parse a track with default settings"""
    parser = TrackParser(config)
    return parser.parse_filename(raw_string)

def parse_file(file_path: str, config: Optional[ParseConfig] = None, generate_fingerprint: bool = True) -> Optional[SoulSyncTrack]:
    """
    Parse a file path and optionally generate fingerprint

    Args:
        file_path: Path to audio file
        config: Optional parse configuration
        generate_fingerprint: Whether to generate Chromaprint fingerprint

    Returns:
        SoulSyncTrack with parsed metadata and optional fingerprint
    """
    parser = TrackParser(config)
    
    # Parse the filename
    track = parser.parse_filename(str(file_path))
    if not track:
        return None

    # Generate fingerprint if requested and file exists
    if generate_fingerprint and Path(file_path).exists():
        fingerprint = FingerprintGenerator.generate(file_path)
        if fingerprint:
            track.fingerprint = fingerprint
            track.fingerprint_confidence = 1.0  # Assume full confidence if generation succeeds

    return track