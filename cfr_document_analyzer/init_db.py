#!/usr/bin/env python3
"""
Database initialization script for CFR Document Analyzer.

Creates the database and tables needed for the proof of concept.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from cfr_document_analyzer.database import Database
from cfr_document_analyzer.config import Config


def main():
    """Initialize the database for CFR Document Analyzer."""
    # Set up logging
    Config.setup_logging(verbose=True)
    logger = logging.getLogger(__name__)
    
    logger.info("Initializing CFR Document Analyzer database...")
    
    try:
        # Validate configuration
        Config.validate()
        
        # Initialize database
        db = Database(Config.DATABASE_PATH)
        
        logger.info(f"Database initialized successfully at {Config.DATABASE_PATH}")
        logger.info("Ready for document analysis!")
        
        # Print some basic info
        print(f"Database created at: {Config.DATABASE_PATH}")
        print(f"Output directory: {Config.OUTPUT_DIRECTORY}")
        print(f"Test agencies configured: {', '.join(Config.TEST_AGENCIES)}")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()