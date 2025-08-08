#!/usr/bin/env python3
"""
Test script for document retrieval functionality.
"""

import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cfr_document_analyzer.config import Config
from cfr_document_analyzer.database import Database
from cfr_document_analyzer.document_retriever import DocumentRetriever


def test_document_retrieval():
    """Test document retrieval for a small agency."""
    # Set up logging
    Config.setup_logging(verbose=True)
    logger = logging.getLogger(__name__)
    
    logger.info("Testing document retrieval...")
    
    try:
        # Initialize database and retriever
        db = Database(Config.DATABASE_PATH)
        retriever = DocumentRetriever(db, use_cache=True)
        
        # Test with a small agency (NCUA)
        test_agency = Config.TEST_AGENCIES[0]  # national-credit-union-administration
        logger.info(f"Testing with agency: {test_agency}")
        
        # Retrieve a small number of documents
        documents = retriever.get_agency_documents(test_agency, limit=2)
        
        logger.info(f"Retrieved {len(documents)} documents")
        
        for i, doc in enumerate(documents):
            logger.info(f"Document {i+1}:")
            logger.info(f"  Number: {doc.document_number}")
            logger.info(f"  Title: {doc.title[:100]}...")
            logger.info(f"  Content length: {doc.content_length}")
            logger.info(f"  Has content: {bool(doc.content)}")
            
            if doc.content:
                logger.info(f"  Content preview: {doc.content[:200]}...")
        
        retriever.close()
        logger.info("Document retrieval test completed successfully!")
        
        return len(documents) > 0
        
    except Exception as e:
        logger.error(f"Document retrieval test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_document_retrieval()
    sys.exit(0 if success else 1)