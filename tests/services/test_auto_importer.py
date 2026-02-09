import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from services.auto_importer import AutoImportService
from core.enums import Capability

class TestAutoImporter(unittest.TestCase):

    @patch('services.auto_importer.get_metadata_enhancer')
    @patch('core.settings.config_manager.get')
    @patch('services.auto_importer.AutoImportService._move_file')
    @patch('services.auto_importer.AutoImportService._cleanup_empty_directories')
    def test_workflow_high_confidence(self, mock_cleanup, mock_move, mock_config, mock_get_enhancer):
        """Test the full auto import workflow (High Confidence + Auto Import)"""

        # Mock Enhancer
        mock_enhancer_instance = MagicMock()
        mock_get_enhancer.return_value = mock_enhancer_instance

        # Mock Identify return: Metadata + 95% confidence
        mock_enhancer_instance.identify_file.return_value = (
            {"title": "Test Title", "artist": "Test Artist"},
            0.95
        )

        service = AutoImportService()

        # Mock config: Auto Import ON, threshold 90
        mock_config.return_value = {"auto_import": True, "enabled": True, "confidence_threshold": 90}

        # Run process
        test_file = Path("/tmp/test.mp3")
        with patch.object(Path, 'exists', return_value=True):
            service.process_batch([test_file])

        # Verify calls
        mock_enhancer_instance.identify_file.assert_called_with(test_file)

        # Should Call Tag (on enhancer)
        mock_enhancer_instance.tag_file.assert_called()

        # Should Call Move (internal)
        mock_move.assert_called()

        # Should Update Review Task (Approved)
        mock_enhancer_instance.create_or_update_review_task.assert_called_with(
            test_file,
            {"title": "Test Title", "artist": "Test Artist"},
            0.95,
            status='approved'
        )

    @patch('services.auto_importer.get_metadata_enhancer')
    @patch('core.settings.config_manager.get')
    @patch('services.auto_importer.AutoImportService._move_file')
    def test_workflow_low_confidence(self, mock_move, mock_config, mock_get_enhancer):
        """Test workflow with Low Confidence (should review)"""

        mock_enhancer_instance = MagicMock()
        mock_get_enhancer.return_value = mock_enhancer_instance

        # Mock Identify return: Metadata + 50% confidence
        mock_enhancer_instance.identify_file.return_value = (
            {"title": "Test Title"},
            0.50
        )

        service = AutoImportService()

        # Mock config: Auto Import ON, threshold 90
        mock_config.return_value = {"auto_import": True, "enabled": True, "confidence_threshold": 90}

        # Run process
        test_file = Path("/tmp/test.mp3")
        with patch.object(Path, 'exists', return_value=True):
            service.process_batch([test_file])

        # Verify calls
        mock_enhancer_instance.tag_file.assert_not_called()
        mock_move.assert_not_called()

        # Should Update Review Task (Pending)
        mock_enhancer_instance.create_or_update_review_task.assert_called_with(
            test_file,
            {"title": "Test Title"},
            0.50,
            status='pending'
        )

if __name__ == '__main__':
    unittest.main()
