# EchoSync plugins namespace package
import sys

from . import Spotify as spotify

sys.modules.setdefault("plugins.EchoSync.spotify", spotify)
if hasattr(spotify, "client"):
    sys.modules.setdefault("plugins.EchoSync.spotify.client", spotify.client)
