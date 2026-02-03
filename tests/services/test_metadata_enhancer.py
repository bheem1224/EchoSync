import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from core.enums import Capability
from core.provider import ProviderRegistry
from core.provider_base import ProviderBase
from providers.acoustid.client import AcoustIDProvider
from providers.musicbrainz.client import MusicBrainzProvider
from services.metadata_enhancer import MetadataEnhancerService

class TestMetadataPipeline(unittest.TestCase):
    def setUp(self):
        # Reset registry for testing
        ProviderRegistry._providers = {}
        ProviderRegistry._provider_sources = {}

        # Register providers manually for test
        ProviderRegistry.register(AcoustIDProvider)
        ProviderRegistry.register(MusicBrainzProvider)

    def test_provider_capabilities(self):
        """Test that providers are registered with correct capabilities"""
        acoustid_providers = ProviderRegistry.get_providers_with_capability(Capability.RESOLVE_FINGERPRINT)
        self.assertEqual(len(acoustid_providers), 1)
        self.assertIsInstance(acoustid_providers[0], AcoustIDProvider)

        mb_providers = ProviderRegistry.get_providers_with_capability(Capability.FETCH_METADATA)
        self.assertEqual(len(mb_providers), 1)
        self.assertIsInstance(mb_providers[0], MusicBrainzProvider)

    def test_acoustid_resolve(self):
        """Test AcoustID resolution logic"""
        provider = AcoustIDProvider()
        # Mock http response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "ok",
            "results": [{
                "recordings": [{"id": "mbid-123"}]
            }]
        }
        provider.http.get = MagicMock(return_value=mock_resp)
        provider._get_api_key = MagicMock(return_value="test-key")

        mbids = provider.resolve_fingerprint("fingerprint", 120)
        self.assertEqual(mbids, ["mbid-123"])

    def test_musicbrainz_metadata(self):
        """Test MusicBrainz metadata fetching"""
        provider = MusicBrainzProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "mbid-123",
            "title": "Test Title",
            "artist-credit": [{"name": "Test Artist"}],
            "releases": [{
                "title": "Test Album",
                "id": "rel-123",
                "date": "2023",
                "status": "Official",
                "media": [{
                    "position": 1,
                    "tracks": [{
                        "number": "5",
                        "recording": {"id": "mbid-123"}
                    }]
                }]
            }]
        }
        provider.http.get = MagicMock(return_value=mock_resp)

        meta = provider.get_metadata("mbid-123")
        self.assertEqual(meta['title'], "Test Title")
        self.assertEqual(meta['artist'], "Test Artist")
        self.assertEqual(meta['album'], "Test Album")
        self.assertEqual(meta['release_id'], "rel-123")
        self.assertEqual(meta['track_number'], "5")
        self.assertEqual(meta['disc_number'], 1)

    @patch('services.metadata_enhancer.MetadataEnhancerService._get_provider')
    @patch('services.metadata_enhancer.FingerprintGenerator.generate')
    @patch('services.metadata_enhancer.MetadataEnhancerService._get_audio_duration')
    @patch('services.metadata_enhancer.MetadataEnhancerService._tag_file')
    @patch('services.metadata_enhancer.MetadataEnhancerService._move_file')
    @patch('services.metadata_enhancer.MetadataEnhancerService._create_review_task')
    @patch('core.settings.config_manager.get')
    def test_enhancer_workflow(self, mock_config, mock_review, mock_move, mock_tag, mock_duration, mock_fp, mock_get_provider):
        """Test the full enhancer workflow (High Confidence + Auto Import)"""
        service = MetadataEnhancerService()

        # Mock config: Auto Import ON
        mock_config.return_value = {"auto_import": True, "enabled": True}

        # Mock providers
        mock_fp_provider = MagicMock()
        mock_fp_provider.resolve_fingerprint.return_value = ["mbid-123"]

        mock_mb_provider = MagicMock()
        mock_mb_provider.get_metadata.return_value = {
            "title": "Test Title", "artist": "Test Artist", "album": "Test Album",
            "track_number": "5"
        }

        # Configure provider retrieval (using plugin_loader.get_provider style)
        def get_provider_side_effect(capability):
            if capability == Capability.RESOLVE_FINGERPRINT:
                return mock_fp_provider
            if capability == Capability.FETCH_METADATA:
                return mock_mb_provider
            return None
        mock_get_provider.side_effect = get_provider_side_effect

        # Mock file info
        mock_fp.return_value = "fingerprint-data"
        mock_duration.return_value = 120

        # Run process
        test_file = Path("/tmp/test.mp3")
        with patch.object(Path, 'exists', return_value=True):
            service.process_batch([test_file])

        # Verify calls
        mock_fp.assert_called_with("/tmp/test.mp3")
        mock_fp_provider.resolve_fingerprint.assert_called_with("fingerprint-data", 120)
        mock_mb_provider.get_metadata.assert_called_with("mbid-123")

        # Should execute move/tag because confidence is high (AcoustID match) and auto_import is ON
        mock_tag.assert_called()
        mock_move.assert_called()
        mock_review.assert_not_called()

    @patch('services.metadata_enhancer.MetadataEnhancerService._get_provider')
    @patch('services.metadata_enhancer.FingerprintGenerator.generate')
    @patch('services.metadata_enhancer.MetadataEnhancerService._get_audio_duration')
    @patch('services.metadata_enhancer.MetadataEnhancerService._tag_file')
    @patch('services.metadata_enhancer.MetadataEnhancerService._move_file')
    @patch('services.metadata_enhancer.MetadataEnhancerService._create_review_task')
    @patch('core.settings.config_manager.get')
    def test_enhancer_workflow_low_confidence(self, mock_config, mock_review, mock_move, mock_tag, mock_duration, mock_fp, mock_get_provider):
        """Test workflow with Auto-Import OFF (should review)"""
        service = MetadataEnhancerService()

        # Mock config: Auto import OFF
        mock_config.return_value = {"auto_import": False, "enabled": True}

        # Mock providers (Same setup, high confidence match found)
        mock_fp_provider = MagicMock()
        mock_fp_provider.resolve_fingerprint.return_value = ["mbid-123"]
        mock_mb_provider = MagicMock()
        mock_mb_provider.get_metadata.return_value = {"title": "Test"}

        mock_get_provider.side_effect = lambda cap: mock_fp_provider if cap == Capability.RESOLVE_FINGERPRINT else mock_mb_provider

        mock_fp.return_value = "fp"
        mock_duration.return_value = 120

        test_file = Path("/tmp/test.mp3")
        with patch.object(Path, 'exists', return_value=True):
            service.process_batch([test_file])

        # Verify: Should NOT move/tag, should create review task
        mock_tag.assert_not_called()
        mock_move.assert_not_called()
        mock_review.assert_called()

if __name__ == '__main__':
    unittest.main()
