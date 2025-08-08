#!/usr/bin/env python3
"""
Test script for LLM client functionality.
"""

import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cfr_document_analyzer.config import Config
from cfr_document_analyzer.llm_client import LLMClient, LLMUsageStats
from cfr_document_analyzer.models import DOGEAnalysis, RegulationCategory


def test_llm_client_setup():
    """Test LLM client setup and parsing functionality."""
    # Set up logging
    Config.setup_logging(verbose=True)
    logger = logging.getLogger(__name__)
    
    logger.info("Testing LLM client setup...")
    
    try:
        # Test client initialization
        client = LLMClient()
        logger.info("✓ LLM client initialization passed")
        
        # Test usage stats
        stats = client.get_usage_stats()
        assert isinstance(stats, LLMUsageStats)
        logger.info("✓ Usage stats retrieval passed")
        
        # Test DOGE response parsing with mock response
        mock_response = """
CATEGORY: NSR

STATUTORY REFERENCES:
- 12 U.S.C. § 1751 et seq. (Federal Credit Union Act)
- 12 CFR Part 701 (Organization and Operations of Federal Credit Unions)

REFORM RECOMMENDATIONS:
- Simplify reporting requirements to reduce administrative burden
- Harmonize with similar regulations from other financial regulators
- Modernize electronic filing requirements

JUSTIFICATION:
This regulation appears to be Not Statutorily Required (NSR) as it implements 
administrative procedures that, while authorized by the Federal Credit Union Act, 
are not specifically mandated by the statute. The regulation could be simplified 
to reduce compliance costs while maintaining necessary oversight.
"""
        
        doge_analysis = client._parse_doge_response(mock_response)
        
        # Verify parsing results
        assert doge_analysis.category == RegulationCategory.NOT_STATUTORILY_REQUIRED
        assert len(doge_analysis.statutory_references) == 2
        assert len(doge_analysis.reform_recommendations) == 3
        assert "Not Statutorily Required" in doge_analysis.justification
        
        logger.info("✓ DOGE response parsing passed")
        logger.info(f"  Category: {doge_analysis.category.value}")
        logger.info(f"  Statutory refs: {len(doge_analysis.statutory_references)}")
        logger.info(f"  Recommendations: {len(doge_analysis.reform_recommendations)}")
        
        # Test rate limiting setup
        client._enforce_rate_limit()  # Should not raise error
        logger.info("✓ Rate limiting setup passed")
        
        logger.info("All LLM client setup tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"LLM client setup test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_llm_client_setup()
    print(f"Test result: {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)