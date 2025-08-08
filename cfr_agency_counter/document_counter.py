"""
Document Counter for processing agency document counts from the Federal Register API.

This module handles matching agencies with API results, processing zero-document
agencies, and identifying agencies missing from API responses. It supports both
API-based and direct fetching methods.
"""

import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple, Union

from .models import Agency, AgencyDocumentCount, CountingResults
from .api_client import FederalRegisterClient, FederalRegisterAPIError
from .direct_fetcher import DirectDocumentCounter


logger = logging.getLogger(__name__)


class DocumentCounter:
    """Processes API responses and matches agencies with document counts."""
    
    def __init__(self, api_client: Optional[FederalRegisterClient] = None, 
                 use_direct_fetch: bool = False, rate_limit: float = 2.0):
        """
        Initialize the document counter.
        
        Args:
            api_client: Federal Register API client instance (optional if using direct fetch)
            use_direct_fetch: Whether to use direct fetching instead of API
            rate_limit: Rate limit for direct fetching (requests per second)
        """
        self.api_client = api_client
        self.use_direct_fetch = use_direct_fetch
        self.rate_limit = rate_limit
        self.processing_start_time: Optional[datetime] = None
        
        if use_direct_fetch:
            logger.info("Document counter initialized with direct fetching enabled")
        else:
            logger.info("Document counter initialized with API client")
    
    def count_documents_by_agency(self, agencies: List[Agency]) -> CountingResults:
        """
        Count documents for all provided agencies.
        
        Args:
            agencies: List of agencies to process
            
        Returns:
            CountingResults with comprehensive processing results
        """
        logger.info(f"Starting document counting for {len(agencies)} agencies")
        self.processing_start_time = datetime.now()
        
        if self.use_direct_fetch:
            return self._count_documents_direct(agencies)
        else:
            return self._count_documents_api(agencies)
    
    def _count_documents_api(self, agencies: List[Agency]) -> CountingResults:
        """
        Count documents using the Federal Register API.
        
        Args:
            agencies: List of agencies to process
            
        Returns:
            CountingResults with comprehensive processing results
        """
        # Get bulk document counts from API
        try:
            api_counts = self.api_client.get_agency_document_counts()
            logger.info(f"Retrieved document counts for {len(api_counts)} agencies from API")
        except FederalRegisterAPIError as e:
            logger.error(f"Failed to retrieve document counts from API: {e}")
            # Return results with all failed queries
            return self._create_failed_results(agencies, str(e))
        
        # Process each agency
        results = []
        successful_queries = 0
        failed_queries = 0
        agencies_with_documents = 0
        agencies_without_documents = 0
        total_documents = 0
        
        for agency in agencies:
            try:
                doc_count_result = self._process_single_agency(agency, api_counts)
                results.append(doc_count_result)
                
                if doc_count_result.query_successful:
                    successful_queries += 1
                    if doc_count_result.document_count > 0:
                        agencies_with_documents += 1
                        total_documents += doc_count_result.document_count
                    else:
                        agencies_without_documents += 1
                else:
                    failed_queries += 1
                    
            except Exception as e:
                logger.error(f"Unexpected error processing agency {agency.slug}: {e}")
                failed_result = AgencyDocumentCount(
                    agency=agency,
                    document_count=0,
                    last_updated=datetime.now(),
                    query_successful=False,
                    error_message=f"Processing error: {str(e)}"
                )
                results.append(failed_result)
                failed_queries += 1
        
        # Calculate execution time
        execution_time = (datetime.now() - self.processing_start_time).total_seconds()
        
        # Create final results
        counting_results = CountingResults(
            total_agencies=len(agencies),
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            agencies_with_documents=agencies_with_documents,
            agencies_without_documents=agencies_without_documents,
            total_documents=total_documents,
            execution_time=execution_time,
            timestamp=datetime.now(),
            results=results
        )
        
        logger.info(f"API document counting completed: {counting_results.get_summary()}")
        return counting_results
    
    def _count_documents_direct(self, agencies: List[Agency]) -> CountingResults:
        """
        Count documents using direct fetching (web scraping).
        
        Args:
            agencies: List of agencies to process
            
        Returns:
            CountingResults with comprehensive processing results
        """
        logger.info(f"Starting direct document counting for {len(agencies)} agencies")
        
        try:
            with DirectDocumentCounter(rate_limit=self.rate_limit) as direct_counter:
                direct_results = direct_counter.count_documents(agencies)
                
                # Convert direct results to AgencyDocumentCount objects
                results = []
                successful_queries = 0
                failed_queries = 0
                agencies_with_documents = 0
                agencies_without_documents = 0
                total_documents = 0
                
                for agency in agencies:
                    if agency.slug in direct_results:
                        count, success, error = direct_results[agency.slug]
                        
                        doc_count_result = AgencyDocumentCount(
                            agency=agency,
                            document_count=count,
                            last_updated=datetime.now(),
                            query_successful=success,
                            error_message=error if not success else None
                        )
                        
                        results.append(doc_count_result)
                        
                        if success:
                            successful_queries += 1
                            if count > 0:
                                agencies_with_documents += 1
                                total_documents += count
                            else:
                                agencies_without_documents += 1
                        else:
                            failed_queries += 1
                    else:
                        # Agency not processed
                        failed_result = AgencyDocumentCount(
                            agency=agency,
                            document_count=0,
                            last_updated=datetime.now(),
                            query_successful=False,
                            error_message="Agency not processed by direct fetcher"
                        )
                        results.append(failed_result)
                        failed_queries += 1
                
                # Calculate execution time
                execution_time = (datetime.now() - self.processing_start_time).total_seconds()
                
                # Create final results
                counting_results = CountingResults(
                    total_agencies=len(agencies),
                    successful_queries=successful_queries,
                    failed_queries=failed_queries,
                    agencies_with_documents=agencies_with_documents,
                    agencies_without_documents=agencies_without_documents,
                    total_documents=total_documents,
                    execution_time=execution_time,
                    timestamp=datetime.now(),
                    results=results
                )
                
                logger.info(f"Direct document counting completed: {counting_results.get_summary()}")
                return counting_results
                
        except Exception as e:
            logger.error(f"Direct document counting failed: {e}")
            return self._create_failed_results(agencies, f"Direct fetching failed: {str(e)}")
    
    def _process_single_agency(self, agency: Agency, api_counts: Dict[str, int]) -> AgencyDocumentCount:
        """
        Process a single agency and create its document count result.
        
        Args:
            agency: Agency to process
            api_counts: Dictionary of agency slugs to document counts from API
            
        Returns:
            AgencyDocumentCount for the agency
        """
        logger.debug(f"Processing agency: {agency.slug}")
        
        # Check if agency exists in API results
        if agency.slug in api_counts:
            document_count = api_counts[agency.slug]
            logger.debug(f"Found {document_count} documents for {agency.slug}")
            
            return AgencyDocumentCount(
                agency=agency,
                document_count=document_count,
                last_updated=datetime.now(),
                query_successful=True
            )
        else:
            # Agency not found in API results - could be zero documents or missing
            logger.debug(f"Agency {agency.slug} not found in API results")
            
            # Try to get individual agency details to confirm existence
            try:
                agency_details = self.api_client.get_agency_details(agency.slug)
                if agency_details is not None:
                    # Agency exists but has zero documents
                    logger.debug(f"Agency {agency.slug} exists but has zero documents")
                    return AgencyDocumentCount(
                        agency=agency,
                        document_count=0,
                        last_updated=datetime.now(),
                        query_successful=True
                    )
                else:
                    # Agency doesn't exist in API
                    logger.warning(f"Agency {agency.slug} not found in Federal Register API")
                    return AgencyDocumentCount(
                        agency=agency,
                        document_count=0,
                        last_updated=datetime.now(),
                        query_successful=False,
                        error_message="Agency not found in Federal Register API"
                    )
            except FederalRegisterAPIError as e:
                logger.warning(f"Error checking agency details for {agency.slug}: {e}")
                return AgencyDocumentCount(
                    agency=agency,
                    document_count=0,
                    last_updated=datetime.now(),
                    query_successful=False,
                    error_message=f"API error: {str(e)}"
                )
    
    def handle_missing_agencies(self, agencies: List[Agency], api_results: Dict[str, int]) -> List[str]:
        """
        Identify agencies that are missing from API results.
        
        Args:
            agencies: List of agencies to check
            api_results: Dictionary of agency slugs to document counts from API
            
        Returns:
            List of agency slugs that are missing from API results
        """
        agency_slugs = {agency.slug for agency in agencies}
        api_slugs = set(api_results.keys())
        
        missing_from_api = agency_slugs - api_slugs
        
        if missing_from_api:
            logger.info(f"Found {len(missing_from_api)} agencies missing from API results")
            for slug in sorted(missing_from_api):
                logger.debug(f"Missing from API: {slug}")
        
        return list(missing_from_api)
    
    def get_extra_agencies_in_api(self, agencies: List[Agency], api_results: Dict[str, int]) -> List[str]:
        """
        Identify agencies that are in API results but not in our agency list.
        
        Args:
            agencies: List of agencies we're processing
            api_results: Dictionary of agency slugs to document counts from API
            
        Returns:
            List of agency slugs that are in API but not in our list
        """
        agency_slugs = {agency.slug for agency in agencies}
        api_slugs = set(api_results.keys())
        
        extra_in_api = api_slugs - agency_slugs
        
        if extra_in_api:
            logger.info(f"Found {len(extra_in_api)} agencies in API that are not in our list")
            for slug in sorted(extra_in_api):
                logger.debug(f"Extra in API: {slug}")
        
        return list(extra_in_api)
    
    def create_comprehensive_mapping(self, agencies: List[Agency], api_results: Dict[str, int]) -> Dict[str, Dict]:
        """
        Create a comprehensive mapping between agency slugs and document counts.
        
        Args:
            agencies: List of agencies to process
            api_results: Dictionary of agency slugs to document counts from API
            
        Returns:
            Dictionary with comprehensive mapping information
        """
        logger.info("Creating comprehensive agency-to-document mapping")
        
        mapping = {
            'agencies_with_counts': {},
            'agencies_without_counts': [],
            'agencies_missing_from_api': [],
            'extra_agencies_in_api': [],
            'total_agencies_processed': len(agencies),
            'total_agencies_in_api': len(api_results),
            'total_documents': sum(api_results.values())
        }
        
        # Process agencies with counts
        for agency in agencies:
            if agency.slug in api_results:
                mapping['agencies_with_counts'][agency.slug] = {
                    'agency_name': agency.name,
                    'document_count': api_results[agency.slug],
                    'cfr_citation': agency.cfr_citation,
                    'parent_agency': agency.parent_agency,
                    'active': agency.active
                }
            else:
                mapping['agencies_without_counts'].append({
                    'slug': agency.slug,
                    'agency_name': agency.name,
                    'cfr_citation': agency.cfr_citation,
                    'parent_agency': agency.parent_agency,
                    'active': agency.active
                })
        
        # Identify missing and extra agencies
        mapping['agencies_missing_from_api'] = self.handle_missing_agencies(agencies, api_results)
        mapping['extra_agencies_in_api'] = self.get_extra_agencies_in_api(agencies, api_results)
        
        logger.info(f"Mapping created: {len(mapping['agencies_with_counts'])} with counts, "
                   f"{len(mapping['agencies_without_counts'])} without counts")
        
        return mapping
    
    def validate_agency_matching(self, agencies: List[Agency], api_results: Dict[str, int]) -> Tuple[bool, List[str]]:
        """
        Validate the matching between agencies and API results.
        
        Args:
            agencies: List of agencies to validate
            api_results: Dictionary of agency slugs to document counts from API
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check for duplicate agency slugs
        agency_slugs = [agency.slug for agency in agencies]
        if len(agency_slugs) != len(set(agency_slugs)):
            duplicates = [slug for slug in set(agency_slugs) if agency_slugs.count(slug) > 1]
            issues.append(f"Duplicate agency slugs found: {duplicates}")
        
        # Check for invalid document counts in API results
        for slug, count in api_results.items():
            if not isinstance(count, int) or count < 0:
                issues.append(f"Invalid document count for {slug}: {count}")
        
        # Check for agencies with empty slugs
        empty_slug_agencies = [agency.name for agency in agencies if not agency.slug]
        if empty_slug_agencies:
            issues.append(f"Agencies with empty slugs: {empty_slug_agencies}")
        
        # Log validation results
        if issues:
            logger.warning(f"Agency matching validation failed with {len(issues)} issues")
            for issue in issues:
                logger.warning(f"Validation issue: {issue}")
        else:
            logger.info("Agency matching validation passed")
        
        return len(issues) == 0, issues
    
    def _create_failed_results(self, agencies: List[Agency], error_message: str) -> CountingResults:
        """
        Create CountingResults for when the entire process fails.
        
        Args:
            agencies: List of agencies that were being processed
            error_message: Error message describing the failure
            
        Returns:
            CountingResults with all failed queries
        """
        results = []
        for agency in agencies:
            failed_result = AgencyDocumentCount(
                agency=agency,
                document_count=0,
                last_updated=datetime.now(),
                query_successful=False,
                error_message=error_message
            )
            results.append(failed_result)
        
        execution_time = 0.0
        if self.processing_start_time:
            execution_time = (datetime.now() - self.processing_start_time).total_seconds()
        
        return CountingResults(
            total_agencies=len(agencies),
            successful_queries=0,
            failed_queries=len(agencies),
            agencies_with_documents=0,
            agencies_without_documents=0,
            total_documents=0,
            execution_time=execution_time,
            timestamp=datetime.now(),
            results=results
        )