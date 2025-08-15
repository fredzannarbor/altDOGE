"""
Regulatory submission document generation for CFR Document Analyzer.

Generates formal regulatory submission documents based on analysis and decisions.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from .llm_client import LLMClient
from .prompt_manager import PromptManager
from .agency_response_simulator import AgencyResponse
from .leadership_decision_simulator import LeadershipDecision, DecisionType
from .utils import safe_json_dumps, safe_json_loads, format_timestamp


logger = logging.getLogger(__name__)


@dataclass
class RegulatorySubmission:
    """Regulatory submission document."""
    session_id: str
    submission_type: str  # NPRM, Final Rule, Interim Rule, etc.
    title: str
    summary: str
    background: str
    rule_changes: List[str] = field(default_factory=list)
    response_to_comments: Optional[str] = None
    implementation_details: Optional[str] = None
    compliance_requirements: List[str] = field(default_factory=list)
    effective_date: Optional[datetime] = None
    comment_period_days: int = 60
    regulatory_analysis: Optional[str] = None
    cost_benefit_analysis: Optional[str] = None
    processing_time: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    raw_response: Optional[str] = None

    def __post_init__(self):
        """Set creation timestamp if not provided."""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.effective_date is None:
            # Default to 30 days after creation
            self.effective_date = self.created_at + timedelta(days=30)


class RegulatorySubmissionGenerator:
    """Generates regulatory submission documents."""
    
    def __init__(self, llm_client: LLMClient, prompt_manager: PromptManager):
        """
        Initialize regulatory submission generator.
        
        Args:
            llm_client: LLM client for generating documents
            prompt_manager: Prompt manager for accessing prompts
        """
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        logger.info("Regulatory submission generator initialized")
    
    def generate_nprm(self, 
                     analysis_results: List[Dict[str, Any]],
                     agency_responses: Dict[str, AgencyResponse],
                     leadership_decision: LeadershipDecision,
                     session_id: str,
                     agency_slug: str) -> RegulatorySubmission:
        """
        Generate a Notice of Proposed Rulemaking (NPRM).
        
        Args:
            analysis_results: Original analysis results
            agency_responses: Agency responses
            leadership_decision: Leadership decision
            session_id: Session identifier
            agency_slug: Primary agency for the rule
            
        Returns:
            RegulatorySubmission object
        """
        import time
        start_time = time.time()
        
        try:
            logger.info(f"Generating NPRM for agency {agency_slug}")
            
            # Prepare submission context
            submission_context = self._prepare_submission_context(
                analysis_results, agency_responses, leadership_decision, agency_slug
            )
            
            # Generate NPRM content
            nprm_content = self._generate_regulatory_document(
                submission_context, "NPRM", session_id
            )
            
            if nprm_content:
                # Parse NPRM content
                submission = self._parse_regulatory_submission(
                    nprm_content, session_id, "NPRM"
                )
                submission.processing_time = time.time() - start_time
                submission.raw_response = nprm_content
                
                # Set NPRM-specific properties
                submission.comment_period_days = 60  # Standard NPRM comment period
                submission.effective_date = datetime.now() + timedelta(days=90)  # After comment period
                
                logger.info(f"NPRM generation completed in {submission.processing_time:.2f}s")
                return submission
            else:
                return RegulatorySubmission(
                    session_id=session_id,
                    submission_type="NPRM",
                    title="Failed to Generate NPRM",
                    summary="NPRM generation failed",
                    background="Error in document generation",
                    success=False,
                    error_message="Failed to generate NPRM content",
                    processing_time=time.time() - start_time
                )
                
        except Exception as e:
            logger.error(f"Error generating NPRM: {e}")
            return RegulatorySubmission(
                session_id=session_id,
                submission_type="NPRM",
                title="Error in NPRM Generation",
                summary="NPRM generation encountered an error",
                background="System error during document generation",
                success=False,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    def generate_final_rule(self,
                          analysis_results: List[Dict[str, Any]],
                          agency_responses: Dict[str, AgencyResponse],
                          leadership_decision: LeadershipDecision,
                          public_comments_summary: str,
                          session_id: str,
                          agency_slug: str) -> RegulatorySubmission:
        """
        Generate a Final Rule document.
        
        Args:
            analysis_results: Original analysis results
            agency_responses: Agency responses
            leadership_decision: Leadership decision
            public_comments_summary: Summary of public comments
            session_id: Session identifier
            agency_slug: Primary agency for the rule
            
        Returns:
            RegulatorySubmission object
        """
        import time
        start_time = time.time()
        
        try:
            logger.info(f"Generating Final Rule for agency {agency_slug}")
            
            # Get final rule prompt
            try:
                prompt = self.prompt_manager.get_prompt("Final Rule Drafting", 0)
            except ValueError as e:
                logger.error(f"Final Rule Drafting prompt not available: {e}")
                return RegulatorySubmission(
                    session_id=session_id,
                    submission_type="Final Rule",
                    title="Final Rule Generation Not Available",
                    summary="Final rule generation prompt not available",
                    background="System configuration error",
                    success=False,
                    error_message=str(e),
                    processing_time=time.time() - start_time
                )
            
            # Prepare context for final rule
            analysis_summary = self._prepare_analysis_summary(analysis_results, agency_slug)
            agency_summary = self._format_agency_responses(agency_responses)
            leadership_summary = self._format_leadership_decision(leadership_decision)
            
            # Format prompt with all context
            formatted_prompt = prompt.format(
                analysis_text=analysis_summary,
                agency_text=agency_summary,
                leadership_text=leadership_summary,
                comments_text=public_comments_summary
            )
            
            # Generate final rule using LLM
            response_text, success, error = self.llm_client.analyze_document(
                analysis_summary,
                formatted_prompt,
                f"final_rule_{agency_slug}_{session_id}"
            )
            
            if success:
                # Parse the final rule
                submission = self._parse_regulatory_submission(
                    response_text, session_id, "Final Rule"
                )
                submission.processing_time = time.time() - start_time
                submission.raw_response = response_text
                submission.response_to_comments = public_comments_summary
                
                # Set Final Rule-specific properties
                submission.comment_period_days = 0  # No comment period for final rules
                submission.effective_date = datetime.now() + timedelta(days=30)  # Standard effective date
                
                logger.info(f"Final Rule generation completed in {submission.processing_time:.2f}s")
                return submission
            else:
                logger.error(f"LLM failed to generate final rule: {error}")
                return RegulatorySubmission(
                    session_id=session_id,
                    submission_type="Final Rule",
                    title="Failed to Generate Final Rule",
                    summary="Final rule generation failed",
                    background="LLM generation error",
                    success=False,
                    error_message=error,
                    processing_time=time.time() - start_time
                )
                
        except Exception as e:
            logger.error(f"Error generating Final Rule: {e}")
            return RegulatorySubmission(
                session_id=session_id,
                submission_type="Final Rule",
                title="Error in Final Rule Generation",
                summary="Final rule generation encountered an error",
                background="System error during document generation",
                success=False,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    def _prepare_submission_context(self, 
                                  analysis_results: List[Dict[str, Any]],
                                  agency_responses: Dict[str, AgencyResponse],
                                  leadership_decision: LeadershipDecision,
                                  agency_slug: str) -> str:
        """
        Prepare context for regulatory submission generation.
        
        Args:
            analysis_results: Analysis results
            agency_responses: Agency responses
            leadership_decision: Leadership decision
            agency_slug: Agency identifier
            
        Returns:
            Formatted submission context
        """
        context_parts = [
            f"REGULATORY SUBMISSION CONTEXT FOR {agency_slug.upper().replace('-', ' ')}",
            "=" * 60,
            "",
            "ANALYSIS SUMMARY:",
            self._prepare_analysis_summary(analysis_results, agency_slug),
            "",
            "AGENCY RESPONSES:",
            self._format_agency_responses(agency_responses),
            "",
            "LEADERSHIP DECISION:",
            self._format_leadership_decision(leadership_decision)
        ]
        
        return "\n".join(context_parts)
    
    def _prepare_analysis_summary(self, analysis_results: List[Dict[str, Any]], agency_slug: str) -> str:
        """
        Prepare analysis summary for submission context.
        
        Args:
            analysis_results: List of analysis results
            agency_slug: Agency identifier
            
        Returns:
            Formatted analysis summary
        """
        # Filter results for the specific agency
        agency_results = [
            result for result in analysis_results 
            if result.get('agency_slug') == agency_slug
        ]
        
        if not agency_results:
            return f"No analysis results available for {agency_slug}"
        
        summary_parts = [
            f"Total Documents Analyzed: {len(agency_results)}",
            ""
        ]
        
        # Categorize results
        categories = {}
        all_recommendations = []
        
        for result in agency_results:
            analysis = result.get('analysis', {})
            category = analysis.get('category', 'UNKNOWN')
            categories[category] = categories.get(category, 0) + 1
            
            # Collect recommendations
            recommendations = analysis.get('reform_recommendations', [])
            if isinstance(recommendations, str):
                recommendations = safe_json_loads(recommendations, [])
            all_recommendations.extend(recommendations)
        
        # Add category breakdown
        summary_parts.append("DOCUMENT CATEGORIZATION:")
        for category, count in categories.items():
            category_name = {
                'SR': 'Statutorily Required',
                'NSR': 'Not Statutorily Required', 
                'NRAN': 'Not Required but Agency Needs',
                'UNKNOWN': 'Requires Further Analysis'
            }.get(category, category)
            percentage = (count / len(agency_results)) * 100
            summary_parts.append(f"  - {category_name}: {count} documents ({percentage:.1f}%)")
        
        summary_parts.append("")
        
        # Add reform recommendations
        if all_recommendations:
            summary_parts.append("KEY REFORM RECOMMENDATIONS:")
            unique_recommendations = list(set(all_recommendations))
            for i, rec in enumerate(unique_recommendations[:10], 1):  # Limit to top 10
                summary_parts.append(f"  {i}. {rec}")
        
        return "\n".join(summary_parts)
    
    def _format_agency_responses(self, agency_responses: Dict[str, AgencyResponse]) -> str:
        """
        Format agency responses for submission context.
        
        Args:
            agency_responses: Dictionary of agency responses
            
        Returns:
            Formatted agency responses text
        """
        if not agency_responses:
            return "No agency responses available."
        
        formatted_parts = []
        
        for agency_slug, response in agency_responses.items():
            agency_name = agency_slug.replace('-', ' ').title()
            
            agency_section = [
                f"{agency_name}:",
                f"  Position: {response.agency_position}",
                f"  Concerns: {len(response.concerns)} identified",
                f"  Counter-proposals: {len(response.counter_proposals)} provided"
            ]
            
            formatted_parts.extend(agency_section)
        
        return "\n".join(formatted_parts)
    
    def _format_leadership_decision(self, leadership_decision: LeadershipDecision) -> str:
        """
        Format leadership decision for submission context.
        
        Args:
            leadership_decision: Leadership decision object
            
        Returns:
            Formatted leadership decision text
        """
        decision_parts = [
            f"Decision Type: {leadership_decision.decision_type.value.title()}",
            f"Rationale: {leadership_decision.rationale}",
            f"Directives: {len(leadership_decision.directives)} provided",
            f"Priorities: {len(leadership_decision.priorities)} identified"
        ]
        
        if leadership_decision.timeline:
            decision_parts.append(f"Timeline: {leadership_decision.timeline}")
        
        return "\n".join(decision_parts)
    
    def _generate_regulatory_document(self, context: str, doc_type: str, session_id: str) -> Optional[str]:
        """
        Generate regulatory document content using LLM.
        
        Args:
            context: Document context
            doc_type: Document type (NPRM, Final Rule, etc.)
            session_id: Session identifier
            
        Returns:
            Generated document content or None if failed
        """
        try:
            # Create a basic regulatory document prompt
            prompt = f"""Generate a {doc_type} document based on the following regulatory analysis context.

CONTEXT:
{context}

Please provide a well-structured {doc_type} document with the following sections:

SUMMARY:
[Brief summary of the proposed rule]

BACKGROUND:
[Background and rationale for the rule]

RULE CHANGES:
[Specific regulatory changes being proposed]

IMPLEMENTATION:
[Implementation details and timeline]

COMPLIANCE:
[Compliance requirements and enforcement]

REGULATORY ANALYSIS:
[Analysis of regulatory impact]

Please format the response clearly with section headers."""
            
            response_text, success, error = self.llm_client.analyze_document(
                context,
                prompt,
                f"{doc_type.lower()}_{session_id}"
            )
            
            if success:
                return response_text
            else:
                logger.error(f"Failed to generate {doc_type}: {error}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating {doc_type}: {e}")
            return None
    
    def _parse_regulatory_submission(self, response_text: str, session_id: str, submission_type: str) -> RegulatorySubmission:
        """
        Parse regulatory submission from LLM output.
        
        Args:
            response_text: Raw LLM response
            session_id: Session identifier
            submission_type: Type of submission
            
        Returns:
            Parsed RegulatorySubmission object
        """
        import re
        
        try:
            # Extract sections using regex
            summary_match = re.search(r'SUMMARY:(.*?)(?=BACKGROUND:|$)', response_text, re.DOTALL | re.IGNORECASE)
            background_match = re.search(r'BACKGROUND:(.*?)(?=RULE CHANGES:|$)', response_text, re.DOTALL | re.IGNORECASE)
            rule_changes_match = re.search(r'RULE CHANGES:(.*?)(?=IMPLEMENTATION:|$)', response_text, re.DOTALL | re.IGNORECASE)
            implementation_match = re.search(r'IMPLEMENTATION:(.*?)(?=COMPLIANCE:|$)', response_text, re.DOTALL | re.IGNORECASE)
            compliance_match = re.search(r'COMPLIANCE:(.*?)(?=REGULATORY ANALYSIS:|$)', response_text, re.DOTALL | re.IGNORECASE)
            analysis_match = re.search(r'REGULATORY ANALYSIS:(.*?)$', response_text, re.DOTALL | re.IGNORECASE)
            
            # Create submission object
            submission = RegulatorySubmission(
                session_id=session_id,
                submission_type=submission_type,
                title=f"{submission_type} - Generated Document",
                summary=summary_match.group(1).strip() if summary_match else "Summary not available",
                background=background_match.group(1).strip() if background_match else "Background not available"
            )
            
            # Extract rule changes
            if rule_changes_match:
                rule_changes_text = rule_changes_match.group(1)
                rule_changes = re.findall(r'[•\-\d]\s*(.+)', rule_changes_text)
                submission.rule_changes = [change.strip() for change in rule_changes if change.strip()]
            
            # Extract implementation details
            if implementation_match:
                submission.implementation_details = implementation_match.group(1).strip()
            
            # Extract compliance requirements
            if compliance_match:
                compliance_text = compliance_match.group(1)
                compliance_reqs = re.findall(r'[•\-\d]\s*(.+)', compliance_text)
                submission.compliance_requirements = [req.strip() for req in compliance_reqs if req.strip()]
            
            # Extract regulatory analysis
            if analysis_match:
                submission.regulatory_analysis = analysis_match.group(1).strip()
            
            return submission
            
        except Exception as e:
            logger.error(f"Error parsing regulatory submission: {e}")
            return RegulatorySubmission(
                session_id=session_id,
                submission_type=submission_type,
                title="Error Parsing Document",
                summary="Error occurred while parsing regulatory submission",
                background="System error during document parsing",
                success=False,
                error_message=str(e)
            )
    
    def export_regulatory_submission(self, submission: RegulatorySubmission, output_path: str) -> bool:
        """
        Export regulatory submission to file.
        
        Args:
            submission: RegulatorySubmission object
            output_path: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create formal regulatory document format
            content = f"""# {submission.submission_type}: {submission.title}

**Session ID:** {submission.session_id}  
**Document Type:** {submission.submission_type}  
**Generated:** {submission.created_at.strftime('%Y-%m-%d %H:%M:%S') if submission.created_at else 'Unknown'}  
**Effective Date:** {submission.effective_date.strftime('%Y-%m-%d') if submission.effective_date else 'TBD'}  
**Comment Period:** {submission.comment_period_days} days

## Summary

{submission.summary}

## Background and Rationale

{submission.background}

## Proposed Rule Changes

"""
            
            if submission.rule_changes:
                for i, change in enumerate(submission.rule_changes, 1):
                    content += f"{i}. {change}\n"
            else:
                content += "No specific rule changes identified.\n"
            
            if submission.implementation_details:
                content += f"\n## Implementation Details\n\n{submission.implementation_details}\n"
            
            content += "\n## Compliance Requirements\n\n"
            
            if submission.compliance_requirements:
                for i, req in enumerate(submission.compliance_requirements, 1):
                    content += f"{i}. {req}\n"
            else:
                content += "Compliance requirements to be determined.\n"
            
            if submission.regulatory_analysis:
                content += f"\n## Regulatory Analysis\n\n{submission.regulatory_analysis}\n"
            
            if submission.response_to_comments:
                content += f"\n## Response to Public Comments\n\n{submission.response_to_comments}\n"
            
            if submission.cost_benefit_analysis:
                content += f"\n## Cost-Benefit Analysis\n\n{submission.cost_benefit_analysis}\n"
            
            content += f"\n## Document Generation Details\n\n"
            content += f"- **Processing Time:** {submission.processing_time:.2f} seconds\n"
            content += f"- **Success:** {'Yes' if submission.success else 'No'}\n"
            
            if submission.error_message:
                content += f"- **Error:** {submission.error_message}\n"
            
            if submission.raw_response:
                content += f"\n## Raw Generated Content\n\n```\n{submission.raw_response}\n```\n"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Exported regulatory submission to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting regulatory submission: {e}")
            return False
    
    def generate_multiple_submissions(self,
                                    analysis_results: List[Dict[str, Any]],
                                    agency_responses: Dict[str, AgencyResponse],
                                    leadership_decision: LeadershipDecision,
                                    session_id: str,
                                    submission_types: List[str]) -> Dict[str, RegulatorySubmission]:
        """
        Generate multiple types of regulatory submissions.
        
        Args:
            analysis_results: Analysis results
            agency_responses: Agency responses
            leadership_decision: Leadership decision
            session_id: Session identifier
            submission_types: List of submission types to generate
            
        Returns:
            Dictionary mapping submission type to RegulatorySubmission
        """
        logger.info(f"Generating {len(submission_types)} regulatory submissions")
        
        submissions = {}
        
        # Get primary agency from results
        primary_agency = None
        if analysis_results:
            primary_agency = analysis_results[0].get('agency_slug', 'unknown-agency')
        
        for submission_type in submission_types:
            if submission_type.upper() == "NPRM":
                submission = self.generate_nprm(
                    analysis_results, agency_responses, leadership_decision, 
                    session_id, primary_agency
                )
            elif submission_type.upper() == "FINAL RULE":
                # For final rule, we need public comments summary
                public_comments = "Public comments analysis not yet implemented."
                submission = self.generate_final_rule(
                    analysis_results, agency_responses, leadership_decision,
                    public_comments, session_id, primary_agency
                )
            else:
                # Generic regulatory document
                submission_context = self._prepare_submission_context(
                    analysis_results, agency_responses, leadership_decision, primary_agency
                )
                doc_content = self._generate_regulatory_document(
                    submission_context, submission_type, session_id
                )
                
                if doc_content:
                    submission = self._parse_regulatory_submission(
                        doc_content, session_id, submission_type
                    )
                else:
                    submission = RegulatorySubmission(
                        session_id=session_id,
                        submission_type=submission_type,
                        title=f"Failed to Generate {submission_type}",
                        summary=f"{submission_type} generation failed",
                        background="Error in document generation",
                        success=False,
                        error_message="Failed to generate document content"
                    )
            
            submissions[submission_type] = submission
        
        return submissions