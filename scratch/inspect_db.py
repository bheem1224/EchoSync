import os
import sys

sys.path.append(os.getcwd())

from database.config_database import get_config_database

db = get_config_database()
for name in [
    "spotify",
    "tidal",
    "EchoSync.Spotify",
    "EchoSync.Tidal",
    "EchoSync.slskd",
]:
    service_id = db.get_service_id(name)
    print(f"Name: {name} -> Service ID: {service_id}")
    if service_id:
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT name, absolute_install_path FROM services WHERE id=?",
                (service_id,),
            )
            row = c.fetchone()
            print(f"  DB Name: {row['name']}, Path: {row['absolute_install_path']}")
