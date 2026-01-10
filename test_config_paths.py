"""
Test script to verify config directory changes are properly applied
"""
from core.settings import config_manager
from pathlib import Path

def test_config_paths():
    print("\n" + "="*70)
    print("TESTING CONFIG PATH APPLICATION")
    print("="*70 + "\n")
    
    # Get storage paths from config
    storage_config = config_manager.get('storage', {})
    
    print("1. Config file storage settings:")
    print(f"   download_dir: {storage_config.get('download_dir')}")
    print(f"   transfer_dir: {storage_config.get('transfer_dir')}")
    print(f"   log_dir:      {storage_config.get('log_dir')}")
    print(f"   config_dir:   {storage_config.get('config_dir')}")
    
    print("\n2. Actual paths being used by ConfigManager:")
    paths = config_manager.get_storage_paths()
    print(f"   download_dir: {paths['download_dir']}")
    print(f"   transfer_dir: {paths['transfer_dir']}")
    print(f"   log_dir:      {paths['log_dir']}")
    print(f"   config_dir:   {paths['config_dir']}")
    
    print("\n3. Database configuration:")
    db_config = config_manager.get_database_config()
    print(f"   Database path: {db_config.get('path')}")
    print(f"   Media DB path: {config_manager.media_db_path}")
    
    print("\n4. Logging configuration:")
    logging_config = config_manager.get_logging_config()
    print(f"   Log file path: {logging_config.get('path')}")
    
    print("\n5. Directory existence check:")
    for name, path in paths.items():
        exists = path.exists()
        status = "✓ EXISTS" if exists else "✗ MISSING"
        print(f"   {name}: {status}")
    
    # Check if database parent directory exists
    db_path_str = db_config.get('path')
    if db_path_str:
        db_parent = Path(db_path_str).parent
        db_exists = db_parent.exists()
        print(f"   database parent: {'✓ EXISTS' if db_exists else '✗ MISSING'}")
    else:
        print("   database parent: ✗ NO PATH CONFIGURED")
    
    print("\n6. Path verification:")
    download_dir_config = storage_config.get('download_dir')
    download_dir_actual = str(paths['download_dir'])
    
    if download_dir_config and download_dir_actual:
        # Normalize paths for comparison
        config_normalized = str(Path(download_dir_config).resolve())
        actual_normalized = str(Path(download_dir_actual).resolve())
        
        if config_normalized == actual_normalized:
            print("   ✓ download_dir matches between config and runtime")
        else:
            print("   ✗ download_dir MISMATCH!")
            print(f"     Config:  {config_normalized}")
            print(f"     Runtime: {actual_normalized}")
    
    print("\n" + "="*70)
    print("Test Complete!")
    print("="*70 + "\n")

if __name__ == "__main__":
    test_config_paths()
