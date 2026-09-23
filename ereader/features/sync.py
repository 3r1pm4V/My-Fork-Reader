import hashlib
import logging
import time
import requests
from pathlib import Path
from ereader.utils import partial_md5
from PyQt6.QtCore import QObject, pyqtSignal, QThread


class SyncClient(QObject):
    """
    Client for KOReader Sync protocol.
    Handles progress pull/push to a remote server.
    """
    sync_finished = pyqtSignal(bool, str) # success, message

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.base_url = config.sync.url.rstrip('/')
        self.username = config.sync.username
        self.password = config.sync.password
        self.device_id = config.sync.device_id

    def _get_headers(self):
        return {
            "x-auth-user": self.username,
            "x-auth-key": self.password,
            "Content-Type": "application/json",
            "User-Agent": "ereader-py/0.1.0"
        }

    def pull_progress(self, doc_hash: str) -> dict | None:
        """Synchronous version of pull_progress for blocking calls."""
        if not self.config.sync.enabled or not self.username:
            return None
            
        url = f"{self.base_url}/koreader/sync/progress/{doc_hash}"
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                logging.info(f"Sync pull success for {doc_hash}: {data.get('percentage')}%")
                return data
        except Exception as e:
            logging.error(f"Sync pull sync error: {e}")
        return None

    async def pull_progress_async(self, doc_hash: str) -> dict | None:
        """Fetches remote reading progress for a document."""
        if not self.config.sync.enabled or not self.username:
            return None
            
        url = f"{self.base_url}/koreader/sync/progress/{doc_hash}"
        try:
            import httpx
            async with httpx.AsyncClient(headers=self._get_headers(), timeout=10) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    logging.info(f"Sync pull success for {doc_hash}: {data.get('percentage')}%")
                    return data
                elif resp.status_code == 404:
                    logging.info(f"No remote progress found for {doc_hash}")
                else:
                    logging.warning(f"Sync pull failed ({resp.status_code}): {resp.text}")
        except Exception as e:
            logging.error(f"Sync pull error: {e}")
        return None

    async def push_progress_async(self, doc_hash: str, percentage: float):
        """Pushes local reading progress to the remote server."""
        if not self.config.sync.enabled or not self.username:
            return
            
        url = f"{self.base_url}/koreader/sync/progress/{doc_hash}"
        payload = {
            "percentage": percentage,
            "device": "ereader-py",
            "device_id": self.device_id,
            "timestamp": int(time.time())
        }
        
        try:
            import httpx
            async with httpx.AsyncClient(headers=self._get_headers(), timeout=10) as client:
                resp = await client.put(url, json=payload)
                if resp.status_code in (200, 201):
                    logging.info(f"Sync push success for {doc_hash}: {percentage}%")
                else:
                    logging.warning(f"Sync push failed ({resp.status_code}): {resp.text}")
        except Exception as e:
            logging.error(f"Sync push error: {e}")

__all__ = ["SyncClient", "partial_md5"]
