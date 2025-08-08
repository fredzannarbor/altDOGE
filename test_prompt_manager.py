#!/usr/bin/env python3
"""
Test script for prompt manager functionality.
"""

import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cfr_document_analyzer.config import Config
from cfr_document_analyzer.prompt_manager import PromptManager, PromptPackage


def test_prompt_manager():
    """Test prompt manager functionality."""
    # Set up logging
    Config.setup_logging(verbose=True)
    logger = logging.getLogger(__name__)
    
    logger.info("Testing prompt manager...")
    
    try:
        # Test initialization
        manager = PromptManager()
        logger.info("✓ Prompt manager initialization passed")
        
        # Test getting available packages
        packages = manager.get_available_packages()
        assert "DOGE Criteria" in packages
        logger.info(f"✓ Available packages: {packages}")
        
        # Test getting a specific package
        doge_package = manager.get_prompt_package("DOGE Criteria")
        assert doge_package is not None
        assert len(doge_package.prompts) == 3
        logger.info(f"✓ DOGE package loaded with {len(doge_package.prompts)} prompts")
        
        # Test package validation
        assert doge_package.validate()
        logger.info("✓ Package validation passed")
        
        # Test prompt formatting
        test_text = "This is a test regulation about credit union operations."
        formatted_prompt = manager.format_prompt("DOGE Criteria", 0, test_text)
        assert formatted_prompt is not None
        assert test_text in formatted_prompt
        assert "CATEGORY:" in formatted_prompt
        logger.info("✓ Prompt formatting passed")
        
        # Test package info
        info = manager.get_package_info("DOGE Criteria")
        assert info is not None
        assert info['name'] == "DOGE Criteria"
        assert info['prompt_count'] == 3
        logger.info(f"✓ Package info: {info}")
        
        # Test prompt validation
        valid_prompts = ["This is a valid prompt with {text} placeholder that is long enough to pass the minimum length validation requirement."]
        invalid_prompts = ["This prompt is missing the placeholder."]
        
        valid_errors = manager.validate_prompts(valid_prompts)
        invalid_errors = manager.validate_prompts(invalid_prompts)
        
        logger.info(f"Valid prompt errors: {valid_errors}")
        logger.info(f"Invalid prompt errors: {invalid_errors}")
        
        assert len(valid_errors) == 0, f"Expected no errors for valid prompts, got: {valid_errors}"
        assert len(invalid_errors) > 0, f"Expected errors for invalid prompts, got: {invalid_errors}"
        logger.info("✓ Prompt validation tests passed")
        
        # Test custom package creation
        custom_prompts = [
            "Analyze this regulation for compliance issues: {text}",
            "Review this regulation for cost-benefit analysis: {text}"
        ]
        
        success = manager.create_custom_package(
            "Test Package",
            "A test package for validation",
            custom_prompts
        )
        assert success
        assert "Test Package" in manager.get_available_packages()
        logger.info("✓ Custom package creation passed")
        
        logger.info("All prompt manager tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"Prompt manager test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_prompt_manager()
    print(f"Test result: {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)