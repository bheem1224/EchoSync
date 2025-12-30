#!/usr/bin/env python
"""
Simple launcher for the SoulSync Flask API backend.

Usage:
    python run_api.py                    # Run with HTTPS (self-signed cert)
    DISABLE_INTERNAL_HTTPS=true python run_api.py  # Run with HTTP (dev only)
"""

from web.api_app import run_with_ssl, create_app
import os

if __name__ == "__main__":
    # Check if HTTPS is explicitly disabled (for dev/testing)
    if os.getenv('DISABLE_INTERNAL_HTTPS') == 'true':
        print("[DEV MODE] Internal HTTPS disabled via DISABLE_INTERNAL_HTTPS env var")
        app = create_app()
        app.run(host="0.0.0.0", port=8000, debug=True)
    else:
        # Default: Run with ephemeral self-signed cert
        run_with_ssl(debug=True)
