import logging
from flask import Flask, request, jsonify, redirect
from core.tiered_logger import get_logger

logger = get_logger("oauth_sidecar")

sidecar_app = Flask(__name__)

@sidecar_app.route('/api/spotify/callback', methods=['GET'])
def spotify_callback_sidecar():
    """Handle Spotify OAuth callback over HTTPS.

    Extracts code and state, calls the extracted `process_oauth_callback` function,
    and returns a 302 redirect back to the main HTTP UI on port 5000.
    """
    from core.provider import ProviderRegistry
    from providers.spotify.client import process_oauth_callback

    if ProviderRegistry.is_provider_disabled('spotify'):
        return jsonify({'error': 'Spotify provider is disabled'}), 403

    try:
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')

        # Handle user-denied or provider errors directly
        if error:
            error_description = request.args.get('error_description', error)
            logger.error(f"Spotify OAuth sidecar error: {error_description}")
            html = f"<html><body style='font-family: Arial, sans-serif;'><h2>Spotify Authentication Failed</h2><p><strong>Error:</strong> {error_description}</p><p>Please try again or check your Spotify app settings.</p></body></html>"
            return html, 400, {"Content-Type": "text/html"}

        # Use the extracted shared function to process token fetching and saving
        ui_redirect_path = process_oauth_callback(code, state, error)

        # construct full URL if the path was relative
        if ui_redirect_path.startswith('/'):
            from core.storage import get_storage_service
            storage = get_storage_service()
            ui_base = storage.get_service_config('webui', 'base_url')

            # Use request.host to get the IP the user is hitting, ensuring we send them back to the correct host on port 5000.
            # Example: user is on https://192.168.1.100:5001/api/spotify/callback
            # request.host = "192.168.1.100:5001"
            # split(':')[0] = "192.168.1.100"
            host_ip = request.host.split(':')[0]

            if ui_base:
                ui_redirect = ui_base.rstrip('/') + ui_redirect_path
            else:
                ui_redirect = f'http://{host_ip}:5000{ui_redirect_path}'
        else:
            ui_redirect = ui_redirect_path

        return redirect(ui_redirect)

    except Exception as e:
        logger.error(f"Spotify sidecar callback error: {e}", exc_info=True)
        error_html = f"<html><body style='font-family: Arial, sans-serif;'><h2>Spotify Authentication Failed</h2><p>{str(e)}</p></body></html>"
        return error_html, 500, {"Content-Type": "text/html"}

if __name__ == '__main__':
    sidecar_app.run(host="0.0.0.0", port=5001)
