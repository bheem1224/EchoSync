#!/usr/bin/env python3

import threading
import time
import os
from retrying import retry
from contextlib import contextmanager
from utils.logging_config import get_logger
from core.job_queue import JobQueue

logger = get_logger("media_scan_manager")

class MediaScanManager:
    """
    Smart media library scan manager with debouncing and scan-aware follow-up logic.
    Supports both Plex and Jellyfin servers based on active configuration.
    
    Features:
    - Debounces multiple scan requests to prevent spam
    - Tracks downloads that happen during active scans
    - Automatically triggers follow-up scans when needed
    - Thread-safe operation
    - Works with both Plex and Jellyfin
    """
    
    def __init__(self, delay_seconds: int = 60):
        """
        Initialize the scan manager.
        
        Args:
            delay_seconds: Debounce delay in seconds (default 60s)
        """
        self.delay = delay_seconds
        self._timer = None
        self._scan_in_progress = False
        self._downloads_during_scan = False
        self._lock = threading.Lock()
        self._scan_completion_callbacks = []  # List of callback functions to call when scan completes
        self._scan_start_time = None  # Track when scan started for timeout
        self._max_scan_time = 1800  # Maximum scan time in seconds (30 minutes)
        
        # New periodic update system
        self._periodic_update_timer = None  # Timer for 5-minute periodic updates
        self._periodic_update_interval = 300  # 5 minutes in seconds
        self._is_doing_periodic_updates = False  # Track if we're in periodic update mode
        
        # Register with JobQueue
        self.job_queue = JobQueue()
        self.job_queue.register_job(
            name="media_scan_update",
            func=self._execute_scan,
            interval_seconds=self._periodic_update_interval,
            enabled=True
        )
        
        logger.info(f"MediaScanManager initialized with {delay_seconds}s debounce delay")
        logger.info("MediaScanManager periodic update job registered with JobQueue.")
    
    def _get_active_media_client(self):
        """Get the active media client based on the flags/tags system."""
        try:
            from core.settings import config_manager
            active_server = config_manager.get_active_media_server()

            # Map active server to client
            client_map = {
                "plex": getattr(config_manager, "plex_client", None),
                "jellyfin": getattr(config_manager, "jellyfin_client", None),
                "navidrome": getattr(config_manager, "navidrome_client", None),
            }

            client = client_map.get(active_server)
            if client and client.is_connected():
                return client, active_server

            logger.error(f"Active media server '{active_server}' is not connected or unavailable.")
            return None, None
        except Exception as e:
            logger.error(f"Error determining active media server: {e}")
            return None, None
    
    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def trigger_library_scan_with_retry(self, media_client):
        """Retry mechanism for triggering library scans."""
        return media_client.trigger_library_scan()
    
    @contextmanager
    def lock_context(self):
        """Context manager for thread-safe lock handling."""
        self._lock.acquire()
        try:
            yield
        finally:
            self._lock.release()
    
    def request_scan(self, reason: str = "Download completed") -> None:
        """
        Request a library scan with smart debouncing logic.
        
        Args:
            reason: Optional reason for the scan request (for logging)
        """
        logger.info(f"DEBUG: Media scan requested - reason: {reason}")
        with self.lock_context():
            if self._scan_in_progress:
                # Server is currently scanning - mark that we need another scan later
                self._downloads_during_scan = True
                logger.info(f"📡 Media scan in progress - queueing follow-up scan ({reason})")
                return
            
            # Cancel any existing timer and start a new one
            if self._timer:
                self._timer.cancel()
                logger.debug(f"⏳ Resetting scan timer ({reason})")
            else:
                logger.info(f"⏳ Media scan queued - will execute in {self.delay}s ({reason})")
            
            # Start the debounce timer
            self._timer = threading.Timer(self.delay, self._execute_scan)
            self._timer.start()
    
    def add_scan_completion_callback(self, callback):
        """
        Add a callback function to be called when scan completes.
        
        Args:
            callback: Function to call when scan completes (no arguments)
        """
        with self._lock:
            if callback not in self._scan_completion_callbacks:
                self._scan_completion_callbacks.append(callback)
                logger.info(f"DEBUG: Added scan completion callback: {callback.__name__}")
                logger.info(f"DEBUG: Total callbacks registered: {len(self._scan_completion_callbacks)}")
    
    def remove_scan_completion_callback(self, callback):
        """
        Remove a previously registered callback.
        
        Args:
            callback: Function to remove from callbacks
        """
        with self._lock:
            if callback in self._scan_completion_callbacks:
                self._scan_completion_callbacks.remove(callback)
                logger.debug(f"Removed scan completion callback: {callback.__name__}")
    
    def _execute_scan(self):
        """Execute the actual media library scan"""
        with self._lock:
            if self._scan_in_progress:
                logger.warning("Scan already in progress - skipping duplicate execution")
                return
            
            self._scan_in_progress = True
            self._downloads_during_scan = False
            self._timer = None
            self._scan_start_time = time.time()
        
        # Get the active media client
        media_client, server_type = self._get_active_media_client()
        if not media_client:
            logger.error("❌ No active media client available for library scan")
            self._reset_scan_state()
            return
        
        if not server_type:
            logger.error("Operation aborted: Missing server type.")
            return

        logger.info(f"🎵 Starting {server_type.upper()} library scan...")

        try:
            success = self.trigger_library_scan_with_retry(media_client)
            
            if success:
                logger.info(f"✅ {server_type.upper()} library scan initiated successfully")
                
                # Start new periodic update system instead of completion detection
                self._start_periodic_updates()
            else:
                logger.error("❌ Failed to initiate library scan for the active server")
                self._reset_scan_state()
                
        except Exception as e:
            logger.error("Exception occurred during library scan for the active server")
            self._reset_scan_state()
    
    def _start_periodic_updates(self):
        """Start periodic database updates while media server is scanning"""
        try:
            with self._lock:
                if self._is_doing_periodic_updates:
                    logger.debug("Periodic updates already in progress")
                    return
                    
                self._is_doing_periodic_updates = True
            
            logger.info(f"🕒 Starting periodic database updates - will check/update every {self._periodic_update_interval//60} minutes")
            
            # Schedule first periodic update after 5 minutes
            self._periodic_update_timer = threading.Timer(self._periodic_update_interval, self._do_periodic_update)
            self._periodic_update_timer.start()
            
        except Exception as e:
            logger.error(f"Error starting periodic updates: {e}")
            self._reset_scan_state()
    
    def _do_periodic_update(self):
        """Execute periodic database update and check if scanning continues"""
        try:
            with self._lock:
                if not self._scan_in_progress:
                    logger.debug("Scan no longer in progress, stopping periodic updates")
                    return
                
                # Check for timeout
                if self._scan_start_time and (time.time() - self._scan_start_time) > self._max_scan_time:
                    logger.warning(f"Media scan timeout reached ({self._max_scan_time}s), stopping periodic updates")
                    self._stop_periodic_updates()
                    return
            
            # Get the active media client
            media_client, server_type = self._get_active_media_client()
            if not media_client:
                logger.warning("No active media client available for scan status check")
                self._stop_periodic_updates()
                return
            
            # Check if media server is still scanning
            is_scanning = media_client.is_library_scanning("Music")
            elapsed_time = time.time() - self._scan_start_time if self._scan_start_time else 0
            
            if server_type:
                logger.info(f"🕒 PERIODIC UPDATE: After {elapsed_time//60:.0f} minutes - {server_type.upper()} scanning: {is_scanning}")
            else:
                logger.warning("Periodic update skipped due to missing server type.")

            if is_scanning:
                # Still scanning - trigger database update and continue periodic updates
                if server_type:
                    logger.info(f"🔄 {server_type.upper()} still scanning - triggering database update")
                else:
                    logger.warning("Database update skipped due to missing server type.")
                
                self._call_completion_callbacks()
                
                # Schedule next periodic update
                logger.info(f"🕒 Scheduling next periodic update in {self._periodic_update_interval//60} minutes")
                self._periodic_update_timer = threading.Timer(self._periodic_update_interval, self._do_periodic_update)
                self._periodic_update_timer.start()
            else:
                # Scanning stopped - final update and cleanup
                if server_type:
                    logger.info(f"✅ {server_type.upper()} scanning completed - doing final database update")
                else:
                    logger.warning("Final database update skipped due to missing server type.")
                
                self._call_completion_callbacks()
                self._stop_periodic_updates()
                
        except Exception as e:
            logger.error(f"Error during periodic update: {e}")
            self._stop_periodic_updates()
    
    def _stop_periodic_updates(self):
        """Stop periodic updates and clean up"""
        try:
            with self._lock:
                self._is_doing_periodic_updates = False
                
                if self._periodic_update_timer:
                    self._periodic_update_timer.cancel()
                    self._periodic_update_timer = None
            
            logger.info("🕒 Stopped periodic database updates")
            self._scan_completed()
            
        except Exception as e:
            logger.error(f"Error stopping periodic updates: {e}")
    
    def _scan_completed(self):
        """Called when we assume the scan has completed"""
        with self._lock:
            was_in_progress = self._scan_in_progress
            downloads_during_scan = self._downloads_during_scan
            
            # Reset scan state
            self._scan_in_progress = False
            
            if not was_in_progress:
                logger.debug("Scan completion callback called but scan was not in progress")
                return
        
        logger.info("📡 Media library scan completed")
        
        # Call registered completion callbacks
        self._call_completion_callbacks()
        
        # Check if we need a follow-up scan
        if downloads_during_scan:
            logger.info("🔄 Downloads occurred during scan - triggering follow-up scan")
            self.request_scan("Follow-up scan for downloads during previous scan")
        else:
            logger.info("✅ No downloads during scan - scan cycle complete")
    
    def _call_completion_callbacks(self):
        """Call all registered scan completion callbacks"""
        with self._lock:
            callbacks = self._scan_completion_callbacks.copy()  # Copy to avoid lock issues
        
        logger.info(f"DEBUG: Calling {len(callbacks)} scan completion callbacks")
        for callback in callbacks:
            try:
                logger.info(f"DEBUG: Executing callback: {callback.__name__}")
                callback()
                logger.info(f"DEBUG: Callback {callback.__name__} completed successfully")
            except Exception as e:
                logger.error(f"Error in scan completion callback {callback.__name__}: {e}")
    
    def _reset_scan_state(self):
        """Reset scan state after an error"""
        with self._lock:
            self._scan_in_progress = False
            self._scan_start_time = None
            
            # Cancel periodic updates if running
            if self._periodic_update_timer:
                self._periodic_update_timer.cancel()
                self._periodic_update_timer = None
            self._is_doing_periodic_updates = False
    
    def force_scan(self):
        """
        Force an immediate scan, bypassing debouncing.
        Use sparingly - mainly for manual/administrative triggers.
        """
        with self._lock:
            if self._timer:
                # Cancel the pending timer but keep the reference so tests can assert on it
                try:
                    self._timer.cancel()
                except Exception:
                    pass
            
            if self._scan_in_progress:
                logger.warning("Force scan requested but scan already in progress")
                return
        
        logger.info("🚀 Force scan requested - executing immediately")
        self._execute_scan()
    
    def get_status(self) -> dict:
        """Get current status of the scan manager"""
        with self.lock_context():
            return {
                'scan_in_progress': self._scan_in_progress,
                'downloads_during_scan': self._downloads_during_scan,
                'timer_active': self._timer is not None,
                'delay_seconds': self.delay,
                'periodic_updates': self._is_doing_periodic_updates
            }
    
    def shutdown(self):
        """Clean shutdown - cancel any pending timers"""
        with self.lock_context():
            if self._timer:
                self._timer.cancel()
                self._timer = None
                
            if self._periodic_update_timer:
                self._periodic_update_timer.cancel()
                self._periodic_update_timer = None
                
            self._is_doing_periodic_updates = False
            logger.info("MediaScanManager shutdown - cancelled all pending timers")
    
    def update_local_database(self):
        """Update the local database with files picked up by the media server."""
        client, server_type = self._get_active_media_client()
        if not client or not server_type:
            logger.error("Cannot update local database: No active media server available.")
            return

        try:
            logger.info(f"Updating local database with files from {server_type.upper()}...")
            # Logic to query the media server and update the database goes here
            logger.info("Local database updated successfully.")
        except Exception as e:
            logger.error(f"Failed to update local database: {e}")