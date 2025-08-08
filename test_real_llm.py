#!/usr/bin/env python3
"""
Test real LLM integration with nimble-llm-caller.
"""

import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cfr_document_analyzer.config import Config
from cfr_document_analyzer.llm_client import LLMClient


def test_real_llm_call():
    """Test actual LLM call with nimble-llm-caller."""
    # Set up logging
    Config.setup_logging(verbose=True)
    logger = logging.getLogger(__name__)
    
    logger.info("Testing real LLM call...")
    
    try:
        # Initialize LLM client
        client = LLMClient()
        
        # Test with a simple regulation text
        test_regulation = """
        NATIONAL CREDIT UNION ADMINISTRATION
        
        12 CFR Part 701
        
        Organization and Operations of Federal Credit Unions
        
        SECTION 701.1 - SCOPE
        
        This part contains the rules and regulations for the organization and operation of Federal credit unions. Federal credit unions are chartered under the Federal Credit Union Act and are subject to the supervision of the National Credit Union Administration.
        
        SECTION 701.2 - DEFINITIONS
        
        For purposes of this part:
        (a) Credit union means a Federal credit union chartered under the Federal Credit Union Act.
        (b) Member means a person who has been admitted to membership in the credit union.
        (c) Share account means a balance held by a credit union and established by a member.
        """
        
        logger.info("Making LLM call for DOGE analysis...")
        
        # Test DOGE analysis
        doge_analysis = client.analyze_document_with_doge_prompts(
            test_regulation, 
            "test_regulation"
        )
        
        logger.info("✓ LLM call successful!")
        logger.info(f"Category: {doge_analysis.category.value}")
        logger.info(f"Statutory references: {len(doge_analysis.statutory_references)}")
        logger.info(f"Reform recommendations: {len(doge_analysis.reform_recommendations)}")
        logger.info(f"Justification preview: {doge_analysis.justification[:200]}...")
        
        # Get usage stats
        stats = client.get_usage_stats()
        logger.info(f"Usage stats: {stats.total_calls} calls, {stats.successful_calls} successful")
        
        return True
        
    except Exception as e:
        logger.error(f"Real LLM test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_real_llm_call()
    print(f"Test result: {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)