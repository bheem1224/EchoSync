from core.backup_manager import backup_manager
try:
    path = backup_manager.create_backup()
    print("Backup created successfully at:", path)
except Exception as e:
    print("Backup failed:", e)
