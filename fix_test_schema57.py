with open("services/download_manager.py", "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "            download = session.query(Download).get(download_id)" in line and "with self.work_db.session_scope() as session:" in lines[i-1]:
        lines[i] = "                download = session.query(Download).get(download_id)\n"

with open("services/download_manager.py", "w") as f:
    f.writelines(lines)
