import hashlib
import logging
import time
import requests
from pathlib import Path
from ereader.utils import partial_md5
from ereader.features.sync_logic import RemoteJump, plan_remote_jump, SYNC_TOLERANCE
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

    def _get_headers(self) -> dict[str, str]:
        # KOReader sync server (kosync) expects x-auth-key to be the MD5
        # hex digest of the password, never the plaintext password.
        hashed_password = hashlib.md5(self.password.encode("utf-8")).hexdigest()
        return {
            "x-auth-user": self.username,
            "x-auth-key": hashed_password,
            "Content-Type": "application/json",
            # Same Accept header the official KOReader client sends.
            "Accept": "application/vnd.koreader.v1+json",
            "User-Agent": "ereader-py/0.1.0"
        }

    def pull_progress(self, doc_hash: str) -> dict | None:
        """Synchronous version of pull_progress for blocking calls."""
        if not self.config.sync.enabled or not self.username:
            return None
            
        # kosync progress endpoints live under /syncs/progress, not /progress.
        url = f"{self.base_url}/syncs/progress/{doc_hash}"
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                logging.info(f"Sync pull success for {doc_hash}: {data.get('percentage')}")
                return data
            elif resp.status_code == 404:
                logging.info(f"No remote progress found for {doc_hash}")
            else:
                # 401 = wrong username/password, etc. Don't swallow silently.
                logging.warning(f"Sync pull failed ({resp.status_code}): {resp.text[:200]}")
        except Exception as e:
            logging.error(f"Sync pull sync error: {e}")
        return None

    def push_progress(self, doc_hash: str, percentage: float, cfi: str, timeout: float = 3) -> bool:
        """Blocking push. Only meant for app shutdown, where the async loop
        may be torn down before a queued push finishes."""
        if not self.config.sync.enabled or not self.username:
            return False
        url = f"{self.base_url}/syncs/progress"
        payload = {
            "document": doc_hash,
            "percentage": percentage,
            "progress": cfi,
            "device": "ereader-py",
            "device_id": self.device_id,
        }
        try:
            resp = requests.put(url, json=payload, headers=self._get_headers(), timeout=timeout)
            if resp.status_code in (200, 201):
                return True
            logging.warning(f"Sync push (blocking) failed: {resp.status_code} - {resp.text[:200]}")
        except Exception as e:
            logging.error(f"Sync push (blocking) error: {e}")
        return False

    async def pull_progress_async(self, doc_hash: str) -> dict | None:
        """Fetches remote reading progress for a document."""
        if not self.config.sync.enabled or not self.username:
            return None
            
        url = f"{self.base_url}/syncs/progress/{doc_hash}"
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

    async def push_progress_async(self, doc_hash: str, percentage: float, cfi: str):
        """Pushes local reading progress to the remote server with CFI."""
        if not self.config.sync.enabled or not self.username:
            return
            
        url = f"{self.base_url}/syncs/progress"
        # 'progress' chứa CFI thật để đảm bảo client khác (Readest) hiểu vị trí chính xác
        payload = {
            "document": doc_hash,
            "percentage": percentage, 
            "progress": cfi, 
            "device": "ereader-py",
            "device_id": self.device_id,
        }

        try:
            import httpx
            async with httpx.AsyncClient(headers=self._get_headers(), timeout=10) as client:
                resp = await client.put(url, json=payload)
                if resp.status_code in (200, 201):
                    logging.info(f"Sync push success for {doc_hash} at {percentage:.4f} (cfi: {cfi})")
                else:
                    logging.warning(f"Sync push failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            logging.error(f"Sync push error: {e}")

__all__ = ["SyncClient", "partial_md5", "RemoteJump", "plan_remote_jump", "SYNC_TOLERANCE"]
