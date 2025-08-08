"""
Federal Register API Client for retrieving document counts and agency information.

This module handles communication with the Federal Register API, including
rate limiting, retry logic, and error handling.
"""

import time
import logging
import requests
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

from .config import Config


logger = logging.getLogger(__name__)


class FederalRegisterAPIError(Exception):
    """Custom exception for Federal Register API errors."""
    pass


class FederalRegisterClient:
    """Client for interacting with the Federal Register API."""
    
    def __init__(self, base_url: str = None, rate_limit: float = None):
        """
        Initialize the Federal Register API client.
        
        Args:
            base_url: Base URL for the Federal Register API
            rate_limit: Maximum requests per second (default from config)
        """
        self.base_url = base_url or Config.FR_API_BASE_URL
        self.rate_limit = rate_limit or Config.FR_API_RATE_LIMIT
        self.session = requests.Session()
        self.last_request_time = 0.0
        
        # Set up session headers
        self.session.headers.update({
            'User-Agent': 'CFR-Agency-Document-Counter/1.0.0 (Educational/Research Tool)',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate'
        })
        
        logger.info(f"Initialized API client with base URL: {self.base_url}")
        logger.info(f"Rate limit: {self.rate_limit} requests/second")
    
    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between API requests."""
        if self.rate_limit <= 0:
            return
        
        min_interval = 1.0 / self.rate_limit
        elapsed = time.time() - self.last_request_time
        
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make a request to the Federal Register API with retry logic.
        
        Args:
            endpoint: API endpoint (relative to base URL)
            params: Query parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            FederalRegisterAPIError: If the request fails after all retries
        """
        url = urljoin(self.base_url, endpoint)
        params = params or {}
        
        for attempt in range(Config.MAX_RETRIES + 1):
            try:
                self._enforce_rate_limit()
                
                logger.debug(f"Making request to {url} (attempt {attempt + 1})")
                
                response = self.session.get(
                    url,
                    params=params,
                    timeout=Config.REQUEST_TIMEOUT
                )
                
                # Handle rate limiting from server
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited by server, waiting {retry_after}s")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                
                try:
                    json_data = response.json()
                    return json_data
                except ValueError as e:
                    # Check if we got HTML (rate limiting page)
                    if response.text.strip().startswith('<!DOCTYPE html>'):
                        logger.error(f"Received HTML response from {url} - likely rate limited or blocked")
                        raise FederalRegisterAPIError("Received HTML response - API may be rate limiting or blocking requests")
                    else:
                        # Log the response content for debugging
                        logger.error(f"Invalid JSON response from {url}. Status: {response.status_code}, Content: {response.text[:200]}")
                        raise FederalRegisterAPIError(f"Invalid JSON response: {e}")
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1})")
                if attempt == Config.MAX_RETRIES:
                    raise FederalRegisterAPIError("Request timed out after all retries")
                
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error (attempt {attempt + 1})")
                if attempt == Config.MAX_RETRIES:
                    raise FederalRegisterAPIError("Connection failed after all retries")
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    continue  # Handle rate limiting above
                elif e.response.status_code >= 500:
                    logger.warning(f"Server error {e.response.status_code} (attempt {attempt + 1})")
                    if attempt == Config.MAX_RETRIES:
                        raise FederalRegisterAPIError(f"Server error: {e.response.status_code}")
                else:
                    # Client errors (4xx) shouldn't be retried
                    raise FederalRegisterAPIError(f"HTTP error: {e.response.status_code}")
            
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise FederalRegisterAPIError(f"Unexpected error: {e}")
            
            # Exponential backoff for retries
            if attempt < Config.MAX_RETRIES:
                sleep_time = Config.RETRY_BACKOFF_FACTOR ** attempt
                logger.debug(f"Retrying in {sleep_time}s")
                time.sleep(sleep_time)
        
        raise FederalRegisterAPIError("Request failed after all retries")
    
    def get_agency_document_counts(self) -> Dict[str, int]:
        """
        Get document counts for all agencies using the facets endpoint.
        
        Returns:
            Dictionary mapping agency slugs to document counts
            
        Raises:
            FederalRegisterAPIError: If the API request fails
        """
        logger.info("Fetching agency document counts from API")
        
        try:
            response = self._make_request('/documents/facets/agency')
            
            # Check if response is valid
            if not isinstance(response, dict):
                logger.error(f"Expected dict response, got {type(response)}: {response}")
                return {}
            
            # The API returns agency data directly, not wrapped in facets
            agency_facets = response
            
            if not agency_facets:
                logger.warning("No agency data found in API response")
                logger.debug(f"Full response: {response}")
                return {}
            
            # Extract counts from facets
            counts = {}
            for agency_slug, data in agency_facets.items():
                # Handle both old format (direct count) and new format (dict with count and name)
                if isinstance(data, dict) and 'count' in data:
                    count = data['count']
                elif isinstance(data, int):
                    count = data
                else:
                    logger.warning(f"Invalid data format for agency {agency_slug}: {data}")
                    continue
                
                if isinstance(count, int) and count >= 0:
                    counts[agency_slug] = count
                else:
                    logger.warning(f"Invalid count for agency {agency_slug}: {count}")
            
            logger.info(f"Retrieved document counts for {len(counts)} agencies")
            return counts
            
        except FederalRegisterAPIError:
            # Re-raise API errors as-is
            raise
        except Exception as e:
            logger.error(f"Failed to get agency document counts: {e}")
            raise FederalRegisterAPIError(f"Failed to get agency document counts: {e}")
    
    def get_agency_details(self, agency_slug: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific agency.
        
        Args:
            agency_slug: The agency slug identifier
            
        Returns:
            Dictionary with agency details or None if not found
            
        Raises:
            FederalRegisterAPIError: If the API request fails
        """
        logger.debug(f"Fetching details for agency: {agency_slug}")
        
        try:
            response = self._make_request(f'/agencies/{agency_slug}')
            return response
            
        except FederalRegisterAPIError as e:
            if "404" in str(e):
                logger.debug(f"Agency not found: {agency_slug}")
                return None
            raise
    
    def get_all_agencies(self) -> List[Dict[str, Any]]:
        """
        Get a list of all agencies from the API.
        
        Returns:
            List of agency dictionaries
            
        Raises:
            FederalRegisterAPIError: If the API request fails
        """
        logger.info("Fetching all agencies from API")
        
        try:
            response = self._make_request('/agencies')
            agencies = response.get('agencies', [])
            
            logger.info(f"Retrieved {len(agencies)} agencies from API")
            return agencies
            
        except Exception as e:
            logger.error(f"Failed to get agencies list: {e}")
            raise FederalRegisterAPIError(f"Failed to get agencies list: {e}")
    
    def search_documents(self, agency_slug: str, **kwargs) -> Dict[str, Any]:
        """
        Search for documents from a specific agency.
        
        Args:
            agency_slug: The agency slug to search for
            **kwargs: Additional search parameters
            
        Returns:
            Search results dictionary
            
        Raises:
            FederalRegisterAPIError: If the API request fails
        """
        logger.debug(f"Searching documents for agency: {agency_slug}")
        
        params = {
            'conditions[agencies][]': agency_slug,
            'per_page': kwargs.get('per_page', 20),
            'page': kwargs.get('page', 1),
            'fields[]': kwargs.get('fields', ['title', 'publication_date', 'document_number'])
        }
        
        # Add any additional search conditions
        for key, value in kwargs.items():
            if key.startswith('conditions[') and key not in params:
                params[key] = value
        
        try:
            response = self._make_request('/documents.json', params)
            return response
            
        except Exception as e:
            logger.error(f"Failed to search documents for {agency_slug}: {e}")
            raise FederalRegisterAPIError(f"Failed to search documents: {e}")
    
    def get_document_count_for_agency(self, agency_slug: str) -> int:
        """
        Get the total document count for a specific agency.
        
        Args:
            agency_slug: The agency slug identifier
            
        Returns:
            Total number of documents for the agency
            
        Raises:
            FederalRegisterAPIError: If the API request fails
        """
        logger.debug(f"Getting document count for agency: {agency_slug}")
        
        try:
            # Search with minimal results to get total count
            response = self.search_documents(
                agency_slug,
                per_page=1,
                fields=['document_number']
            )
            
            total_count = response.get('count', 0)
            logger.debug(f"Agency {agency_slug} has {total_count} documents")
            
            return total_count
            
        except Exception as e:
            logger.error(f"Failed to get document count for {agency_slug}: {e}")
            raise FederalRegisterAPIError(f"Failed to get document count: {e}")
    
    def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            self.session.close()
            logger.debug("API client session closed")