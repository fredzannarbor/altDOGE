"""
Prompt management for CFR Document Analyzer.

Manages analysis prompts and prompt packages for different analysis strategies.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .config import Config


logger = logging.getLogger(__name__)


@dataclass
class PromptPackage:
    """Container for a set of analysis prompts."""
    name: str
    description: str
    prompts: List[str]
    version: str = "1.0"
    
    def validate(self) -> bool:
        """Validate the prompt package."""
        if not self.name or not self.prompts:
            return False
        
        # Check that all prompts contain {text} placeholder
        for prompt in self.prompts:
            if '{text}' not in prompt:
                logger.warning(f"Prompt missing {{text}} placeholder: {prompt[:50]}...")
                return False
        
        return True


class PromptManager:
    """Manages analysis prompts and prompt packages."""
    
    def __init__(self):
        """Initialize the prompt manager."""
        self.packages = {}
        self._load_default_packages()
        logger.info("Prompt manager initialized")
    
    def _load_default_packages(self):
        """Load default prompt packages."""
        # DOGE Criteria package for proof of concept
        doge_prompts = [
            """Analyze the following regulation text and categorize it according to DOGE criteria.

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
{text}""",

            """Evaluate the following regulation for potential reform actions. Consider whether it should be:
- DELETED: Regulation serves no useful purpose and should be eliminated
- SIMPLIFIED: Regulation is overly complex and should be streamlined
- HARMONIZED: Regulation conflicts with or duplicates other regulations
- MODERNIZED: Regulation uses outdated processes or terminology

Provide specific recommendations with justifications:

REFORM ACTION: [DELETE/SIMPLIFY/HARMONIZE/MODERNIZE]

SPECIFIC CHANGES:
- [List specific changes needed]

BENEFITS:
- [List expected benefits of the reform]

IMPLEMENTATION:
- [Describe how the reform should be implemented]

Regulation text:
{text}""",

            """Assess the clarity and effectiveness of the following regulation. Identify:
- Ambiguous language that could lead to confusion
- Outdated terminology or processes
- Unnecessary complexity or bureaucratic burden
- Missing elements that would improve compliance

Provide recommendations for improvement:

CLARITY ISSUES:
- [List specific clarity problems]

MODERNIZATION NEEDS:
- [List outdated elements]

SIMPLIFICATION OPPORTUNITIES:
- [List ways to reduce complexity]

RECOMMENDED CHANGES:
- [List specific language or process improvements]

Regulation text:
{text}"""
        ]
        
        doge_package = PromptPackage(
            name="DOGE Criteria",
            description="Department of Government Efficiency analysis criteria for regulation categorization and reform recommendations",
            prompts=doge_prompts
        )
        
        if doge_package.validate():
            self.packages["DOGE Criteria"] = doge_package
            logger.info("Loaded DOGE Criteria prompt package")
        else:
            logger.error("Failed to validate DOGE Criteria prompt package")
    
    def get_prompt_package(self, package_name: str) -> Optional[PromptPackage]:
        """
        Get a prompt package by name.
        
        Args:
            package_name: Name of the prompt package
            
        Returns:
            PromptPackage or None if not found
        """
        package = self.packages.get(package_name)
        if not package:
            logger.warning(f"Prompt package not found: {package_name}")
        return package
    
    def get_available_packages(self) -> List[str]:
        """
        Get list of available prompt package names.
        
        Returns:
            List of package names
        """
        return list(self.packages.keys())
    
    def create_custom_package(self, name: str, description: str, prompts: List[str]) -> bool:
        """
        Create a custom prompt package.
        
        Args:
            name: Package name
            description: Package description
            prompts: List of prompt templates
            
        Returns:
            True if successful, False otherwise
        """
        try:
            package = PromptPackage(
                name=name,
                description=description,
                prompts=prompts
            )
            
            if not package.validate():
                logger.error(f"Custom package validation failed: {name}")
                return False
            
            self.packages[name] = package
            logger.info(f"Created custom prompt package: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating custom package {name}: {e}")
            return False
    
    def load_package_from_file(self, file_path: str) -> bool:
        """
        Load a prompt package from JSON file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"Prompt package file not found: {file_path}")
                return False
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            package = PromptPackage(
                name=data['name'],
                description=data['description'],
                prompts=data['prompts'],
                version=data.get('version', '1.0')
            )
            
            if not package.validate():
                logger.error(f"Package validation failed for file: {file_path}")
                return False
            
            self.packages[package.name] = package
            logger.info(f"Loaded prompt package from file: {package.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading package from {file_path}: {e}")
            return False
    
    def save_package_to_file(self, package_name: str, file_path: str) -> bool:
        """
        Save a prompt package to JSON file.
        
        Args:
            package_name: Name of package to save
            file_path: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            package = self.packages.get(package_name)
            if not package:
                logger.error(f"Package not found: {package_name}")
                return False
            
            data = {
                'name': package.name,
                'description': package.description,
                'prompts': package.prompts,
                'version': package.version
            }
            
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved prompt package to file: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving package to {file_path}: {e}")
            return False
    
    def validate_prompts(self, prompts: List[str]) -> List[str]:
        """
        Validate a list of prompts and return any issues.
        
        Args:
            prompts: List of prompt templates
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not prompts:
            errors.append("No prompts provided")
            return errors
        
        for i, prompt in enumerate(prompts):
            if not prompt or not prompt.strip():
                errors.append(f"Prompt {i+1} is empty")
                continue
            
            if '{text}' not in prompt:
                errors.append(f"Prompt {i+1} missing {{text}} placeholder")
            
            if len(prompt) < 50:
                errors.append(f"Prompt {i+1} seems too short (less than 50 characters)")
            
            if len(prompt) > 5000:
                errors.append(f"Prompt {i+1} seems too long (more than 5000 characters)")
        
        return errors
    
    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a prompt package.
        
        Args:
            package_name: Name of the package
            
        Returns:
            Dictionary with package information or None
        """
        package = self.packages.get(package_name)
        if not package:
            return None
        
        return {
            'name': package.name,
            'description': package.description,
            'version': package.version,
            'prompt_count': len(package.prompts),
            'total_length': sum(len(p) for p in package.prompts)
        }
    
    def format_prompt(self, package_name: str, prompt_index: int, document_text: str) -> Optional[str]:
        """
        Format a specific prompt with document text.
        
        Args:
            package_name: Name of the prompt package
            prompt_index: Index of the prompt to use
            document_text: Document text to insert
            
        Returns:
            Formatted prompt or None if not found
        """
        package = self.packages.get(package_name)
        if not package:
            logger.error(f"Package not found: {package_name}")
            return None
        
        if prompt_index < 0 or prompt_index >= len(package.prompts):
            logger.error(f"Invalid prompt index {prompt_index} for package {package_name}")
            return None
        
        try:
            prompt_template = package.prompts[prompt_index]
            formatted_prompt = prompt_template.format(text=document_text)
            return formatted_prompt
            
        except Exception as e:
            logger.error(f"Error formatting prompt: {e}")
            return None