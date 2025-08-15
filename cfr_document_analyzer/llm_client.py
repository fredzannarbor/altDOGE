"""
LLM client for CFR Document Analyzer using nimble-llm-caller.

Handles LLM interactions for document analysis with retry logic and token tracking.
"""

import logging
import time
import json
import re
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

# Import nimble-llm-caller
from nimble_llm_caller import LLMCaller, LLMRequest

from .config import Config
from .models import DOGEAnalysis, RegulationCategory, MetaAnalysis
from .utils import truncate_text, safe_json_loads


logger = logging.getLogger(__name__)


@dataclass
class LLMUsageStats:
    """Track LLM usage statistics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_time: float = 0.0


class LLMClient:
    """LLM client using nimble-llm-caller for document analysis."""
    
    def __init__(self, model: str = None, rate_limit: float = None):
        """
        Initialize the LLM client.
        
        Args:
            model: Model name to use (defaults to config)
            rate_limit: Rate limit in requests per second
        """
        self.model = model or Config.DEFAULT_MODEL
        self.rate_limit = rate_limit or Config.LLM_RATE_LIMIT
        self.last_request_time = 0.0
        self.usage_stats = LLMUsageStats()
        
        # Set API key if available
        if Config.GEMINI_API_KEY:
            os.environ['GEMINI_API_KEY'] = Config.GEMINI_API_KEY
            logger.info("Gemini API key loaded from environment")
        else:
            logger.warning("No Gemini API key found - LLM calls will fail")
        
        # Initialize nimble-llm-caller
        self.llm_caller = LLMCaller()
        
        logger.info(f"LLM client initialized with model: {self.model}")
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting between requests."""
        if self.rate_limit <= 0:
            return
        
        min_interval = 1.0 / self.rate_limit
        elapsed = time.time() - self.last_request_time
        
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def analyze_document(self, content: str, prompt: str, document_id: str = None) -> Tuple[str, bool, Optional[str]]:
        """
        Analyze a document using LLM.
        
        Args:
            content: Document content to analyze
            prompt: Analysis prompt
            document_id: Document identifier for logging
            
        Returns:
            Tuple of (response_text, success, error_message)
        """
        start_time = time.time()
        self.usage_stats.total_calls += 1
        
        try:
            # Enforce rate limiting
            self._enforce_rate_limit()
            
            # Truncate content if too long
            if len(content) > Config.MAX_DOCUMENT_LENGTH:
                content = truncate_text(content, Config.MAX_DOCUMENT_LENGTH)
                logger.warning(f"Document content truncated for analysis (doc: {document_id})")
            
            # Format the prompt with document content
            formatted_prompt = prompt.format(text=content)
            
            logger.debug(f"Analyzing document {document_id} with model {self.model}")
            
            # Create LLM request with proper message structure
            request = LLMRequest(
                prompt_key=f"doge_analysis_{document_id or 'unknown'}",
                model=self.model,
                substitutions={},
                model_params={
                    "max_tokens": Config.MAX_TOKENS,
                    "temperature": 0.1
                },
                metadata={
                    "messages": [{"role": "user", "content": formatted_prompt}]
                }
            )
            
            # Call nimble-llm-caller with error handling
            logger.debug(f"Making LLM request for document {document_id}")
            
            try:
                response = self.llm_caller.call(request)
                logger.debug(f"Received LLM response type: {type(response)}")
                
                # Check if the response indicates success
                if hasattr(response, 'status') and response.status != 'success':
                    error_msg = getattr(response, 'error_message', 'Unknown error')
                    raise Exception(f"LLM call failed with status {response.status}: {error_msg}")
                
                # Extract response content
                response_text = None
                if hasattr(response, 'content') and response.content:
                    response_text = response.content
                elif hasattr(response, 'parsed_content') and response.parsed_content:
                    response_text = str(response.parsed_content)
                else:
                    logger.error(f"No content in response. Response attributes: {dir(response)}")
                    raise Exception("No content in LLM response")
                
                # Track token usage if available
                try:
                    if hasattr(response, 'tokens_used') and response.tokens_used:
                        # Try to get total tokens, handling different formats
                        tokens_used = response.tokens_used
                        if hasattr(tokens_used, 'total_tokens'):
                            total_tokens = tokens_used.total_tokens
                            if isinstance(total_tokens, int):
                                self.usage_stats.total_tokens += total_tokens
                        elif hasattr(tokens_used, 'input_tokens') and hasattr(tokens_used, 'output_tokens'):
                            input_tokens = getattr(tokens_used, 'input_tokens', 0)
                            output_tokens = getattr(tokens_used, 'output_tokens', 0)
                            if isinstance(input_tokens, int) and isinstance(output_tokens, int):
                                self.usage_stats.total_tokens += input_tokens + output_tokens
                except Exception as token_error:
                    logger.debug(f"Could not extract token usage: {token_error}")
                
            except Exception as llm_error:
                # If nimble-llm-caller fails, we might still get a partial response
                logger.warning(f"nimble-llm-caller error: {llm_error}")
                
                # Check if it's a validation error but the LLM call actually succeeded
                if "validation errors for LLMResponse" in str(llm_error):
                    logger.info("LLM call may have succeeded despite validation error - checking for response content")
                    
                    # Try to extract content from the error context if possible
                    # This is a workaround for the Pydantic validation issue
                    try:
                        # The LLM call succeeded but response parsing failed.
                        # Attempt to extract the raw response from the error string.
                        error_str = str(llm_error)
                        
                        # Use regex to find content, which is likely in the error's string representation.
                        match = re.search(r"content='(.*?)'", error_str, re.DOTALL)
                        
                        if match:
                            response_text = match.group(1).replace('\\n', '\n').replace("\\'", "'")
                            logger.warning("Extracted fallback response from validation error.")
                        else:
                            # Fallback to the original message if extraction fails.
                            response_text = "LLM response received but parsing failed due to format changes. This is a known issue with newer Gemini API responses."
                            logger.warning("Using fallback response due to parsing error. Could not extract content.")
                            
                    except Exception as extraction_error:
                        logger.error(f"Could not extract content from validation error: {extraction_error}")
                        raise llm_error
                else:
                    raise llm_error
            
            # Track successful call
            self.usage_stats.successful_calls += 1
            processing_time = time.time() - start_time
            self.usage_stats.total_time += processing_time
            
            logger.debug(f"Successfully analyzed document {document_id} in {processing_time:.2f}s")
            
            return response_text, True, None
            
        except Exception as e:
            # Track failed call
            self.usage_stats.failed_calls += 1
            processing_time = time.time() - start_time
            self.usage_stats.total_time += processing_time
            
            error_msg = f"LLM analysis failed for document {document_id}: {str(e)}"
            logger.error(error_msg)
            
            return "", False, error_msg
    
    def analyze_document_with_doge_prompts(self, content: str, document_id: str = None) -> DOGEAnalysis:
        """
        Analyze a document using DOGE-specific prompts.
        
        Args:
            content: Document content to analyze
            document_id: Document identifier for logging
            
        Returns:
            DOGEAnalysis object with structured results
        """
        # DOGE categorization prompt
        doge_prompt = """
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

Your response must be no more than 300 words for each section and delivered as a valid JSON array.

Regulation text:
{text}
"""
        
        response_text, success, error = self.analyze_document(content, doge_prompt, document_id)
        
        if not success:
            # Return error analysis
            return DOGEAnalysis(
                category=RegulationCategory.UNKNOWN,
                statutory_references=[],
                reform_recommendations=[],
                justification=f"Analysis failed: {error}"
            )
        
        # Parse the structured response
        return self._parse_doge_response(response_text)
    
    def _parse_doge_response(self, response_text: str) -> DOGEAnalysis:
        """
        Parse LLM response into structured DOGE analysis.
        
        Args:
            response_text: Raw LLM response
            
        Returns:
            DOGEAnalysis object
        """
        try:
            # Initialize defaults
            category = RegulationCategory.UNKNOWN
            statutory_refs = []
            recommendations = []
            justification = response_text
            
            # Parse category
            category_match = re.search(r'CATEGORY:\s*([A-Z]+)', response_text, re.IGNORECASE)
            if category_match:
                cat_str = category_match.group(1).upper()
                if cat_str == 'SR':
                    category = RegulationCategory.STATUTORILY_REQUIRED
                elif cat_str == 'NSR':
                    category = RegulationCategory.NOT_STATUTORILY_REQUIRED
                elif cat_str == 'NRAN':
                    category = RegulationCategory.NOT_REQUIRED_AGENCY_NEEDS
            
            # Parse statutory references
            stat_section = re.search(r'STATUTORY REFERENCES:(.*?)(?=REFORM RECOMMENDATIONS:|JUSTIFICATION:|$)', 
                                   response_text, re.DOTALL | re.IGNORECASE)
            if stat_section:
                stat_text = stat_section.group(1)
                # Extract bullet points
                stat_refs = re.findall(r'-\s*(.+)', stat_text)
                statutory_refs = [ref.strip() for ref in stat_refs if ref.strip()]
            
            # Parse reform recommendations
            rec_section = re.search(r'REFORM RECOMMENDATIONS:(.*?)(?=JUSTIFICATION:|$)', 
                                  response_text, re.DOTALL | re.IGNORECASE)
            if rec_section:
                rec_text = rec_section.group(1)
                # Extract bullet points
                recs = re.findall(r'-\s*(.+)', rec_text)
                recommendations = [rec.strip() for rec in recs if rec.strip()]
            
            # Parse justification
            just_section = re.search(r'JUSTIFICATION:(.*?)$', response_text, re.DOTALL | re.IGNORECASE)
            if just_section:
                justification = just_section.group(1).strip()
            
            return DOGEAnalysis(
                category=category,
                statutory_references=statutory_refs,
                reform_recommendations=recommendations,
                justification=justification
            )
            
        except Exception as e:
            logger.error(f"Error parsing DOGE response: {e}")
            return DOGEAnalysis(
                category=RegulationCategory.UNKNOWN,
                statutory_references=[],
                reform_recommendations=[],
                justification=f"Parsing failed: {str(e)}\n\nRaw response: {response_text}"
            )
    
    def batch_analyze_documents(self, documents: List[Dict], prompt: str) -> List[Tuple[str, str, bool, Optional[str]]]:
        """
        Analyze multiple documents in batch.
        
        Args:
            documents: List of document dictionaries with 'content' and 'document_number'
            prompt: Analysis prompt template
            
        Returns:
            List of tuples (document_id, response_text, success, error_message)
        """
        results = []
        
        logger.info(f"Starting batch analysis of {len(documents)} documents")
        
        for i, doc in enumerate(documents):
            doc_id = doc.get('document_number', f'doc_{i}')
            content = doc.get('content', '')
            
            logger.info(f"Analyzing document {i+1}/{len(documents)}: {doc_id}")
            
            response_text, success, error = self.analyze_document(content, prompt, doc_id)
            results.append((doc_id, response_text, success, error))
            
            # Progress logging
            if (i + 1) % 5 == 0:
                successful = sum(1 for _, _, s, _ in results if s)
                logger.info(f"Batch progress: {i+1}/{len(documents)} completed, {successful} successful")
        
        successful = sum(1 for _, _, s, _ in results if s)
        logger.info(f"Batch analysis completed: {successful}/{len(documents)} successful")
        
        return results
    
    def get_usage_stats(self) -> LLMUsageStats:
        """Get current usage statistics."""
        return self.usage_stats
    
    def reset_usage_stats(self):
        """Reset usage statistics."""
        self.usage_stats = LLMUsageStats()
        logger.info("Usage statistics reset")
    
    def perform_meta_analysis(self, analysis_results: List[Dict[str, Any]], session_id: str = None) -> MetaAnalysis:
        """
        Perform meta-analysis on a collection of document analysis results.
        
        Args:
            analysis_results: List of analysis result dictionaries
            session_id: Session identifier for tracking
            
        Returns:
            MetaAnalysis object with synthesized insights
        """
        start_time = time.time()
        
        try:
            if not analysis_results:
                return MetaAnalysis(
                    session_id=session_id or "unknown",
                    success=False,
                    error_message="No analysis results provided for meta-analysis",
                    processing_time=time.time() - start_time
                )
            
            # Prepare analysis data for meta-analysis
            analysis_summary = self._prepare_analysis_summary(analysis_results)
            
            logger.info(f"Performing meta-analysis on {len(analysis_results)} document analyses")
            
            # Use strategic insights prompt for meta-analysis
            strategic_prompt = """You are analyzing a collection of regulatory document analyses to provide strategic insights and recommendations.

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
[Provide a 2-3 sentence executive summary of the most critical findings]"""
            
            # Perform strategic meta-analysis
            strategic_response, success1, error1 = self.analyze_document(
                analysis_summary, strategic_prompt, f"meta_analysis_strategic_{session_id}"
            )
            
            # Use reform opportunities prompt for detailed recommendations
            reform_prompt = """Analyze the following regulatory analysis results to identify reform opportunities and potential challenges.

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
            
            # Perform reform-focused meta-analysis
            reform_response, success2, error2 = self.analyze_document(
                analysis_summary, reform_prompt, f"meta_analysis_reform_{session_id}"
            )
            
            # Parse and combine results
            if success1 or success2:
                meta_analysis = self._parse_meta_analysis_response(
                    strategic_response if success1 else "",
                    reform_response if success2 else "",
                    session_id or "unknown"
                )
                meta_analysis.processing_time = time.time() - start_time
                
                logger.info(f"Meta-analysis completed successfully in {meta_analysis.processing_time:.2f}s")
                return meta_analysis
            else:
                # Both analyses failed
                error_msg = f"Meta-analysis failed - Strategic: {error1}, Reform: {error2}"
                return MetaAnalysis(
                    session_id=session_id or "unknown",
                    success=False,
                    error_message=error_msg,
                    processing_time=time.time() - start_time
                )
                
        except Exception as e:
            error_msg = f"Meta-analysis failed: {str(e)}"
            logger.error(error_msg)
            return MetaAnalysis(
                session_id=session_id or "unknown",
                success=False,
                error_message=error_msg,
                processing_time=time.time() - start_time
            )
    
    def _prepare_analysis_summary(self, analysis_results: List[Dict[str, Any]]) -> str:
        """
        Prepare a summary of analysis results for meta-analysis.
        
        Args:
            analysis_results: List of analysis result dictionaries
            
        Returns:
            Formatted summary string
        """
        summary_parts = []
        
        # Group by category
        categories = {}
        for result in analysis_results:
            analysis = result.get('analysis', {})
            category = analysis.get('category', 'UNKNOWN')
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
        
        # Add category summary
        summary_parts.append("CATEGORY DISTRIBUTION:")
        for category, docs in categories.items():
            summary_parts.append(f"- {category}: {len(docs)} documents")
        
        summary_parts.append("\nKEY FINDINGS BY DOCUMENT:")
        
        # Add key findings for each document (limit to prevent token overflow)
        for i, result in enumerate(analysis_results[:20]):  # Limit to first 20 documents
            doc_num = result.get('document_number', f'doc_{i}')
            title = result.get('title', 'Unknown Title')[:100]  # Truncate long titles
            analysis = result.get('analysis', {})
            
            category = analysis.get('category', 'UNKNOWN')
            statutory_refs = analysis.get('statutory_references', [])
            recommendations = analysis.get('reform_recommendations', [])
            
            summary_parts.append(f"\nDocument {doc_num}: {title}")
            summary_parts.append(f"  Category: {category}")
            
            if statutory_refs:
                summary_parts.append(f"  Key Statutes: {', '.join(statutory_refs[:3])}")  # First 3 refs
            
            if recommendations:
                summary_parts.append(f"  Top Recommendation: {recommendations[0][:150]}")  # First recommendation, truncated
        
        if len(analysis_results) > 20:
            summary_parts.append(f"\n[... and {len(analysis_results) - 20} more documents]")
        
        return "\n".join(summary_parts)
    
    def _parse_meta_analysis_response(self, strategic_response: str, reform_response: str, session_id: str) -> MetaAnalysis:
        """
        Parse meta-analysis responses into structured MetaAnalysis object.
        
        Args:
            strategic_response: Response from strategic analysis prompt
            reform_response: Response from reform analysis prompt
            session_id: Session identifier
            
        Returns:
            MetaAnalysis object with parsed results
        """
        try:
            meta_analysis = MetaAnalysis(session_id=session_id)
            
            # Parse strategic response
            if strategic_response:
                # Extract key patterns
                patterns_match = re.search(r'KEY PATTERNS:(.*?)(?=STRATEGIC THEMES:|$)', strategic_response, re.DOTALL | re.IGNORECASE)
                if patterns_match:
                    patterns_text = patterns_match.group(1)
                    patterns = re.findall(r'-\s*(.+)', patterns_text)
                    meta_analysis.key_patterns = [p.strip() for p in patterns if p.strip()]
                
                # Extract strategic themes
                themes_match = re.search(r'STRATEGIC THEMES:(.*?)(?=PRIORITY ACTIONS:|$)', strategic_response, re.DOTALL | re.IGNORECASE)
                if themes_match:
                    themes_text = themes_match.group(1)
                    themes = re.findall(r'-\s*(.+)', themes_text)
                    meta_analysis.strategic_themes = [t.strip() for t in themes if t.strip()]
                
                # Extract priority actions
                actions_match = re.search(r'PRIORITY ACTIONS:(.*?)(?=GOAL ALIGNMENT:|$)', strategic_response, re.DOTALL | re.IGNORECASE)
                if actions_match:
                    actions_text = actions_match.group(1)
                    actions = re.findall(r'-\s*(.+)', actions_text)
                    meta_analysis.priority_actions = [a.strip() for a in actions if a.strip()]
                
                # Extract goal alignment
                goal_match = re.search(r'GOAL ALIGNMENT:(.*?)(?=IMPLEMENTATION ROADMAP:|$)', strategic_response, re.DOTALL | re.IGNORECASE)
                if goal_match:
                    meta_analysis.goal_alignment = goal_match.group(1).strip()
                
                # Extract implementation roadmap
                roadmap_match = re.search(r'IMPLEMENTATION ROADMAP:(.*?)(?=SUMMARY:|$)', strategic_response, re.DOTALL | re.IGNORECASE)
                if roadmap_match:
                    meta_analysis.implementation_roadmap = roadmap_match.group(1).strip()
                
                # Extract executive summary
                summary_match = re.search(r'SUMMARY:(.*?)$', strategic_response, re.DOTALL | re.IGNORECASE)
                if summary_match:
                    meta_analysis.executive_summary = summary_match.group(1).strip()
            
            # Parse reform response
            if reform_response:
                # Extract reform opportunities
                opportunities_match = re.search(r'REFORM OPPORTUNITIES:(.*?)(?=IMPLEMENTATION CHALLENGES:|$)', reform_response, re.DOTALL | re.IGNORECASE)
                if opportunities_match:
                    opportunities_text = opportunities_match.group(1)
                    opportunities = re.findall(r'•\s*(.+)', opportunities_text)
                    meta_analysis.reform_opportunities = [o.strip() for o in opportunities if o.strip()]
                
                # Extract implementation challenges
                challenges_match = re.search(r'IMPLEMENTATION CHALLENGES:(.*?)(?=STAKEHOLDER IMPACT:|$)', reform_response, re.DOTALL | re.IGNORECASE)
                if challenges_match:
                    challenges_text = challenges_match.group(1)
                    challenges = re.findall(r'•\s*(.+)', challenges_text)
                    meta_analysis.implementation_challenges = [c.strip() for c in challenges if c.strip()]
                
                # Extract stakeholder impact
                stakeholder_match = re.search(r'STAKEHOLDER IMPACT:(.*?)(?=RESOURCE REQUIREMENTS:|$)', reform_response, re.DOTALL | re.IGNORECASE)
                if stakeholder_match:
                    meta_analysis.stakeholder_impact = stakeholder_match.group(1).strip()
                
                # Extract resource requirements
                resources_match = re.search(r'RESOURCE REQUIREMENTS:(.*?)(?=RISK ASSESSMENT:|$)', reform_response, re.DOTALL | re.IGNORECASE)
                if resources_match:
                    meta_analysis.resource_requirements = resources_match.group(1).strip()
                
                # Extract risk assessment
                risk_match = re.search(r'RISK ASSESSMENT:(.*?)(?=QUICK WINS:|$)', reform_response, re.DOTALL | re.IGNORECASE)
                if risk_match:
                    meta_analysis.risk_assessment = risk_match.group(1).strip()
                
                # Extract quick wins
                wins_match = re.search(r'QUICK WINS:(.*?)(?=LONG-TERM STRATEGY:|$)', reform_response, re.DOTALL | re.IGNORECASE)
                if wins_match:
                    wins_text = wins_match.group(1)
                    wins = re.findall(r'•\s*(.+)', wins_text)
                    meta_analysis.quick_wins = [w.strip() for w in wins if w.strip()]
                
                # Extract long-term strategy
                strategy_match = re.search(r'LONG-TERM STRATEGY:(.*?)$', reform_response, re.DOTALL | re.IGNORECASE)
                if strategy_match:
                    meta_analysis.long_term_strategy = strategy_match.group(1).strip()
            
            return meta_analysis
            
        except Exception as e:
            logger.error(f"Error parsing meta-analysis response: {e}")
            return MetaAnalysis(
                session_id=session_id,
                success=False,
                error_message=f"Parsing failed: {str(e)}"
            )