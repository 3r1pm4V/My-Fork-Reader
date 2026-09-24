import hashlib
from pathlib import Path
import logging

def get_file_hash(path: Path) -> str:
    """Calculates SHA256 hash of a file for unique identification.
    Reads only first 1MB and last 1MB for speed on large files.
    """
    sha256 = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            file_size = path.stat().st_size
            if file_size > 2_000_000:
                sha256.update(f.read(1_000_000))
                f.seek(file_size - 1_000_000)
                sha256.update(f.read(1_000_000))
            else:
                sha256.update(f.read())
    except Exception as e:
        logging.error(f"Hash calculation failed for {path}: {e}")
        return hashlib.sha256(path.name.encode()).hexdigest()
    return sha256.hexdigest()

def partial_md5(path: Path) -> str:
    """KOReader-compatible document ID using the correct "Binary" matching method offset sequence."""
    try:
        digest = hashlib.md5()
        with open(path, "rb") as f:
            # Correct KOReader offset sequence as derived from util.lua
            offsets = [0, 1024, 4096, 16384, 65536, 262144, 1048576, 4194304, 16777216, 67108864, 268435456, 1073741824]
            for offset in offsets:
                f.seek(offset)
                sample = f.read(1024)
                if not sample:
                    break
                digest.update(sample)
        return digest.hexdigest()
    except Exception as e:
        logging.error(f"Partial MD5 calculation failed for {path}: {e}")
        return hashlib.md5(path.name.encode("utf-8")).hexdigest()

__all__ = ["get_file_hash", "partial_md5"]
