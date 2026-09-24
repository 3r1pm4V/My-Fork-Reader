import os
import requests
import logging
from pathlib import Path

# Thư mục đích chứa các file JS
ASSETS_DIR = Path(__file__).parent / "foliate-js"
# Nguồn tải file (Sử dụng branch main của foliate-js)
BASE_URL = "https://cdn.jsdelivr.net/gh/johnfactotum/foliate-js@main/"
REQUIRED_FILES = [
    # Core modules statically imported by view.js
    "view.js", "epub.js", "epubcfi.js", "paginator.js",
    "overlayer.js", "progress.js", "search.js", "text-walker.js",
    # Format-specific modules view.js loads dynamically depending on the
    # file being opened (view.open() is called directly on the raw file
    # for EPUB/MOBI/FB2/CBZ/PDF, so all of these are needed at runtime,
    # not just EPUB's own dependencies).
    "fb2.js", "mobi.js", "comic-book.js", "pdf.js", "fixed-layout.js", "tts.js",
    # 'vendor/zip.js' unzips EPUB/CBZ/FBZ containers; 'vendor/fflate.js'
    # decompresses MOBI records. Both are dynamic imports of view.js.
    "vendor/zip.js", "vendor/fflate.js"
]

def ensure_assets():
    """Tự động kiểm tra và tải các file JS còn thiếu từ foliate-js."""
    if not ASSETS_DIR.exists():
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        logging.info(f"Created assets directory at {ASSETS_DIR}")

    for filename in REQUIRED_FILES:
        file_path = ASSETS_DIR / filename
        if not file_path.exists():
            logging.info(f"Downloading missing asset: {filename}...")
            try:
                # Ensure parent directory exists for nested assets (e.g. 'vendor/zip.js')
                file_path.parent.mkdir(parents=True, exist_ok=True)
                response = requests.get(BASE_URL + filename, timeout=10)
                response.raise_for_status()
                file_path.write_text(response.text, encoding="utf-8")
                logging.info(f"Successfully downloaded {filename}")
            except Exception as e:
                logging.error(f"Failed to download {filename}: {e}")
        else:
            logging.debug(f"Asset already exists: {filename}")
