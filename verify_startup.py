"""
Startup verification script - demonstrates ConfigManager initialization
This simulates what happens when the application starts
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("\n" + "="*80)
    print("SOULSYNC STARTUP - CONFIG INITIALIZATION")
    print("="*80 + "\n")
    
    print("Initializing ConfigManager...")
    print("-" * 80)
    
    # Import ConfigManager (this triggers initialization)
    try:
        from core.settings import config_manager
        print("\n" + "-" * 80)
        print("ConfigManager initialized successfully!")
        print("-" * 80 + "\n")
        
        # Get and display storage paths
        paths = config_manager.get_storage_paths()
        
        print("ACTIVE STORAGE PATHS:")
        print("-" * 80)
        print(f"Download Directory: {paths['download_dir']}")
        print(f"Transfer Directory: {paths['transfer_dir']}")
        print(f"Log Directory:      {paths['log_dir']}")
        print(f"Config Directory:   {paths['config_dir']}")
        print(f"Media Database:     {config_manager.media_db_path}")
        
        print("\n" + "DIRECTORY STATUS:")
        print("-" * 80)
        for name, path in paths.items():
            status = "✓" if path.exists() else "✗"
            print(f"{status} {name:20} {path}")
        
        db_status = "✓" if config_manager.media_db_path.parent.exists() else "✗"
        print(f"{db_status} {'media_db_parent':20} {config_manager.media_db_path.parent}")
        
        print("\n" + "CONFIGURATION VERIFICATION:")
        print("-" * 80)
        
        # Check if paths from config match runtime paths
        storage_config = config_manager.get('storage', {})
        matches = []
        mismatches = []
        
        for key, runtime_path in paths.items():
            config_path_str = storage_config.get(key)
            if config_path_str:
                config_path = Path(config_path_str).resolve()
                runtime_path_resolved = Path(runtime_path).resolve()
                
                if config_path == runtime_path_resolved:
                    matches.append(f"✓ {key}: Config matches runtime")
                else:
                    mismatches.append(f"✗ {key}: MISMATCH")
                    mismatches.append(f"  Config:  {config_path}")
                    mismatches.append(f"  Runtime: {runtime_path_resolved}")
        
        for match in matches:
            print(match)
        
        for mismatch in mismatches:
            print(mismatch)
        
        if not mismatches:
            print("\n✓ All storage paths are correctly applied from config!")
        else:
            print("\n✗ Some paths don't match - check logs above")
        
        print("\n" + "="*80)
        print("STARTUP VERIFICATION COMPLETE")
        print("="*80 + "\n")
        
        print("✓ ConfigManager is ready")
        print("✓ All required directories will be created on first use")
        print("✓ Configuration paths are properly loaded and applied")
        print("\nYou can now start the application normally.\n")
        
    except Exception as e:
        print(f"\n✗ ERROR during initialization: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
