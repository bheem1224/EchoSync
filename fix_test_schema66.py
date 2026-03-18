import re

with open("services/download_manager.py", "r") as f:
    code = f.read()

pattern = re.compile(r'def _track_exists_in_library\(self, artist_name: str, title: str, album: Optional\[str\] = None, duration: Optional\[int\] = None\) -> bool:.*?try:', re.DOTALL)
def repl(m):
    return """def _track_exists_in_library(self, artist_name: str, title: str, album: Optional[str] = None, duration: Optional[int] = None) -> bool:
        \"\"\"
        Check if a track already exists in the library (database).
        \"\"\"
        if not artist_name or not title:
            return False

        try:
            db = get_database()
            with db.session_scope() as session:"""

code = pattern.sub(repl, code, count=1)

with open("services/download_manager.py", "w") as f:
    f.write(code)

with open("services/auto_importer.py", "r") as f:
    code = f.read()

pattern2 = re.compile(r'def _is_path_ignored\(self, file_path: str\) -> bool:.*?try:', re.DOTALL)
def repl2(m):
    return """def _is_path_ignored(self, file_path: str) -> bool:
        \"\"\"Check if a file was explicitly ignored in a previous review.\"\"\"
        work_db = get_working_database()
        try:"""

code = pattern2.sub(repl2, code, count=1)

with open("services/auto_importer.py", "w") as f:
    f.write(code)
