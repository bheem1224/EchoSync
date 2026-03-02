import socket

def get_lan_ip():
    """Returns the local network IP address of the current machine."""
    try:
        # We don't need to actually connect to the remote host.
        # This just helps the socket figure out which interface's IP to return.
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_main_app_port():
    """Returns the port the main app is running on. Default is 5000."""
    try:
        from core.settings import config_manager
        app_config = config_manager.get_config('app_config') or {}
        return int(app_config.get('port', 5000))
    except Exception:
        return 5000
