with open("services/download_manager.py", "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "            with self.db.session_scope() as session:" in line and "with db.session_scope() as session:" in lines[i-1]:
        lines[i] = ""

with open("services/download_manager.py", "w") as f:
    f.writelines(lines)
