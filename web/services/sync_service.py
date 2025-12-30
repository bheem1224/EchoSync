# Thin adapter to existing services.sync_service
from typing import Dict

from services.sync_service import PlaylistSyncService  # reuse existing implementation

class SyncAdapter:
    def __init__(self):
        self._service = PlaylistSyncService()

    def trigger_sync(self, payload: Dict) -> Dict:
        mode = payload.get("mode", "provider-to-provider")
        sources = payload.get("sources") or []
        targets = payload.get("targets") or {}
        provider_targets = targets.get("providers") or []
        library_targets = targets.get("libraries") or []

        if not sources:
            return {"accepted": False, "error": "At least one source provider is required."}

        if mode == "provider-to-provider" and not provider_targets:
            return {"accepted": False, "error": "Select at least one provider target for provider-to-provider sync."}

        if mode == "provider-to-library" and not library_targets:
            return {"accepted": False, "error": "Select at least one library target for provider-to-library sync."}

        # Placeholder for real sync orchestration; for now, echo validated payload
        return {
            "accepted": True,
            "mode": mode,
            "sources": sources,
            "targets": {
                "providers": provider_targets,
                "libraries": library_targets,
            },
        }
