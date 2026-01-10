"""
Simple test script to verify config directory changes are properly applied
(avoids importing the full core module which has heavy dependencies)
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import only what we need
from pathlib import Path
import json

def test_config_paths():
    print("\n" + "="*70)
    print("TESTING CONFIG PATH APPLICATION")
    print("="*70 + "\n")
    
    # Read config.json directly
    config_path = Path(__file__).parent / 'config' / 'config.json'
    
    if not config_path.exists():
        print(f"ERROR: Config file not found at {config_path}")
        return
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    storage_config = config.get('storage', {})
    
    print("1. Config file storage settings:")
    print(f"   download_dir: {storage_config.get('download_dir')}")
    print(f"   transfer_dir: {storage_config.get('transfer_dir')}")
    print(f"   log_dir:      {storage_config.get('log_dir')}")
    print(f"   config_dir:   {storage_config.get('config_dir')}")
    
    print("\n2. Path existence check:")
    for key, path_str in storage_config.items():
        if path_str:
            path = Path(path_str)
            exists = path.exists()
            status = "✓ EXISTS" if exists else "✗ MISSING"
            print(f"   {key}: {status}")
            if not exists:
                print(f"      Path: {path}")
        else:
            print(f"   {key}: ✗ NOT CONFIGURED")
    
    print("\n3. Database path:")
    db_config = config.get('database', {})
    db_path_str = db_config.get('path')
    if db_path_str:
        db_path = Path(db_path_str)
        print(f"   Database: {db_path}")
        if db_path.is_absolute():
            db_parent = db_path.parent
            print(f"   Parent:   {db_parent}")
            print(f"   Status:   {'✓ EXISTS' if db_parent.exists() else '✗ MISSING'}")
        else:
            print("   Type:     Relative path")
    else:
        print("   Database: ✗ NOT CONFIGURED")
    
    print("\n4. Logging path:")
    logging_config = config.get('logging', {})
    log_path_str = logging_config.get('path')
    if log_path_str:
        log_path = Path(log_path_str)
        print(f"   Log file: {log_path}")
        print(f"   Type:     {'Absolute' if log_path.is_absolute() else 'Relative'}")
    else:
        print("   Log file: ✗ NOT CONFIGURED")
    
    print("\n" + "="*70)
    print("SUMMARY: Config file contains the following directory settings:")
    print("="*70)
    print(f"Downloads:  {storage_config.get('download_dir', 'NOT SET')}")
    print(f"Transfer:   {storage_config.get('transfer_dir', 'NOT SET')}")
    print(f"Logs:       {storage_config.get('log_dir', 'NOT SET')}")
    print(f"Config:     {storage_config.get('config_dir', 'NOT SET')}")
    print(f"Database:   {db_path_str or 'NOT SET'}")
    print("="*70 + "\n")
    
    print("Next step: When you start the application, ConfigManager will:")
    print("  1. Read these paths from config.json")
    print("  2. Apply them as the active storage directories")
    print("  3. Create any missing directories automatically")
    print("  4. Log the resolved paths to console\n")

if __name__ == "__main__":
    test_config_paths()
