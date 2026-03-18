with open("services/download_manager.py", "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "            download = Download(" in line:
        # Check if next line is sync_id
        if "sync_id" not in lines[i+1]:
            lines.insert(i+1, "                sync_id=track.sync_id,\n")

with open("services/download_manager.py", "w") as f:
    f.writelines(lines)
