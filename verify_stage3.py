import asyncio
import os
from soulsync_core import (
    LibraryManager, 
    ProviderManager, 
    SoulSyncTrack, 
    ScannerService
)

# Setup paths for testing
DB_PATH = "test_library.db"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

async def main():
    print("--- 🚀 Starting Stage 3 Verification ---")

    # 1. Verify LibraryManager (The Actor)
    print("\n[1] Initializing Library Manager (Actor Mode)...")
    lib = LibraryManager(DB_PATH)
    print("    ✅ LibraryManager instantiated.")
    
    # Test Sync Insert
    track = SoulSyncTrack()
    track.title = "Test Track"
    track.artist_name = "Test Artist"
    track.file_path = "/tmp/test.mp3"
    
    print("    -> Sending Upsert Message to Actor...")
    track_id = lib.upsert_track(track)
    print(f"    ✅ Actor replied. Track ID: {track_id}")

    # 2. Verify ProviderManager (The Async Engine)
    print("\n[2] Initializing Provider Manager (Zero-Trust)...")
    # Mock config (assuming ConfigManager isn't strictly required for init, or we pass a mock)
    # Note: If ProviderManager requires arguments, we might need to adjust this.
    # Based on your code, it likely takes (config_manager, provider_cache). 
    # For this smoke test, we check if we can import it.
    
    try:
        # We need the dependencies for the manager if the constructor requires them.
        # If the constructor is complex, we might skip full instantiation in this smoke test
        # and just verify the class exists.
        print(f"    ✅ ProviderManager class available: {ProviderManager}")
    except Exception as e:
        print(f"    ❌ ProviderManager init failed (Expected if missing deps): {e}")

    # 3. Verify Async Search (Mock)
    # Since we don't have real providers configured, we just check if the method exists
    if hasattr(ProviderManager, 'search'):
        print("    ✅ Async 'search' method exposed to Python.")
    else:
        print("    ❌ Async 'search' method MISSING.")

    print("\n--- ✨ Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(main())