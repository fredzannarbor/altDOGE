#!/usr/bin/env python3
"""
Test script to validate document retrieval fixes.

Tests the fixed document retrieval system with problematic agencies.
"""

import logging
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from cfr_document_analyzer.database import Database
from cfr_document_analyzer.document_retriever import DocumentRetriever
from cfr_document_analyzer.config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_agency_document_retrieval(agency_slug: str, limit: int = 5):
    """
    Test document retrieval for a specific agency.
    
    Args:
        agency_slug: Agency identifier to test
        limit: Maximum number of documents to retrieve
    """
    logger.info(f"Testing document retrieval for agency: {agency_slug}")
    
    try:
        # Initialize components
        db = Database(':memory:')  # Use in-memory database for testing
        retriever = DocumentRetriever(db, use_cache=False)
        
        # Retrieve documents
        logger.info(f"Retrieving up to {limit} documents...")
        documents = retriever.get_agency_documents(agency_slug, limit)
        
        # Analyze results
        logger.info(f"Retrieved {len(documents)} documents")
        
        if not documents:
            logger.warning("No documents retrieved - this may indicate an issue")
            return False
        
        # Validate document content
        valid_documents = 0
        for i, doc in enumerate(documents, 1):
            logger.info(f"Document {i}: {doc.document_number}")
            logger.info(f"  Title: {doc.title[:100]}...")
            logger.info(f"  Content length: {doc.content_length}")
            
            if doc.content and len(doc.content) > 50:
                valid_documents += 1
                logger.info(f"  Content preview: {doc.content[:200]}...")
            else:
                logger.warning(f"  Invalid or missing content")
        
        success_rate = (valid_documents / len(documents)) * 100
        logger.info(f"Valid documents: {valid_documents}/{len(documents)} ({success_rate:.1f}%)")
        
        # Clean up
        retriever.close()
        
        return valid_documents > 0
        
    except Exception as e:
        logger.error(f"Error testing agency {agency_slug}: {e}")
        return False


def main():
    """Main test function."""
    logger.info("Starting document retrieval fix validation")
    
    # Test agencies that were previously problematic
    test_agencies = [
        'engraving-and-printing-bureau',  # The failing agency from the logs
        'national-credit-union-administration',  # Small agency for comparison
        'farm-credit-administration'  # Another small agency
    ]
    
    results = {}
    
    for agency_slug in test_agencies:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing agency: {agency_slug}")
        logger.info(f"{'='*60}")
        
        success = test_agency_document_retrieval(agency_slug, limit=10)
        results[agency_slug] = success
        
        if success:
            logger.info(f"✅ SUCCESS: {agency_slug} document retrieval working")
        else:
            logger.error(f"❌ FAILED: {agency_slug} document retrieval failed")
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    
    successful_agencies = sum(1 for success in results.values() if success)
    total_agencies = len(results)
    
    for agency_slug, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status}: {agency_slug}")
    
    logger.info(f"\nOverall success rate: {successful_agencies}/{total_agencies} agencies")
    
    if successful_agencies == total_agencies:
        logger.info("🎉 All tests passed! Document retrieval fixes are working.")
        return 0
    else:
        logger.error("⚠️  Some tests failed. Document retrieval may still have issues.")
        return 1


if __name__ == '__main__':
    sys.exit(main())