import unittest
from core.path_mapper import PathMapper

class TestPathMapper(unittest.TestCase):
    def test_basic_mapping(self):
        mappings = [{"remote": "/data/media", "local": "/mnt/user/media"}]
        mapper = PathMapper(mappings)

        # Exact match
        self.assertEqual(mapper.map_to_local("/data/media"), "/mnt/user/media")

        # Prefix match
        self.assertEqual(mapper.map_to_local("/data/media/movies/film.mkv"), "/mnt/user/media/movies/film.mkv")

        # No match
        self.assertEqual(mapper.map_to_local("/other/path/file.txt"), "/other/path/file.txt")

    def test_windows_paths(self):
        mappings = [{"remote": "C:\\Media", "local": "/mnt/media"}]
        mapper = PathMapper(mappings)

        # Note: Input paths are normalized to forward slashes in output
        self.assertEqual(mapper.map_to_local("C:\\Media\\Movies\\Film.mkv"), "/mnt/media/Movies/Film.mkv")

        # Mixed separators
        self.assertEqual(mapper.map_to_local("C:/Media\\Movies/Film.mkv"), "/mnt/media/Movies/Film.mkv")

    def test_root_mapping(self):
        mappings = [{"remote": "/", "local": "/host_mnt"}]
        mapper = PathMapper(mappings)

        self.assertEqual(mapper.map_to_local("/etc/passwd"), "/host_mnt/etc/passwd")
        self.assertEqual(mapper.map_to_local("/"), "/host_mnt")

    def test_trailing_slashes(self):
        # Mapping with trailing slash on remote
        mappings = [{"remote": "/data/", "local": "/mnt/data"}]
        mapper = PathMapper(mappings)
        self.assertEqual(mapper.map_to_local("/data/file.txt"), "/mnt/data/file.txt")

        # Mapping with trailing slash on local
        mappings = [{"remote": "/data", "local": "/mnt/data/"}]
        mapper = PathMapper(mappings)
        self.assertEqual(mapper.map_to_local("/data/file.txt"), "/mnt/data/file.txt")

    def test_empty_mappings(self):
        mapper = PathMapper([])
        self.assertEqual(mapper.map_to_local("/any/path"), "/any/path")

    def test_normalization_only(self):
        mapper = PathMapper([])
        self.assertEqual(mapper.map_to_local("C:\\Users\\Name"), "C:/Users/Name")

    def test_multiple_mappings_order(self):
        # Order matters: first match wins
        mappings = [
            {"remote": "/data/music", "local": "/mnt/music"},
            {"remote": "/data", "local": "/mnt/data"}
        ]
        mapper = PathMapper(mappings)

        # Should match specific music mapping first
        self.assertEqual(mapper.map_to_local("/data/music/song.mp3"), "/mnt/music/song.mp3")

        # Should match general data mapping
        self.assertEqual(mapper.map_to_local("/data/other/file.txt"), "/mnt/data/other/file.txt")

    def test_case_sensitivity(self):
        # Currently implementation is case-sensitive (standard for Linux)
        mappings = [{"remote": "/Data", "local": "/mnt/data"}]
        mapper = PathMapper(mappings)

        self.assertEqual(mapper.map_to_local("/data/file.txt"), "/data/file.txt")
        self.assertEqual(mapper.map_to_local("/Data/file.txt"), "/mnt/data/file.txt")

if __name__ == '__main__':
    unittest.main()
