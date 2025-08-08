#!/usr/bin/env python3
"""
Test direct LLM call to verify the API is working.
"""

import os
import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cfr_document_analyzer.config import Config

# Test direct litellm call
def test_direct_llm():
    """Test direct LLM call using litellm."""
    Config.setup_logging(verbose=True)
    logger = logging.getLogger(__name__)
    
    logger.info("Testing direct LLM call...")
    
    try:
        import litellm
        
        # Set API key
        if Config.GEMINI_API_KEY:
            os.environ['GEMINI_API_KEY'] = Config.GEMINI_API_KEY
            logger.info("API key set")
        else:
            logger.error("No API key found")
            return False
        
        # Simple test prompt
        test_prompt = """
Analyze the following regulation text and categorize it according to DOGE criteria.

Determine if this regulation is:
- SR (Statutorily Required): Required by specific statutory language
- NSR (Not Statutorily Required): Not required by statute but may be permissible
- NRAN (Not Required but Agency Needs): Not required by statute but needed for agency operations

Provide your analysis in the following format:

CATEGORY: [SR/NSR/NRAN]

STATUTORY REFERENCES:
- [List any specific statutory provisions that require or authorize this regulation]

REFORM RECOMMENDATIONS:
- [List specific recommendations for deletion, simplification, harmonization, or modernization]

JUSTIFICATION:
[Provide detailed justification for your categorization and recommendations, citing specific statutory provisions where applicable]

Regulation text:
NATIONAL CREDIT UNION ADMINISTRATION

Renewal of Agency Information Collection of a Previously Approved Collection; Request for Comments

AGENCY: National Credit Union Administration (NCUA).
ACTION: Notice.

SUMMARY: The National Credit Union Administration (NCUA) is requesting comments on a renewal of a previously approved information collection.
"""
        
        # Make direct litellm call
        response = litellm.completion(
            model="gemini/gemini-2.5-flash",
            messages=[{"role": "user", "content": test_prompt}],
            max_tokens=4000,
            temperature=0.1
        )
        
        logger.info("✓ Direct LLM call successful!")
        
        # Extract content
        if response and response.choices:
            content = response.choices[0].message.content
            logger.info(f"Response length: {len(content)} characters")
            logger.info(f"Response preview: {content[:300]}...")
            
            # Check for DOGE format
            if "CATEGORY:" in content:
                logger.info("✓ Response contains DOGE format")
            
            # Token usage
            if hasattr(response, 'usage') and response.usage:
                logger.info(f"Token usage: {response.usage}")
            
            return True
        else:
            logger.error("No response content")
            return False
            
    except Exception as e:
        logger.error(f"Direct LLM test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_direct_llm()
    print(f"Test result: {'SUCCESS' if success else 'FAILED'}")
    sys.exit(0 if success else 1)