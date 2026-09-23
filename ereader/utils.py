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

def partial_md5(path: Path, chunk_size: int = 1024) -> str:
    """
    KOReader-compatible partial MD5 of file.
    Reads 1KB chunks at exponentially increasing offsets.
    """
    md5 = hashlib.md5()
    try:
        file_size = path.stat().st_size
        offset = chunk_size
        with open(path, "rb") as f:
            while offset < file_size:
                f.seek(offset)
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                md5.update(chunk)
                offset *= 2
    except Exception as e:
        logging.error(f"Partial MD5 failed for {path}: {e}")
        return hashlib.md5(path.name.encode()).hexdigest()
    return md5.hexdigest()

__all__ = ["get_file_hash", "partial_md5"]
