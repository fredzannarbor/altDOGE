#!/usr/bin/env python3
"""
Basic setup test for CFR Document Analyzer.
"""

import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cfr_document_analyzer.config import Config
from cfr_document_analyzer.database import Database
from cfr_document_analyzer.models import Document, AnalysisResult, RegulationCategory


def test_basic_setup():
    """Test basic setup and database operations."""
    # Set up logging
    Config.setup_logging(verbose=True)
    logger = logging.getLogger(__name__)
    
    logger.info("Testing basic setup...")
    
    try:
        # Test configuration
        Config.validate()
        logger.info("✓ Configuration validation passed")
        
        # Test database
        db = Database(Config.DATABASE_PATH)
        logger.info("✓ Database initialization passed")
        
        # Test models
        test_doc = Document(
            document_number="TEST-2025-001",
            title="Test Document",
            agency_slug="test-agency",
            content="This is a test document for validation."
        )
        logger.info("✓ Document model creation passed")
        
        # Test database storage
        doc_data = {
            'document_number': test_doc.document_number,
            'title': test_doc.title,
            'agency_slug': test_doc.agency_slug,
            'content': test_doc.content
        }
        doc_id = db.store_document(doc_data)
        logger.info(f"✓ Document storage passed (ID: {doc_id})")
        
        # Test analysis storage
        analysis_data = {
            'document_id': doc_id,
            'prompt_strategy': 'DOGE Criteria',
            'category': RegulationCategory.NOT_STATUTORILY_REQUIRED.value,
            'justification': 'Test analysis result',
            'success': True
        }
        analysis_id = db.store_analysis(analysis_data)
        logger.info(f"✓ Analysis storage passed (ID: {analysis_id})")
        
        # Test retrieval
        docs = db.get_documents_by_agency('test-agency')
        logger.info(f"✓ Document retrieval passed ({len(docs)} documents)")
        
        analyses = db.get_analyses_by_document(doc_id)
        logger.info(f"✓ Analysis retrieval passed ({len(analyses)} analyses)")
        
        logger.info("All basic setup tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"Basic setup test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_basic_setup()
    print(f"Test result: {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)