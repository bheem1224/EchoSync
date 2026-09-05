import re

content = open("plugins/EchoSync/slskd/plugin.py").read()

old_block = """        # Transition DownloadQueue state to VERIFYING
        if task_id:
            try:
                from services.download_manager import get_download_manager

                dm = get_download_manager()
                dm.transition_to_verifying(task_id, file_path=file_path)
            except Exception as e:
                logger.error(
                    "Failed to transition DownloadQueue %s to VERIFYING: %s", task_id, e
                )"""

new_block = """        # Transition DownloadQueue state to VERIFYING
        if task_id:
            try:
                task_id = int(task_id) if str(task_id).isdigit() else task_id
                from database.working_database import get_working_database
                from core.database.models.working import DownloadQueue, DownloadStatus
                from core.utils import utc_now
                
                work_db = get_working_database()
                with work_db.session_scope() as session:
                    task = session.get(DownloadQueue, task_id)
                    if task:
                        task.status = DownloadStatus.VERIFYING.value
                        if file_path and task.echo_sync_track is not None:
                            track_dict = dict(task.echo_sync_track)
                            track_dict["downloaded_file_path"] = file_path
                            task.echo_sync_track = track_dict
                        task.updated_at = utc_now()
                        session.commit()
                        session.refresh(task)
                        logger.info("DownloadQueue %s transitioned to VERIFYING", task_id)
            except Exception as e:
                logger.error(
                    "Failed to transition DownloadQueue %s to VERIFYING: %s", task_id, e
                )"""

content = content.replace(old_block, new_block)
open("plugins/EchoSync/slskd/plugin.py", "w").write(content)
