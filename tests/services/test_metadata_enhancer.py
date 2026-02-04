import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from core.enums import Capability
from core.provider import ProviderRegistry
from providers.acoustid.client import AcoustIDProvider
from providers.musicbrainz.client import MusicBrainzProvider
from services.metadata_enhancer import MetadataEnhancerService

class TestMetadataEnhancer(unittest.TestCase):
    def setUp(self):
        # Reset registry for testing
        ProviderRegistry._providers = {}
        ProviderRegistry._provider_sources = {}
        ProviderRegistry.register(AcoustIDProvider)
        ProviderRegistry.register(MusicBrainzProvider)

    @patch('services.metadata_enhancer.MetadataEnhancerService._get_provider')
    @patch('services.metadata_enhancer.FingerprintGenerator.generate')
    @patch('services.metadata_enhancer.MetadataEnhancerService._get_audio_duration')
    def test_identify_file_success(self, mock_duration, mock_fp, mock_get_provider):
        """Test identify_file with successful fingerprint resolution"""
        service = MetadataEnhancerService()

        # Mock providers
        mock_fp_provider = MagicMock()
        mock_fp_provider.resolve_fingerprint.return_value = ["mbid-123"]

        mock_mb_provider = MagicMock()
        mock_mb_provider.get_metadata.return_value = {
            "title": "Test Title", "artist": "Test Artist"
        }

        def get_provider_side_effect(capability):
            if capability == Capability.RESOLVE_FINGERPRINT:
                return mock_fp_provider
            if capability == Capability.FETCH_METADATA:
                return mock_mb_provider
            return None
        mock_get_provider.side_effect = get_provider_side_effect

        mock_fp.return_value = "fingerprint-data"
        mock_duration.return_value = 120

        test_file = Path("/tmp/test.mp3")

        # Act
        metadata, confidence = service.identify_file(test_file)

        # Assert
        self.assertEqual(confidence, 0.95)
        self.assertEqual(metadata['title'], "Test Title")

        mock_fp_provider.resolve_fingerprint.assert_called_with("fingerprint-data", 120)
        mock_mb_provider.get_metadata.assert_called_with("mbid-123")

    @patch('services.metadata_enhancer.MetadataEnhancerService._get_provider')
    @patch('services.metadata_enhancer.FingerprintGenerator.generate')
    @patch('services.metadata_enhancer.MetadataEnhancerService._get_audio_duration')
    def test_identify_file_fallback(self, mock_duration, mock_fp, mock_get_provider):
        """Test identify_file fallback to search when fingerprint fails"""
        service = MetadataEnhancerService()

        # Mock providers
        mock_fp_provider = MagicMock()
        mock_fp_provider.resolve_fingerprint.return_value = [] # No match

        mock_mb_provider = MagicMock()
        # Search returns a candidate
        mock_mb_provider.search_metadata.return_value = [{"mbid": "mbid-456", "score": 80}]
        mock_mb_provider.get_metadata.return_value = {"title": "Searched Title"}

        def get_provider_side_effect(capability):
            if capability == Capability.RESOLVE_FINGERPRINT:
                return mock_fp_provider
            if capability == Capability.FETCH_METADATA:
                return mock_mb_provider
            return None
        mock_get_provider.side_effect = get_provider_side_effect

        mock_fp.return_value = "fingerprint-data"
        mock_duration.return_value = 120
        test_file = Path("/tmp/test.mp3")

        # Act
        metadata, confidence = service.identify_file(test_file)

        # Assert
        self.assertEqual(confidence, 0.8) # 80/100
        self.assertEqual(metadata['title'], "Searched Title")

        # Verify search was called with filename sanitized
        # "test.mp3" -> stem "test"
        mock_mb_provider.search_metadata.assert_called()

if __name__ == '__main__':
    unittest.main()
