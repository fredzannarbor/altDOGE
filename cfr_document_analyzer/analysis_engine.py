"""
Analysis engine for CFR Document Analyzer.

Coordinates document analysis using LLM client and prompt manager.
"""

import logging
import time
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

from .config import Config
from .database import Database
from .document_retriever import DocumentRetriever
from .llm_client import LLMClient
from .prompt_manager import PromptManager
from .models import Document, AnalysisResult, AnalysisSession, SessionStatus, RegulationCategory, MetaAnalysis
from .utils import safe_json_dumps, format_timestamp


logger = logging.getLogger(__name__)


class AnalysisEngine:
    """Main analysis engine that coordinates document analysis."""
    
    def __init__(self, database: Database):
        """
        Initialize the analysis engine.
        
        Args:
            database: Database instance
        """
        self.database = database
        self.document_retriever = DocumentRetriever(database, use_cache=False)
        self.llm_client = LLMClient()
        self.prompt_manager = PromptManager()
        
        logger.info("Analysis engine initialized")
    
    def \
            analyze_agency_documents(self, agency_slug: str, prompt_strategy: str = "DOGE Criteria",
                               document_limit: Optional[int] = None) -> AnalysisSession:
        """
        Analyze documents for a specific agency.
        
        Args:
            agency_slug: Agency identifier
            prompt_strategy: Name of prompt strategy to use
            document_limit: Maximum number of documents to analyze
            
        Returns:
            AnalysisSession with results
        """
        logger.info(f"Starting analysis for agency: {agency_slug}")
        
        # Create analysis session
        session_data = {
            'agency_slugs': safe_json_dumps([agency_slug]),
            'prompt_strategy': prompt_strategy,
            'document_limit': document_limit
        }
        session_id = self.database.create_session(session_data)
        
        session = AnalysisSession(
            session_id=session_id,
            agency_slugs=[agency_slug],
            prompt_strategy=prompt_strategy,
            document_limit=document_limit,
            status=SessionStatus.RUNNING
        )
        
        try:
            # Update session status
            self.database.update_session_status(session_id, SessionStatus.RUNNING.value)
            
            # Retrieve documents
            logger.info(f"Retrieving documents for {agency_slug} (limit: {document_limit})")
            documents = self.document_retriever.get_agency_documents(agency_slug, document_limit)
            
            if not documents:
                logger.warning(f"No documents found for agency: {agency_slug}")
                session.status = SessionStatus.COMPLETED
                self.database.update_session_status(session_id, SessionStatus.COMPLETED.value, 0)
                return session
            
            session.total_documents = len(documents)
            logger.info(f"Found {len(documents)} documents to analyze")
            
            # Analyze each document
            results = []
            for i, document in enumerate(documents):
                logger.info(f"Analyzing document {i+1}/{len(documents)}: {document.document_number}")
                
                try:
                    analysis_result = self._analyze_single_document(document, prompt_strategy)
                    if analysis_result:
                        results.append(analysis_result)
                    
                    session.documents_processed = i + 1
                    self.database.update_session_status(session_id, SessionStatus.RUNNING.value, session.documents_processed)
                    
                except Exception as e:
                    logger.error(f"Error analyzing document {document.document_number}: {e}")
                    # Continue with next document
                    continue
            
            # Complete session
            session.status = SessionStatus.COMPLETED
            session.completed_at = datetime.now()
            self.database.update_session_status(session_id, SessionStatus.COMPLETED.value, session.documents_processed)
            
            logger.info(f"Analysis completed: {len(results)} documents analyzed successfully")
            return session
            
        except Exception as e:
            logger.error(f"Analysis failed for agency {agency_slug}: {e}")
            session.status = SessionStatus.FAILED
            self.database.update_session_status(session_id, SessionStatus.FAILED.value)
            raise
    
    def _analyze_single_document(self, document: Document, prompt_strategy: str) -> Optional[AnalysisResult]:
        """
        Analyze a single document using the specified prompt strategy.
        
        Args:
            document: Document to analyze
            prompt_strategy: Name of prompt strategy
            
        Returns:
            AnalysisResult or None if analysis failed
        """
        start_time = time.time()
        
        try:
            if not document.content:
                logger.warning(f"Document {document.document_number} has no content")
                return None
            
            # Get prompt package
            prompt_package = self.prompt_manager.get_prompt_package(prompt_strategy)
            if not prompt_package:
                logger.error(f"Prompt strategy not found: {prompt_strategy}")
                return None
            
            # For DOGE analysis, use the specialized method
            if prompt_strategy == "DOGE Criteria":
                doge_analysis = self.llm_client.analyze_document_with_doge_prompts(
                    document.content, 
                    document.document_number
                )
                
                # Convert DOGE analysis to AnalysisResult
                analysis_result = AnalysisResult(
                    document_id=document.id,
                    prompt_strategy=prompt_strategy,
                    category=doge_analysis.category,
                    statutory_references=doge_analysis.statutory_references,
                    reform_recommendations=doge_analysis.reform_recommendations,
                    justification=doge_analysis.justification,
                    processing_time=time.time() - start_time,
                    success=True
                )
            else:
                # Use first prompt from package for other strategies
                prompt = prompt_package.prompts[0]
                response_text, success, error = self.llm_client.analyze_document(
                    document.content, 
                    prompt, 
                    document.document_number
                )
                
                analysis_result = AnalysisResult(
                    document_id=document.id,
                    prompt_strategy=prompt_strategy,
                    raw_response=response_text,
                    processing_time=time.time() - start_time,
                    success=success,
                    error_message=error
                )
            
            # Store analysis in database
            analysis_data = {
                'document_id': document.id,
                'prompt_strategy': prompt_strategy,
                'category': analysis_result.category.value if analysis_result.category else None,
                'statutory_references': safe_json_dumps(analysis_result.statutory_references),
                'reform_recommendations': safe_json_dumps(analysis_result.reform_recommendations),
                'justification': analysis_result.justification,
                'raw_response': analysis_result.raw_response,
                'token_usage': analysis_result.token_usage,
                'processing_time': analysis_result.processing_time,
                'success': analysis_result.success,
                'error_message': analysis_result.error_message
            }
            print(analysis_result)
            print('---')
            print(analysis_data)
            analysis_id = self.database.store_analysis(analysis_data)
            analysis_result.id = analysis_id
            
            logger.debug(f"Analysis completed for document {document.document_number} in {analysis_result.processing_time:.2f}s")
            return analysis_result
            
        except Exception as e:

            
            # Store failed analysis
            if document and document.id is not None:
                document_id_to_store = document.id
                logger.info(f"Storing failed analysis for document {document_id_to_store}")
            else:
                document_id_to_store = None
                logger.info("Storing failed analysis for unknown document id with id = 0")

            analysis_data = {
                'document_id': document_id_to_store,
                'prompt_strategy': prompt_strategy,
                'processing_time': time.time() - start_time,
                'success': False,
                'error_message': str(e)
            }

            try:
                self.database.store_analysis(analysis_data)
            except Exception as db_error:
                logger.error(f"Failed to store error analysis: {db_error}")
            
            return None
    
    def get_analysis_results(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get analysis results for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of analysis result dictionaries
        """
        try:
            # Get session info
            query = "SELECT * FROM sessions WHERE session_id = ?"
            session_results = self.database.execute_query(query, (session_id,))
            
            if not session_results:
                logger.error(f"Session not found: {session_id}")
                return []
            
            session_data = dict(session_results[0])
            
            # Get documents and analyses for this session
            agency_slugs = json.loads(session_data.get('agency_slugs', '[]'))
            
            results = []
            for agency_slug in agency_slugs:
                # Get documents for this agency
                documents = self.database.get_documents_by_agency(agency_slug)
                
                for doc in documents:
                    # Get analyses for this document
                    analyses = self.database.get_analyses_by_document(doc['id'])
                    
                    # Filter analyses by session's prompt strategy
                    session_analyses = [
                        a for a in analyses 
                        if a['prompt_strategy'] == session_data['prompt_strategy']
                    ]
                    
                    if session_analyses:
                        # Use the most recent analysis
                        analysis = session_analyses[0]
                        
                        result = {
                            'document_number': doc['document_number'],
                            'title': doc['title'],
                            'agency_slug': doc['agency_slug'],
                            'publication_date': doc['publication_date'],
                            'content_length': doc['content_length'],
                            'analysis': {
                                'prompt_strategy': analysis['prompt_strategy'],
                                'category': analysis['category'],
                                'statutory_references': json.loads(analysis['statutory_references'] or '[]'),
                                'reform_recommendations': json.loads(analysis['reform_recommendations'] or '[]'),
                                'justification': analysis['justification'],
                                'success': bool(analysis['success']),
                                'error_message': analysis['error_message'],
                                'processing_time': analysis['processing_time'],
                                'created_at': analysis['created_at']
                            }
                        }
                        results.append(result)
            
            logger.info(f"Retrieved {len(results)} analysis results for session {session_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving analysis results for session {session_id}: {e}")
            return []
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """
        Get usage statistics from LLM client.
        
        Returns:
            Dictionary with usage statistics
        """
        stats = self.llm_client.get_usage_stats()
        return {
            'total_calls': stats.total_calls,
            'successful_calls': stats.successful_calls,
            'failed_calls': stats.failed_calls,
            'success_rate': (stats.successful_calls / stats.total_calls * 100) if stats.total_calls > 0 else 0,
            'total_tokens': stats.total_tokens,
            'total_cost': stats.total_cost,
            'total_time': stats.total_time,
            'average_time_per_call': (stats.total_time / stats.total_calls) if stats.total_calls > 0 else 0
        }
    
    def perform_meta_analysis(self, session_id: str) -> Optional[MetaAnalysis]:
        """
        Perform meta-analysis on the results of an analysis session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            MetaAnalysis object or None if failed
        """
        try:
            logger.info(f"Starting meta-analysis for session: {session_id}")
            
            # Get analysis results for the session
            analysis_results = self.get_analysis_results(session_id)
            
            if not analysis_results:
                logger.warning(f"No analysis results found for session: {session_id}")
                return None
            
            # Perform meta-analysis using LLM client
            meta_analysis = self.llm_client.perform_meta_analysis(analysis_results, session_id)
            
            if meta_analysis.success:
                # Store meta-analysis in database
                meta_data = {
                    'session_id': session_id,
                    'key_patterns': safe_json_dumps(meta_analysis.key_patterns),
                    'strategic_themes': safe_json_dumps(meta_analysis.strategic_themes),
                    'priority_actions': safe_json_dumps(meta_analysis.priority_actions),
                    'goal_alignment': meta_analysis.goal_alignment,
                    'implementation_roadmap': meta_analysis.implementation_roadmap,
                    'executive_summary': meta_analysis.executive_summary,
                    'reform_opportunities': safe_json_dumps(meta_analysis.reform_opportunities),
                    'implementation_challenges': safe_json_dumps(meta_analysis.implementation_challenges),
                    'stakeholder_impact': meta_analysis.stakeholder_impact,
                    'resource_requirements': meta_analysis.resource_requirements,
                    'risk_assessment': meta_analysis.risk_assessment,
                    'quick_wins': safe_json_dumps(meta_analysis.quick_wins),
                    'long_term_strategy': meta_analysis.long_term_strategy,
                    'processing_time': meta_analysis.processing_time,
                    'success': meta_analysis.success,
                    'error_message': meta_analysis.error_message
                }
                
                meta_id = self.database.store_meta_analysis(meta_data)
                logger.info(f"Meta-analysis completed and stored with ID: {meta_id}")
                
                return meta_analysis
            else:
                logger.error(f"Meta-analysis failed: {meta_analysis.error_message}")
                return meta_analysis
                
        except Exception as e:
            logger.error(f"Error performing meta-analysis for session {session_id}: {e}")
            return MetaAnalysis(
                session_id=session_id,
                success=False,
                error_message=str(e)
            )
    
    def get_meta_analysis(self, session_id: str) -> Optional[MetaAnalysis]:
        """
        Get meta-analysis results for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            MetaAnalysis object or None if not found
        """
        try:
            meta_data = self.database.get_meta_analysis_by_session(session_id)
            
            if not meta_data:
                return None
            
            # Convert database record to MetaAnalysis object
            meta_analysis = MetaAnalysis(
                session_id=meta_data['session_id'],
                key_patterns=safe_json_loads(meta_data.get('key_patterns', '[]')),
                strategic_themes=safe_json_loads(meta_data.get('strategic_themes', '[]')),
                priority_actions=safe_json_loads(meta_data.get('priority_actions', '[]')),
                goal_alignment=meta_data.get('goal_alignment'),
                implementation_roadmap=meta_data.get('implementation_roadmap'),
                executive_summary=meta_data.get('executive_summary'),
                reform_opportunities=safe_json_loads(meta_data.get('reform_opportunities', '[]')),
                implementation_challenges=safe_json_loads(meta_data.get('implementation_challenges', '[]')),
                stakeholder_impact=meta_data.get('stakeholder_impact'),
                resource_requirements=meta_data.get('resource_requirements'),
                risk_assessment=meta_data.get('risk_assessment'),
                quick_wins=safe_json_loads(meta_data.get('quick_wins', '[]')),
                long_term_strategy=meta_data.get('long_term_strategy'),
                processing_time=meta_data.get('processing_time', 0.0),
                success=bool(meta_data.get('success', True)),
                error_message=meta_data.get('error_message'),
                created_at=meta_data.get('created_at')
            )
            
            return meta_analysis
            
        except Exception as e:
            logger.error(f"Error retrieving meta-analysis for session {session_id}: {e}")
            return None
    
    def get_session_results(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get complete session results including analysis and meta-analysis.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of analysis result dictionaries
        """
        return self.get_analysis_results(session_id)
    
    def close(self):
        """Clean up resources."""
        if self.document_retriever:
            self.document_retriever.close()
        logger.info("Analysis engine closed")