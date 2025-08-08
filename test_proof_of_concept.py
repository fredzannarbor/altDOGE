#!/usr/bin/env python3
"""
Proof of concept test for CFR Document Analyzer.

Tests the complete workflow from document retrieval to analysis.
"""

import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cfr_document_analyzer.config import Config
from cfr_document_analyzer.database import Database
from cfr_document_analyzer.analysis_engine import AnalysisEngine
from cfr_document_analyzer.models import SessionStatus


def test_proof_of_concept():
    """Test the complete proof of concept workflow."""
    # Set up logging
    Config.setup_logging(verbose=True)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting proof of concept test...")
    
    try:
        # Initialize components
        db = Database(Config.DATABASE_PATH)
        engine = AnalysisEngine(db)
        
        logger.info("✓ Components initialized")
        
        # Test with a small agency
        test_agency = Config.TEST_AGENCIES[0]  # national-credit-union-administration
        logger.info(f"Testing with agency: {test_agency}")
        
        # Run analysis with very small limit for testing
        session = engine.analyze_agency_documents(
            agency_slug=test_agency,
            prompt_strategy="DOGE Criteria",
            document_limit=1  # Just one document for proof of concept
        )
        
        logger.info(f"Analysis session created: {session.session_id}")
        logger.info(f"Session status: {session.status}")
        logger.info(f"Documents processed: {session.documents_processed}/{session.total_documents}")
        
        # Check if we got results
        if session.status == SessionStatus.COMPLETED and session.documents_processed > 0:
            logger.info("✓ Document analysis completed successfully")
            
            # Get detailed results
            results = engine.get_analysis_results(session.session_id)
            logger.info(f"Retrieved {len(results)} detailed results")
            
            if results:
                result = results[0]
                logger.info("✓ Analysis result details:")
                logger.info(f"  Document: {result['document_number']}")
                logger.info(f"  Title: {result['title'][:100]}...")
                logger.info(f"  Category: {result['analysis']['category']}")
                logger.info(f"  Success: {result['analysis']['success']}")
                
                if result['analysis']['statutory_references']:
                    logger.info(f"  Statutory refs: {len(result['analysis']['statutory_references'])}")
                
                if result['analysis']['reform_recommendations']:
                    logger.info(f"  Recommendations: {len(result['analysis']['reform_recommendations'])}")
                
                logger.info(f"  Processing time: {result['analysis']['processing_time']:.2f}s")
        
        # Get usage statistics
        stats = engine.get_usage_statistics()
        logger.info("✓ Usage statistics:")
        logger.info(f"  Total LLM calls: {stats['total_calls']}")
        logger.info(f"  Successful calls: {stats['successful_calls']}")
        logger.info(f"  Success rate: {stats['success_rate']:.1f}%")
        
        # Clean up
        engine.close()
        
        # Determine success
        success = (session.status == SessionStatus.COMPLETED and 
                  session.documents_processed > 0)
        
        if success:
            logger.info("🎉 Proof of concept test PASSED!")
            logger.info("The system successfully:")
            logger.info("  - Retrieved documents from Federal Register")
            logger.info("  - Analyzed content using DOGE criteria")
            logger.info("  - Stored results in database")
            logger.info("  - Generated structured analysis output")
        else:
            logger.warning("⚠️  Proof of concept test completed with limited results")
            logger.info("This may be due to:")
            logger.info("  - No documents available for the test agency")
            logger.info("  - Network connectivity issues")
            logger.info("  - LLM service unavailability")
        
        return success
        
    except Exception as e:
        logger.error(f"Proof of concept test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_proof_of_concept()
    print(f"\nTest result: {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)