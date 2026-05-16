import sqlalchemy as sa
import os
from pathlib import Path
from core.settings import config_manager

def check_columns():
    db_path = config_manager.database_path
    engine = sa.create_engine(f"sqlite:///{db_path}")
    inspector = sa.inspect(engine)
    if 'services' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('services')]
        print(f"Columns in 'services': {columns}")
    else:
        print("Table 'services' not found")

if __name__ == "__main__":
    check_columns()
