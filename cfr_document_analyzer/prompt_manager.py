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
        
        # Meta-analysis prompts for synthesizing multiple document analyses
        meta_analysis_prompts = [
            """You are analyzing a collection of regulatory document analyses to provide strategic insights and recommendations.

Based on the following analysis results, provide a comprehensive meta-analysis that synthesizes patterns, identifies key themes, and recommends strategic actions.

ANALYSIS RESULTS:
{text}

Provide your meta-analysis in the following structured format:

KEY PATTERNS:
- [List 3-5 major patterns observed across the analyzed documents]

STRATEGIC THEMES:
- [Identify 3-5 overarching themes that emerge from the analysis]

PRIORITY ACTIONS:
- [List 5-7 specific actions ranked by priority and impact]

GOAL ALIGNMENT:
- [Assess how well current regulations align with stated policy goals]

IMPLEMENTATION ROADMAP:
- [Provide a high-level roadmap for implementing recommended changes]

SUMMARY:
[Provide a 2-3 sentence executive summary of the most critical findings]""",

            """Analyze the following regulatory analysis results to identify reform opportunities and potential challenges.

ANALYSIS DATA:
{text}

Focus on providing actionable insights in this format:

REFORM OPPORTUNITIES:
• [List specific opportunities for regulatory reform with expected impact]

IMPLEMENTATION CHALLENGES:
• [Identify potential obstacles and resistance points]

STAKEHOLDER IMPACT:
• [Assess impact on different stakeholder groups]

RESOURCE REQUIREMENTS:
• [Estimate resources needed for implementation]

RISK ASSESSMENT:
• [Identify key risks and mitigation strategies]

QUICK WINS:
• [List actions that can be implemented quickly with high impact]

LONG-TERM STRATEGY:
• [Outline strategic approach for comprehensive reform]"""
        ]
        
        meta_package = PromptPackage(
            name="Meta-Analysis",
            description="Meta-analysis prompts for synthesizing multiple document analyses and providing strategic insights",
            prompts=meta_analysis_prompts
        )
        
        if meta_package.validate():
            self.packages["Meta-Analysis"] = meta_package
            logger.info("Loaded Meta-Analysis prompt package")
        else:
            logger.error("Failed to validate Meta-Analysis prompt package")
        
        # Blue Dreams prompt package
        blue_dreams_prompts = [
            """Analyze the following regulation through the lens of the Blue Dreams framework, focusing on innovation, efficiency, and citizen-centric governance.

Evaluate how this regulation:
- Promotes or hinders innovation and technological advancement
- Supports efficient government operations
- Serves citizen needs and improves public outcomes
- Aligns with modern governance principles

Provide your analysis in this format:

INNOVATION IMPACT:
- [Assess impact on innovation and technology adoption]

EFFICIENCY ASSESSMENT:
- [Evaluate operational efficiency and resource utilization]

CITIZEN BENEFIT:
- [Analyze benefits and burdens for citizens and businesses]

MODERNIZATION OPPORTUNITIES:
- [Identify specific opportunities for improvement]

BLUE DREAMS SCORE: [1-10 scale where 10 = fully aligned with Blue Dreams principles]

RECOMMENDATIONS:
- [List specific recommendations for alignment with Blue Dreams vision]

Regulation text:
{text}""",

            """Evaluate this regulation's alignment with Blue Dreams principles of streamlined, technology-enabled government that serves citizens effectively.

Focus on:
- Digital transformation opportunities
- Bureaucratic burden reduction
- Stakeholder experience improvement
- Data-driven decision making

Provide recommendations in this format:

DIGITAL TRANSFORMATION:
- [Opportunities for digital solutions and automation]

BURDEN REDUCTION:
- [Ways to reduce bureaucratic complexity]

USER EXPERIENCE:
- [Improvements for citizen/business interactions]

DATA UTILIZATION:
- [Better use of data for decision making]

IMPLEMENTATION ROADMAP:
- [Practical steps for Blue Dreams alignment]

Regulation text:
{text}"""
        ]
        
        blue_dreams_package = PromptPackage(
            name="Blue Dreams",
            description="Blue Dreams framework for innovation-focused, citizen-centric governance analysis",
            prompts=blue_dreams_prompts
        )
        
        if blue_dreams_package.validate():
            self.packages["Blue Dreams"] = blue_dreams_package
            logger.info("Loaded Blue Dreams prompt package")
        else:
            logger.error("Failed to validate Blue Dreams prompt package")
        
        # EO 14219 prompt package
        eo_14219_prompts = [
            """Analyze this regulation in the context of Executive Order 14219 on Advancing Effective, Accountable, and Transparent Government.

Evaluate compliance with EO 14219 principles:
- Transparency and public participation
- Accountability and performance measurement
- Effectiveness and evidence-based policy
- Equity and accessibility

Provide analysis in this format:

TRANSPARENCY ASSESSMENT:
- [Evaluate transparency and public access to information]

ACCOUNTABILITY MEASURES:
- [Assess accountability mechanisms and performance metrics]

EFFECTIVENESS EVALUATION:
- [Analyze evidence base and policy effectiveness]

EQUITY CONSIDERATIONS:
- [Review equity impacts and accessibility]

EO 14219 COMPLIANCE SCORE: [1-10 scale]

IMPROVEMENT RECOMMENDATIONS:
- [Specific recommendations for better EO 14219 alignment]

Regulation text:
{text}""",

            """Review this regulation for alignment with Executive Order 14219's requirements for effective, accountable, and transparent government operations.

Focus on:
- Public engagement and participation opportunities
- Performance measurement and evaluation
- Evidence-based policy development
- Equitable access and outcomes

Analysis format:

PUBLIC ENGAGEMENT:
- [Assessment of public participation mechanisms]

PERFORMANCE METRICS:
- [Evaluation of measurement and accountability systems]

EVIDENCE BASE:
- [Review of supporting evidence and data]

EQUITY ANALYSIS:
- [Assessment of equitable access and outcomes]

COMPLIANCE GAPS:
- [Identification of areas needing improvement]

ACTION PLAN:
- [Specific steps for enhanced EO 14219 compliance]

Regulation text:
{text}"""
        ]
        
        eo_14219_package = PromptPackage(
            name="EO 14219",
            description="Executive Order 14219 analysis for effective, accountable, and transparent government",
            prompts=eo_14219_prompts
        )
        
        if eo_14219_package.validate():
            self.packages["EO 14219"] = eo_14219_package
            logger.info("Loaded EO 14219 prompt package")
        else:
            logger.error("Failed to validate EO 14219 prompt package")
        
        # Technical Competence prompt package
        technical_competence_prompts = [
            """Analyze this regulation from a technical competence perspective, evaluating the technical accuracy, feasibility, and implementation requirements.

Assess:
- Technical accuracy and scientific validity
- Implementation feasibility and resource requirements
- Compliance monitoring and enforcement mechanisms
- Industry best practices alignment

Provide analysis in this format:

TECHNICAL ACCURACY:
- [Evaluation of technical and scientific validity]

IMPLEMENTATION FEASIBILITY:
- [Assessment of practical implementation challenges]

RESOURCE REQUIREMENTS:
- [Analysis of human, financial, and technical resources needed]

COMPLIANCE MECHANISMS:
- [Review of monitoring and enforcement approaches]

INDUSTRY ALIGNMENT:
- [Comparison with industry standards and best practices]

TECHNICAL COMPETENCE SCORE: [1-10 scale]

TECHNICAL RECOMMENDATIONS:
- [Specific technical improvements and considerations]

Regulation text:
{text}""",

            """Evaluate this regulation's technical merit, implementation practicality, and alignment with established technical standards and best practices.

Focus on:
- Scientific and technical foundation
- Practical implementation considerations
- Resource and capability requirements
- Measurable outcomes and success criteria

Analysis format:

TECHNICAL FOUNDATION:
- [Assessment of underlying technical/scientific basis]

IMPLEMENTATION ANALYSIS:
- [Practical considerations for implementation]

CAPABILITY REQUIREMENTS:
- [Skills, systems, and resources needed]

SUCCESS METRICS:
- [Measurable outcomes and evaluation criteria]

RISK ASSESSMENT:
- [Technical and implementation risks]

OPTIMIZATION OPPORTUNITIES:
- [Ways to improve technical effectiveness]

Regulation text:
{text}"""
        ]
        
        technical_competence_package = PromptPackage(
            name="Technical Competence",
            description="Technical competence analysis focusing on accuracy, feasibility, and best practices",
            prompts=technical_competence_prompts
        )
        
        if technical_competence_package.validate():
            self.packages["Technical Competence"] = technical_competence_package
            logger.info("Loaded Technical Competence prompt package")
        else:
            logger.error("Failed to validate Technical Competence prompt package")
    
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
    
    def create_custom_prompt_package(self, name: str, description: str, prompts: List[str], 
                                   version: str = "1.0") -> bool:
        """
        Create a custom prompt package with validation.
        
        Args:
            name: Package name
            description: Package description
            prompts: List of prompt templates
            version: Package version
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate inputs
            if not name or not description or not prompts:
                logger.error("Name, description, and prompts are required")
                return False
            
            # Check if package already exists
            if name in self.packages:
                logger.warning(f"Package '{name}' already exists. Use update_package to modify.")
                return False
            
            # Validate prompts
            validation_errors = self.validate_prompts(prompts)
            if validation_errors:
                logger.error(f"Prompt validation failed: {validation_errors}")
                return False
            
            # Create package
            package = PromptPackage(
                name=name,
                description=description,
                prompts=prompts,
                version=version
            )
            
            if package.validate():
                self.packages[name] = package
                logger.info(f"Created custom prompt package: {name}")
                return True
            else:
                logger.error(f"Package validation failed for: {name}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating custom package {name}: {e}")
            return False
    
    def update_package(self, package_name: str, **updates) -> bool:
        """
        Update an existing prompt package.
        
        Args:
            package_name: Name of package to update
            **updates: Fields to update (description, prompts, version)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if package_name not in self.packages:
                logger.error(f"Package not found: {package_name}")
                return False
            
            package = self.packages[package_name]
            
            # Update fields
            if 'description' in updates:
                package.description = updates['description']
            
            if 'version' in updates:
                package.version = updates['version']
            
            if 'prompts' in updates:
                new_prompts = updates['prompts']
                validation_errors = self.validate_prompts(new_prompts)
                if validation_errors:
                    logger.error(f"Prompt validation failed: {validation_errors}")
                    return False
                package.prompts = new_prompts
            
            # Validate updated package
            if package.validate():
                logger.info(f"Updated prompt package: {package_name}")
                return True
            else:
                logger.error(f"Package validation failed after update: {package_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating package {package_name}: {e}")
            return False
    
    def delete_package(self, package_name: str) -> bool:
        """
        Delete a prompt package.
        
        Args:
            package_name: Name of package to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prevent deletion of core packages
            core_packages = ["DOGE Criteria", "Meta-Analysis"]
            if package_name in core_packages:
                logger.error(f"Cannot delete core package: {package_name}")
                return False
            
            if package_name in self.packages:
                del self.packages[package_name]
                logger.info(f"Deleted prompt package: {package_name}")
                return True
            else:
                logger.warning(f"Package not found: {package_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting package {package_name}: {e}")
            return False
    
    def test_prompt_package(self, package_name: str, test_text: str = None) -> Dict[str, Any]:
        """
        Test a prompt package with sample text.
        
        Args:
            package_name: Name of package to test
            test_text: Sample text for testing (optional)
            
        Returns:
            Dictionary with test results
        """
        try:
            package = self.packages.get(package_name)
            if not package:
                return {'success': False, 'error': f'Package not found: {package_name}'}
            
            test_text = test_text or "This is a sample regulation for testing prompt formatting."
            
            test_results = {
                'success': True,
                'package_name': package_name,
                'prompt_count': len(package.prompts),
                'formatted_prompts': []
            }
            
            # Test each prompt
            for i, prompt in enumerate(package.prompts):
                try:
                    formatted = prompt.format(text=test_text)
                    test_results['formatted_prompts'].append({
                        'prompt_index': i,
                        'length': len(formatted),
                        'success': True,
                        'preview': formatted[:200] + "..." if len(formatted) > 200 else formatted
                    })
                except Exception as e:
                    test_results['formatted_prompts'].append({
                        'prompt_index': i,
                        'success': False,
                        'error': str(e)
                    })
            
            return test_results
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def export_package_to_dict(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Export a package to dictionary format.
        
        Args:
            package_name: Name of package to export
            
        Returns:
            Package dictionary or None
        """
        package = self.packages.get(package_name)
        if not package:
            return None
        
        return {
            'name': package.name,
            'description': package.description,
            'version': package.version,
            'prompts': package.prompts,
            'exported_at': datetime.now().isoformat()
        }
    
    def import_package_from_dict(self, package_data: Dict[str, Any]) -> bool:
        """
        Import a package from dictionary format.
        
        Args:
            package_data: Package data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            required_fields = ['name', 'description', 'prompts']
            for field in required_fields:
                if field not in package_data:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            return self.create_custom_prompt_package(
                name=package_data['name'],
                description=package_data['description'],
                prompts=package_data['prompts'],
                version=package_data.get('version', '1.0')
            )
            
        except Exception as e:
            logger.error(f"Error importing package: {e}")
            return False
    
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