import os
import sqlite3
import json
import time

# It's important to set the working directory to the project root
# for the test to find the files it needs.
# This is usually handled by the test runner, but we do it manually here.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Now we can import the config_manager
from core.settings import config_manager, SECRETS

def run_test():
    """
    Tests the encryption and decryption of secrets in the ConfigManager.
    """
    print("--- Running Encryption Test ---")

    # 1. Define test data
    test_secret_key = "spotify.client_secret"
    test_secret_value = "my_super_secret_spotify_value"
    db_path = config_manager.database_path

    # Clean up before test
    if os.path.exists(db_path):
        os.remove(db_path)
    if os.path.exists(config_manager.config_path.parent / ".encryption_key"):
        os.remove(config_manager.config_path.parent / ".encryption_key")
    
    # Re-initialize config manager to pick up clean state
    config_manager.__init__()

    print(f"Testing with secret: '{test_secret_key}'")

    # 2. Set a secret value
    config_manager.set(test_secret_key, test_secret_value)
    print("Successfully set a secret value.")

    # 3. Get the secret value and verify it
    retrieved_value = config_manager.get(test_secret_key)
    print(f"Retrieved value: '{retrieved_value}'")
    assert retrieved_value == test_secret_value, f"FAIL: Retrieved value '{retrieved_value}' does not match original '{test_secret_value}'"
    print("✅ SUCCESS: Retrieved value matches original value.")

    # 4. Inspect the database to ensure the value is encrypted
    print("\nInspecting database...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM metadata WHERE key = 'app_config'")
    row = cursor.fetchone()
    conn.close()

    assert row, "FAIL: 'app_config' not found in database."

    db_config_data = json.loads(row[0])
    keys = test_secret_key.split('.')
    encrypted_value = db_config_data
    for k in keys:
        encrypted_value = encrypted_value[k]

    print(f"Encrypted value from DB: '{encrypted_value[:20]}...'")
    assert encrypted_value.startswith("enc:"), "FAIL: Value in database is not prefixed with 'enc:'"
    assert encrypted_value != test_secret_value, "FAIL: Value in database is not encrypted."
    print("✅ SUCCESS: Value is encrypted in the database.")
    
    # 5. Test non-secret value
    print("\nTesting non-secret value...")
    non_secret_key = "logging.level"
    non_secret_value = "DEBUG"
    config_manager.set(non_secret_key, non_secret_value)
    retrieved_non_secret = config_manager.get(non_secret_key)
    assert retrieved_non_secret == non_secret_value, "FAIL: Non-secret value did not match."
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM metadata WHERE key = 'app_config'")
    row = cursor.fetchone()
    conn.close()
    db_config_data = json.loads(row[0])
    assert db_config_data['logging']['level'] == non_secret_value, "FAIL: Non-secret value was modified in DB."
    print("✅ SUCCESS: Non-secret value is stored in plaintext.")


    # 6. Clean up after test
    print("\n--- Test Finished ---")
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed test database: {db_path}")
    if os.path.exists(config_manager.config_path.parent / ".encryption_key"):
        os.remove(config_manager.config_path.parent / ".encryption_key")
        print("Removed test encryption key.")

if __name__ == "__main__":
    run_test()
