with open('/app/database/working_database.py', 'r') as f:
    content = f.read()

import re

new_init = """    def __init__(self, database_path: Optional[str] = None) -> None:
        from core.settings import config_manager

        uri = config_manager.get("database.working_uri")
        if uri:
            engine_url = uri
        else:
            data_dir = os.getenv("ECHOSYNC_DATA_DIR")
            if database_path:
                resolved_path = Path(database_path)
            elif data_dir:
                resolved_path = Path(data_dir) / "working.db"
            else:
                resolved_path = Path("data") / "working.db"

            self.database_path = resolved_path
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            engine_url = f"sqlite:///{self.database_path}"

        connect_args = {"check_same_thread": False} if engine_url.startswith("sqlite") else {}

        self.engine = create_engine(
            engine_url,
            future=True,
            echo=False,
            poolclass=NullPool,
            connect_args=connect_args,
        )
        if engine_url.startswith("sqlite"):
            event.listen(self.engine, "connect", _sqlite_pragmas)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)"""

content = re.sub(
    r'    def __init__\(self, database_path: Optional\[str\] = None\) -> None:.*?self\.SessionLocal = sessionmaker\(bind=self\.engine, expire_on_commit=False, future=True\)',
    new_init,
    content,
    flags=re.DOTALL
)

with open('/app/database/working_database.py', 'w') as f:
    f.write(content)
