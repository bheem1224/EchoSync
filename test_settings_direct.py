"""
Direct settings test - minimal imports
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_settings_import():
    print("\n" + "="*80)
    print("TESTING SETTINGS MODULE IMPORT")
    print("="*80 + "\n")
    
    try:
        # Import just the settings module without going through core.__init__
        print("Importing core.settings...")
        sys.path.insert(0, str(Path(__file__).parent))
        
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "settings", 
            Path(__file__).parent / "core" / "settings.py"
        )
        settings = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(settings)
        
        print("SUCCESS: Settings module loaded\n")
        
        # Get the config_manager instance
        config_mgr = settings.config_manager
        
        print("STORAGE PATHS FROM ConfigManager:")
        print("-" * 80)
        
        paths = config_mgr.get_storage_paths()
        for name, path in paths.items():
            exists = "[EXISTS]" if path.exists() else "[MISSING]"
            print(f"{name:20} {exists:10} {path}")
        
        print(f"\nmedia_db_path:       {config_mgr.media_db_path}")
        
        print("\n" + "="*80)
        print("TEST COMPLETE - All paths loaded successfully!")
        print("="*80 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_settings_import())
