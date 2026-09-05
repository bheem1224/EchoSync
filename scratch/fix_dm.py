import re

content = open("services/download_manager.py").read()

# Fix active_states sets
content = content.replace(
    'active_states = {"queued", "searching", "downloading"}',
    "active_states = {DownloadStatus.QUEUED.value, DownloadStatus.SEARCHING.value, DownloadStatus.DOWNLOADING.value}",
)
content = content.replace(
    'active_states = {"queued", "searching", "downloading", "in_progress", "paused"}',
    "active_states = {DownloadStatus.QUEUED.value, DownloadStatus.SEARCHING.value, DownloadStatus.DOWNLOADING.value}",
)

# Fix in_ lists
content = content.replace(
    '["searching", "downloading", "SEARCHING", "DOWNLOADING"]',
    "[DownloadStatus.SEARCHING.value, DownloadStatus.DOWNLOADING.value]",
)

content = content.replace(
    '["queued", "searching", "downloading", "in_progress", "paused", "verifying"]',
    "[DownloadStatus.QUEUED.value, DownloadStatus.SEARCHING.value, DownloadStatus.DOWNLOADING.value, DownloadStatus.VERIFYING.value]",
)

content = content.replace(
    'DownloadQueue.status.ilike("downloading")',
    "DownloadQueue.status == DownloadStatus.DOWNLOADING.value",
)

content = content.replace(
    'if item.status == "downloading" and item.provider_id:',
    "if item.status == DownloadStatus.DOWNLOADING.value and item.provider_id:",
)

content = content.replace(
    'if new_status != "downloading":',
    "if new_status != DownloadStatus.DOWNLOADING.value:",
)

open("services/download_manager.py", "w").write(content)
