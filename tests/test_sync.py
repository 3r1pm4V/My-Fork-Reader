import pytest
from pathlib import Path
import hashlib
from ereader.features.sync import partial_md5, SyncClient
from ereader.config import Config

def test_partial_md5_stability(tmp_path):
    """Verifies that the partial hash is stable and follows the exponential rule."""
    test_file = tmp_path / "test_hash.txt"
    # Create a 20KB file
    content = b"A" * 20480 
    test_file.write_bytes(content)
    
    hash1 = partial_md5(test_file)
    hash2 = partial_md5(test_file)
    
    assert hash1 == hash2
    assert len(hash1) == 32 # MD5 hex length

def test_partial_md5_diff(tmp_path):
    """Partial hash should change if specific byte offsets change."""
    f1 = tmp_path / "f1.txt"
    f2 = tmp_path / "f2.txt"
    
    base_content = bytearray(b"0" * 10000)
    f1.write_bytes(base_content)
    
    # Modify f2 at an offset that partial_md5 checks (e.g., 2048)
    base_content[2048] = ord('1')
    f2.write_bytes(base_content)
    
    assert partial_md5(f1) != partial_md5(f2)

def test_sync_client_header_generation():
    cfg = Config()
    cfg.sync.username = "testuser"
    cfg.sync.password = "secretkey"
    
    client = SyncClient(cfg)
    headers = client._get_headers()
    
    assert headers["x-auth-user"] == "testuser"
    assert headers["x-auth-key"] == "secretkey"
    assert "User-Agent" in headers
