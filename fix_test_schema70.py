with open("services/auto_importer.py", "r") as f:
    code = f.read()

# Ah ha! It sets `work_db = get_working_database()` but THEN calls `with db.session_scope() as session:` where `db = get_database()`!
# My regex replacement didn't replace `db.session_scope` correctly here!

code = code.replace("db = get_database()\n            with db.session_scope() as session:", "with work_db.session_scope() as session:")

with open("services/auto_importer.py", "w") as f:
    f.write(code)
