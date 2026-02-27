
import asyncio
import os
import threading
from playwright.sync_api import Page, expect, sync_playwright
import sys
import time
import requests

# Add repository root to path so we can import modules if needed
sys.path.append(os.getcwd())

def run_flask_app():
    # Set necessary env vars
    os.environ['FLASK_ENV'] = 'development'

    # Import create_app correctly
    from web.api_app import create_app
    app = create_app()

    # Disable reloader to run in thread
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

def verify_routing_and_jobs(page: Page):
    # 1. Navigate to the root to ensure the app loads
    print("Navigating to root...")
    page.goto("http://127.0.0.1:5000/")

    # Wait for the app to load (look for a known element, e.g., Sidebar or Header)
    # Based on file list, there is a Sidebar.svelte. Let's look for a nav element.
    page.wait_for_selector("nav", timeout=10000)
    print("Root loaded.")

    # 2. Test SPA Routing: Navigate to a nested route directly
    # The issue was that refreshing on /settings/servers caused 404
    print("Testing nested route navigation...")
    page.goto("http://127.0.0.1:5000/settings/music-services")

    # Verify we are on the music services page
    # Look for "Music Services" header from SpotifyServiceCard.svelte/Music Services page
    expect(page.get_by_role("heading", name="Music Services")).to_be_visible(timeout=10000)
    print("Nested route loaded successfully (SPA routing fix verified).")

    # 3. Verify Spotify Redirect URI Auto-population
    # Check if the Spotify card exists
    spotify_card = page.locator(".spotify-card")
    if spotify_card.count() > 0:
        print("Spotify card found.")
        # Check the redirect URI input
        redirect_input = page.get_by_placeholder("http://127.0.0.1:8008/api/spotify/callback")

        # We expect it to be auto-populated with the current host (127.0.0.1:5000)
        # Note: The component logic uses window.location. Since we are on port 5000, it should use that.
        expected_uri = "http://127.0.0.1:5000/api/spotify/callback"

        # Expand credentials if collapsed
        expand_btn = page.get_by_role("button", name="Expand")
        if expand_btn.is_visible():
            expand_btn.click()

        # The input might be empty initially if not saved, so the onMount logic should populate it
        # We check if the value matches OR if it's empty in config but populated in UI
        # But wait, the component binds `value={redirectUri}`.
        # If `redirectUri` was empty from API, onMount sets it.

        expect(redirect_input).to_have_value(expected_uri)
        print(f"Spotify Redirect URI auto-populated correctly to {expected_uri}")
    else:
        print("Spotify card not found (maybe disabled?). Skipping specific Spotify check.")

    # 4. Verify Job Queue UI and Edit Interval
    print("Navigating to Jobs Settings...")
    page.goto("http://127.0.0.1:5000/settings/jobs")

    # Wait for jobs to load
    page.wait_for_selector(".job-card", timeout=10000)

    # Find the 'download_manager_status' job or any Soulsync/System job
    # We want to verify we can edit it.
    # Let's look for "download_manager_status" text
    job_card = page.locator(".job-card", has_text="download_manager_status")

    if job_card.count() > 0:
        print("Found download_manager_status job.")
        # Check if "Edit" button is visible
        # Try finding by text "Edit" inside the button
        edit_btn = job_card.locator("button", has_text="Edit")
        expect(edit_btn).to_be_visible()
        print("Edit button is visible for SoulSync job (Edit restriction removed).")

        # Click edit
        edit_btn.click()

        # Check if input appears
        input_field = job_card.locator("input[type='number']")
        expect(input_field).to_be_visible()

        # Check default value (should be 360 = 21600/60 minutes)
        # We updated the default to 21600s in backend.
        # But we need to see if the frontend loaded it.
        # If the backend is running with our changes, it should return 21600.
        # 21600 / 60 = 360 minutes.
        expect(input_field).to_have_value("360")
        print("Download manager job interval verified as 360 minutes (6 hours).")

    else:
        print("download_manager_status job not found in list. Checking for any edit button.")
        # Just verify we see at least one Edit button
        expect(page.get_by_role("button", name="Edit").first).to_be_visible()

    # Take screenshot
    page.screenshot(path="/home/jules/verification/verification.png")
    print("Verification screenshot saved.")

if __name__ == "__main__":
    # Start Flask in background thread
    server_thread = threading.Thread(target=run_flask_app, daemon=True)
    server_thread.start()

    # Give server a moment to start
    time.sleep(5)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            verify_routing_and_jobs(page)
            browser.close()
    except Exception as e:
        print(f"Verification failed: {e}")
        # Keep process alive briefly to ensure logs flush if needed
        time.sleep(1)
        sys.exit(1)
