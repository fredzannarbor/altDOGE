#!/usr/bin/env python3
"""
Entry point script for CFR Document Analyzer CLI.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cfr_document_analyzer.cli import main

if __name__ == '__main__':
    sys.exit(main())