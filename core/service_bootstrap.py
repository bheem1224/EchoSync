import asyncio
from core.tiered_logger import get_logger
from services.download_manager import get_download_manager
from services.auto_importer import get_auto_importer
from services.metadata_enhancer import get_metadata_enhancer

logger = get_logger("service_bootstrap")

async def start_services():
    """
    Initialize and start background services.
    This should be called after the core application context is ready.
    """
    logger.info("Starting background services...")

    # 1. Download Manager
    try:
        dm = get_download_manager()
        # Ensure it's running (it usually starts its own thread/loop on init or first access if designed that way,
        # but explicit start is safer if method exists)
        if hasattr(dm, 'start'):
            # Some implementations might be async or sync
            if asyncio.iscoroutinefunction(dm.start):
                await dm.start()
            else:
                dm.start()
        # If it uses ensure_background_task pattern:
        if hasattr(dm, 'ensure_background_task'):
            dm.ensure_background_task()

        logger.info("DownloadManager service started")
    except Exception as e:
        logger.error(f"Failed to start DownloadManager: {e}")

    # 2. Auto Importer
    try:
        importer = get_auto_importer()
        # Assuming similar start pattern or it hooks into job queue
        logger.info("AutoImporter service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize AutoImporter: {e}")

    # 3. Metadata Enhancer
    try:
        enhancer = get_metadata_enhancer()
        logger.info("MetadataEnhancer service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize MetadataEnhancer: {e}")

    logger.info("All background services initialization sequence completed.")
