"""
Main entry point for the ereader application.
"""

import warnings
try:
    from bs4 import XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
except ImportError:
    pass

from ereader.app import run

if __name__ == "__main__":
    run()
