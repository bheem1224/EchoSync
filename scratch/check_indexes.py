import sqlalchemy as sa
import os
from pathlib import Path
from core.settings import config_manager

def check_indexes():
    db_path = config_manager.database_path
    engine = sa.create_engine(f"sqlite:///{db_path}")
    inspector = sa.inspect(engine)
    if 'services' in inspector.get_table_names():
        indexes = inspector.get_indexes('services')
        print(f"Indexes on 'services': {[idx['name'] for idx in indexes]}")
    else:
        print("Table 'services' not found")

if __name__ == "__main__":
    check_indexes()
