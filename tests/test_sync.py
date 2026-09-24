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
    # kosync wants the MD5 hex digest of the password, never the plaintext
    assert headers["x-auth-key"] == hashlib.md5(b"secretkey").hexdigest()
    assert "User-Agent" in headers


# --- remote progress reconciliation -------------------------------------

from ereader.features.sync_logic import plan_remote_jump


def test_no_remote_no_jump():
    assert plan_remote_jump(None, 0.3) is None
    assert plan_remote_jump({}, 0.3) is None
    assert plan_remote_jump({"percentage": "abc"}, 0.3) is None


def test_within_tolerance_no_jump():
    assert plan_remote_jump({"percentage": 0.302}, 0.300) is None


def test_far_remote_offers_jump_by_percentage_for_koreader_xpointer():
    remote = {"percentage": 0.5, "progress": "/body/DocFragment[3]/body/p[2]/text().0",
              "device": "Kindle"}
    jump = plan_remote_jump(remote, 0.0)
    assert jump is not None
    assert jump.percentage == 0.5
    assert jump.cfi is None            # xpointer is not a CFI -> fall back to %
    assert jump.device == "Kindle"


def test_real_cfi_is_used_and_percentage_string_is_accepted():
    remote = {"percentage": "0.75", "progress": "epubcfi(/6/8!/4/2)"}
    jump = plan_remote_jump(remote, 0.1)
    assert jump.cfi == "epubcfi(/6/8!/4/2)"
    assert jump.percentage == 0.75
