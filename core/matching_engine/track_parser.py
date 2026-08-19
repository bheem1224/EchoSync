"""
TrackParser Service - Converts raw filenames/strings into EchosyncTrack objects

This service handles:
1. Regex-based parsing of artist/title/version information
2. Quality tag extraction (FLAC, MP3 bitrates, etc.)
3. Compilation detection
4. Version/remix detection
5. Junk character removal and normalization
6. Audio fingerprint generation from local files
"""

import re
import logging
from typing import Optional, List, Dict, Set, Any
from dataclasses import dataclass
from pathlib import Path
from ..db.echo_sync_track import EchosyncTrack, QualityTag
from .fingerprinting import FingerprintGenerator, FingerprintCache

logger = logging.getLogger(__name__)


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
    """Parser for converting raw filename/string input into EchosyncTrack objects"""

    # Regex patterns for common filename formats
    PATTERNS = {
        'extension_strip': re.compile(r'\.(mp3|flac|m4a|aac|ogg|wav|wma)$', re.IGNORECASE),
        'quality_marker_strip': re.compile(r'\b(?:FLAC|MP3|AAC|OGG|ALAC|Opus|WMA)\b', re.IGNORECASE),
        'bitrate_marker_strip': re.compile(r'\b(?:24[-_]?bit|16[-_]?bit|lossless|320kbps|256kbps|192kbps|320k|256k|192k)\b', re.IGNORECASE),
        'phrase_clean': re.compile(r'[()[\]{}<>]'),
        'brackets_clean': re.compile(r'\[.*?\]'),
        'braces_clean': re.compile(r'{.*?}'),
        'angle_brackets_clean': re.compile(r'<.*?>'),
        'underscores_clean': re.compile(r'_+'),
        'tildes_clean': re.compile(r'~.*?~'),
        'junk_extensions_clean': re.compile(r'\s*(?:www\d+|320|192|256)[\.\s]*$', re.IGNORECASE),
        'file_extensions_clean': re.compile(r'\b(?:mp3|flac|m4a|aac|ogg|wav|wma)$', re.IGNORECASE),
        'whitespace_clean': re.compile(r'\s+'),
        'extension_strip': re.compile(r'\.(mp3|flac|m4a|aac|ogg|wav|wma)$', re.IGNORECASE),
        'quality_marker_strip': re.compile(r'(?:FLAC|MP3|AAC|OGG|ALAC|Opus|WMA)', re.IGNORECASE),
        'bitrate_marker_strip': re.compile(r'(?:24[-_]?bit|16[-_]?bit|lossless|320kbps|256kbps|192kbps|320k|256k|192k)', re.IGNORECASE),
        'phrase_clean': re.compile(r'[()[\]{}<>]'),
        'brackets_clean': re.compile(r'\[.*?\]'),
        'braces_clean': re.compile(r'{.*?}'),
        'angle_brackets_clean': re.compile(r'<.*?>'),
        'underscores_clean': re.compile(r'_+'),
        'tildes_clean': re.compile(r'~.*?~'),
        'junk_extensions_clean': re.compile(r'\s*(?:www\d+|320|192|256)[\.\s]*$', re.IGNORECASE),
        'file_extensions_clean': re.compile(r'(?:mp3|flac|m4a|aac|ogg|wav|wma)$', re.IGNORECASE),
        'whitespace_clean': re.compile(r'\s+'),
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

    def parse_filename(self_or_raw: Any, raw_string: Optional[str] = None) -> Optional[EchosyncTrack]:
        """
        Parse a raw filename or hierarchical path into a EchosyncTrack object.
        Supports being called as TrackParser.parse_filename(path) or parser.parse_filename(path).

        Args:
            self_or_raw: TrackParser instance or raw filename / file path string
            raw_string: Raw filename or track description / file path if called on instance

        Returns:
            EchosyncTrack object if parsing succeeds, None otherwise
        """
        if isinstance(self_or_raw, TrackParser):
            return self_or_raw._parse_filename_core(raw_string)
        elif isinstance(self_or_raw, (str, Path)):
            return TrackParser()._parse_filename_core(self_or_raw)
        else:
            target = raw_string if raw_string is not None else self_or_raw
            return TrackParser()._parse_filename_core(target)

    def _parse_filename_core(self, raw_string: Any) -> Optional[EchosyncTrack]:
        if raw_string is None:
            return None
        raw_string = str(raw_string)
        if not raw_string:
            return None

        # Clean input
        raw_clean = raw_string.strip()
        if not raw_clean:
            return None

        # Detect directory separators (/ or \)
        clean_path = raw_clean.replace('\\', '/')
        parts = [p.strip() for p in clean_path.split('/') if p.strip()]

        dir_artist = None
        dir_album = None
        if len(parts) >= 3:
            dir_artist = parts[-3]
            dir_album = parts[-2]
            filename_part = parts[-1]
        elif len(parts) == 2:
            dir_artist = parts[-2]
            filename_part = parts[-1]
        else:
            filename_part = parts[0]

        working_string = filename_part

        # Extract year early (check filename first, then directory album)
        year = self._extract_year(working_string) or (self._extract_year(dir_album) if dir_album else None)

        # Extract track/disk numbers
        track_number, disc_number = self._extract_track_numbers(working_string)

        # Extract quality tags
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

        # Remove leading track number prefixes (e.g. "01 - ", "01. ", "1-05 ", "01 ")
        clean_filename_part = re.sub(r'^(?:(?:\d+[.-])?\d{1,2}[\s.-]+)', '', working_string).strip()

        # Try different parsing patterns on clean_filename_part first
        parsed_data = self._try_parse_patterns(clean_filename_part)

        # If clean_filename_part didn't have artist-title pattern (e.g. title-only like "01 - Title.flac"),
        # and dir_artist is available, use dir_artist and clean_title
        if not parsed_data and dir_artist:
            clean_title = self.PATTERNS['extension_strip'].sub('', clean_filename_part or working_string).strip()
            if clean_title:
                parsed_data = {
                    'artist': dir_artist,
                    'album': dir_album or '',
                    'title': clean_title
                }

        # Otherwise fallback to parsing the uncleaned working_string if parsed_data is still None
        if not parsed_data:
            parsed_data = self._try_parse_patterns(working_string)

        if parsed_data:
            # If the parsed artist is purely digits (e.g. leftover track number), fallback to dir_artist
            parsed_artist = (parsed_data.get('artist') or '').strip()
            if re.match(r'^\d+$', parsed_artist) or not parsed_artist:
                if dir_artist:
                    parsed_data['artist'] = dir_artist
                else:
                    parsed_data = None
            if parsed_data and dir_album and not parsed_data.get('album'):
                parsed_data['album'] = dir_album

        if not parsed_data:
            return None

        # Detect if compilation
        is_compilation = False
        if self.config.detect_compilation:
            is_compilation = self._is_compilation(parsed_data.get('artist', ''))

        # Normalize text if requested
        if self.config.normalize_text:
            parsed_data = self._normalize_parsed_data(parsed_data)

        # Build EchosyncTrack
        try:
            album_title = parsed_data.get('album')
            if not album_title:
                album_title = ""

            track = EchosyncTrack(
                raw_title=parsed_data.get('title', ''),
                artist_name=parsed_data.get('artist', ''),
                album_title=album_title,
                release_year=year,
                edition=version,
                version=version,
                quality_tags=quality_tags,
                track_number=track_number,
                disc_number=disc_number,
                is_compilation=is_compilation,
                album_type='compilation' if is_compilation else None
            )

            # Validate the track
            if track.raw_title and track.artist_name:
                return track
            return None

        except Exception as e:
            logger.error(f"Error creating EchosyncTrack: {e}")
            return None

    def _try_parse_patterns(self, working_string: str) -> Optional[Dict[str, str]]:
        """Try each parsing pattern in order"""
        # Remove file extensions
        clean_string = self.PATTERNS['extension_strip'].sub('', working_string)

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

        # FLAC detection
        if self.PATTERNS['quality_flac'].search(text):
            # Distinguish 24bit vs 16bit FLAC
            if re.search(r'\b24[-_]?bit\b', text, re.IGNORECASE):
                tags.append(QualityTag.FLAC_24BIT.value)
            else:
                tags.append(QualityTag.FLAC_16BIT.value)

        # AAC detection (check before MP3 to avoid '256' matching MP3 when it's 'AAC 256')
        if self.PATTERNS['quality_aac'].search(text):
            tags.append(QualityTag.AAC.value)
        
        # MP3 detection
        elif self.PATTERNS['quality_mp3_320'].search(text):
            tags.append(QualityTag.MP3_320KBPS.value)
        elif self.PATTERNS['quality_mp3_256'].search(text):
            tags.append(QualityTag.MP3_256KBPS.value)
        elif self.PATTERNS['quality_mp3_192'].search(text):
            tags.append(QualityTag.MP3_192KBPS.value)
        
        # Other formats
        if self.PATTERNS['quality_alac'].search(text):
            tags.append(QualityTag.ALAC.value)
        if self.PATTERNS['quality_ogg'].search(text):
            tags.append(QualityTag.OGG_VORBIS.value)
        if self.PATTERNS['quality_opus'].search(text):
            tags.append(QualityTag.OPUS.value)

        return tags

    def _remove_quality_markers(self, text: str) -> str:
        """Remove quality markers from text"""
        text = self.PATTERNS['quality_marker_strip'].sub('', text)
        text = self.PATTERNS['bitrate_marker_strip'].sub('', text)
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
            phrase = self.PATTERNS['phrase_clean'].sub('', phrase)
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
        text = self.PATTERNS['brackets_clean'].sub('', text)  # [brackets]
        text = self.PATTERNS['braces_clean'].sub('', text)    # {braces}
        text = self.PATTERNS['angle_brackets_clean'].sub('', text)    # <angle brackets>
        text = self.PATTERNS['underscores_clean'].sub(' ', text)      # underscores to spaces
        text = self.PATTERNS['tildes_clean'].sub('', text)    # ~tildes~

        # Remove common extensions/markers at end
        text = self.PATTERNS['junk_extensions_clean'].sub('', text)
        text = self.PATTERNS['file_extensions_clean'].sub('', text)

        # Clean up whitespace
        text = self.PATTERNS['whitespace_clean'].sub(' ', text)
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


def parse_track(raw_string: str, config: Optional[ParseConfig] = None) -> Optional[EchosyncTrack]:
    """Convenience function to parse a track with default settings"""
    parser = TrackParser(config)
    return parser.parse_filename(raw_string)

def parse_file(file_path: str, config: Optional[ParseConfig] = None, generate_fingerprint: bool = True) -> Optional[EchosyncTrack]:
    """
    Parse a file path and optionally generate fingerprint

    Args:
        file_path: Path to audio file
        config: Optional parse configuration
        generate_fingerprint: Whether to generate Chromaprint fingerprint

    Returns:
        EchosyncTrack with parsed metadata and optional fingerprint
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