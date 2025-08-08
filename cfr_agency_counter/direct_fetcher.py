"""
Direct data fetcher for Federal Register documents.

This module provides an alternative to the API by directly scraping
the Federal Register website to get document counts.
"""

import logging
import re
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, quote
import requests
from bs4 import BeautifulSoup

from .models import Agency
from .error_handler import APIError

logger = logging.getLogger(__name__)


class DirectFetcher:
    """Direct fetcher for Federal Register document data."""
    
    def __init__(self, rate_limit: float = 2.0, timeout: int = 30):
        """
        Initialize the direct fetcher.
        
        Args:
            rate_limit: Delay between requests in seconds
            timeout: Request timeout in seconds
        """
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.session = requests.Session()
        
        # Set a realistic user agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        logger.info(f"Direct fetcher initialized with rate limit: {rate_limit}s")
    
    def get_agency_document_count(self, agency: Agency) -> Tuple[int, bool, Optional[str]]:
        """
        Get document count for an agency by scraping the Federal Register website.
        
        Args:
            agency: Agency object
            
        Returns:
            Tuple of (document_count, success, error_message)
        """
        try:
            # Try multiple approaches to get document count
            count, success, error = self._try_search_page_method(agency)
            
            if not success:
                # Fallback to agency page method
                count, success, error = self._try_agency_page_method(agency)
            
            if success:
                logger.debug(f"Found {count} documents for {agency.name}")
            else:
                logger.warning(f"Failed to get document count for {agency.name}: {error}")
            
            # Rate limiting
            time.sleep(self.rate_limit)
            
            return count, success, error
            
        except Exception as e:
            error_msg = f"Unexpected error fetching documents for {agency.name}: {str(e)}"
            logger.error(error_msg)
            return 0, False, error_msg
    
    def _try_search_page_method(self, agency: Agency) -> Tuple[int, bool, Optional[str]]:
        """
        Try to get document count from the search results page using JSON API.
        
        Args:
            agency: Agency object
            
        Returns:
            Tuple of (document_count, success, error_message)
        """
        try:
            # Try JSON API first (most reliable)
            json_attempts = [
                # Method 1: JSON API with agency slug
                {
                    'url': 'https://www.federalregister.gov/api/v1/documents.json',
                    'params': {
                        'conditions[agencies][]': agency.slug,
                        'per_page': 1  # We only need the count, not the documents
                    }
                },
                # Method 2: JSON API with agency name as fallback
                {
                    'url': 'https://www.federalregister.gov/api/v1/documents.json',
                    'params': {
                        'conditions[agencies][]': agency.name,
                        'per_page': 1
                    }
                }
            ]
            
            for i, attempt in enumerate(json_attempts, 1):
                logger.debug(f"Fetching JSON API for {agency.name} (attempt {i}): {attempt['url']}")
                
                try:
                    # Set JSON accept header
                    headers = self.session.headers.copy()
                    headers['Accept'] = 'application/json'
                    
                    response = self.session.get(
                        attempt['url'], 
                        params=attempt['params'], 
                        headers=headers,
                        timeout=self.timeout
                    )
                    response.raise_for_status()
                    
                    # Parse JSON response
                    try:
                        data = response.json()
                        count = data.get('count', 0)
                        
                        if isinstance(count, int) and count >= 0:
                            logger.debug(f"Successfully found {count} documents for {agency.name} using JSON API method {i}")
                            return count, True, None
                            
                    except ValueError as e:
                        logger.debug(f"JSON parsing failed for {agency.name} method {i}: {e}")
                        continue
                        
                except requests.RequestException as e:
                    logger.debug(f"JSON API method {i} failed for {agency.name}: {e}")
                    continue
            
            # Fallback to HTML scraping if JSON API fails
            logger.debug(f"JSON API failed for {agency.name}, falling back to HTML scraping")
            return self._try_html_scraping_method(agency)
                
        except Exception as e:
            return 0, False, f"All search methods failed: {str(e)}"
    
    def _try_html_scraping_method(self, agency: Agency) -> Tuple[int, bool, Optional[str]]:
        """
        Fallback method using HTML scraping when JSON API fails.
        
        Args:
            agency: Agency object
            
        Returns:
            Tuple of (document_count, success, error_message)
        """
        try:
            # HTML scraping attempts
            html_attempts = [
                # Method 1: Standard search with agency slug
                {
                    'url': 'https://www.federalregister.gov/documents/search',
                    'params': {
                        'conditions[agencies][]': agency.slug,
                        'order': 'newest'
                    }
                },
                # Method 2: Search with agency name
                {
                    'url': 'https://www.federalregister.gov/documents/search',
                    'params': {
                        'conditions[agencies][]': agency.name,
                        'order': 'newest'
                    }
                }
            ]
            
            for i, attempt in enumerate(html_attempts, 1):
                logger.debug(f"Fetching HTML page for {agency.name} (fallback attempt {i}): {attempt['url']}")
                
                try:
                    response = self.session.get(attempt['url'], params=attempt['params'], timeout=self.timeout)
                    response.raise_for_status()
                    
                    # Parse the HTML
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for result count indicators
                    count = self._extract_count_from_search_page(soup, agency.name)
                    
                    if count is not None and count > 0:
                        logger.debug(f"Successfully found {count} documents for {agency.name} using HTML method {i}")
                        return count, True, None
                    elif count == 0:
                        # Zero is a valid result, return it
                        return 0, True, None
                        
                except requests.RequestException as e:
                    logger.debug(f"HTML method {i} failed for {agency.name}: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"HTML method {i} parsing failed for {agency.name}: {e}")
                    continue
            
            return 0, False, "Could not find document count using HTML scraping methods"
                
        except Exception as e:
            return 0, False, f"HTML scraping methods failed: {str(e)}"
    
    def _try_agency_page_method(self, agency: Agency) -> Tuple[int, bool, Optional[str]]:
        """
        Try to get document count from the agency's dedicated page.
        
        Args:
            agency: Agency object
            
        Returns:
            Tuple of (document_count, success, error_message)
        """
        try:
            # Build agency page URL
            agency_url = f"https://www.federalregister.gov/agencies/{agency.slug}"
            
            logger.debug(f"Fetching agency page for {agency.name}: {agency_url}")
            
            response = self.session.get(agency_url, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for document count on agency page
            count = self._extract_count_from_agency_page(soup, agency.name)
            
            if count is not None:
                return count, True, None
            else:
                return 0, False, "Could not find document count on agency page"
                
        except requests.RequestException as e:
            return 0, False, f"Request failed: {str(e)}"
        except Exception as e:
            return 0, False, f"Parsing failed: {str(e)}"
    
    def _extract_count_from_search_page(self, soup: BeautifulSoup, agency_name: str) -> Optional[int]:
        """
        Extract document count from search results page.
        
        Args:
            soup: BeautifulSoup object of the page
            agency_name: Name of the agency for logging
            
        Returns:
            Document count or None if not found
        """
        # Enhanced patterns for Federal Register website
        patterns = [
            # "Showing 1-20 of 1,234 results" (most common)
            r'showing\s+\d+\s*-\s*\d+\s+of\s+([\d,]+)\s+results?',
            # "1,234 documents found"
            r'([\d,]+)\s+documents?\s+found',
            # "Found 1,234 documents"
            r'found\s+([\d,]+)\s+documents?',
            # "1,234 total results"
            r'([\d,]+)\s+total\s+results?',
            # "Results: 1,234"
            r'results?\s*:\s*([\d,]+)',
            # "1,234 matches"
            r'([\d,]+)\s+matches?',
            # Federal Register specific: "1,234 documents match your search"
            r'([\d,]+)\s+documents?\s+match\s+your\s+search',
        ]
        
        # Get the full page text for comprehensive search
        full_text = soup.get_text()
        
        # Search in specific elements first (more reliable)
        priority_elements = [
            soup.find('div', class_='search-count'),
            soup.find('div', class_='results-count'),
            soup.find('div', class_='search-summary'),
            soup.find('div', class_='pagination-summary'),
            soup.find('span', class_='search-count'),
            soup.find('p', class_='search-summary'),
        ]
        
        # Check priority elements first
        for element in priority_elements:
            if element:
                element_text = element.get_text().lower()
                for pattern in patterns:
                    matches = re.findall(pattern, element_text, re.IGNORECASE)
                    if matches:
                        try:
                            count_str = matches[0].replace(',', '')
                            count = int(count_str)
                            logger.debug(f"Extracted count {count} for {agency_name} from element using pattern: {pattern}")
                            return count
                        except (ValueError, IndexError):
                            continue
        
        # Search in full page text as fallback
        full_text_lower = full_text.lower()
        for pattern in patterns:
            matches = re.findall(pattern, full_text_lower, re.IGNORECASE)
            if matches:
                try:
                    count_str = matches[0].replace(',', '')
                    count = int(count_str)
                    logger.debug(f"Extracted count {count} for {agency_name} from full text using pattern: {pattern}")
                    return count
                except (ValueError, IndexError):
                    continue
        
        # Look for pagination info to estimate total
        pagination_info = self._extract_pagination_total(soup, agency_name)
        if pagination_info:
            return pagination_info
        
        # Last resort: count visible items (but warn that this might be incomplete)
        result_items = soup.find_all(['div', 'li'], class_=re.compile(r'document|result|item'))
        if result_items and len(result_items) > 0:
            logger.warning(f"Could not find total count for {agency_name}, counting visible items: {len(result_items)} (may be incomplete due to pagination)")
            return len(result_items)
        
        return None
    
    def _extract_pagination_total(self, soup: BeautifulSoup, agency_name: str) -> Optional[int]:
        """
        Extract total count from pagination information.
        
        Args:
            soup: BeautifulSoup object of the page
            agency_name: Name of the agency for logging
            
        Returns:
            Total document count or None if not found
        """
        # Look for pagination elements
        pagination_elements = [
            soup.find('div', class_='pagination'),
            soup.find('nav', class_='pagination'),
            soup.find('ul', class_='pagination'),
        ]
        
        for pagination in pagination_elements:
            if not pagination:
                continue
                
            # Look for "Page X of Y" or similar
            pagination_text = pagination.get_text().lower()
            
            # Patterns for pagination
            pagination_patterns = [
                r'page\s+\d+\s+of\s+(\d+)',
                r'(\d+)\s+pages?',
                r'showing\s+\d+\s*-\s*\d+\s+of\s+([\d,]+)',
            ]
            
            for pattern in pagination_patterns:
                matches = re.findall(pattern, pagination_text, re.IGNORECASE)
                if matches:
                    try:
                        if 'page' in pattern:
                            # If we found total pages, estimate total items
                            total_pages = int(matches[0])
                            # Assume 20 items per page (Federal Register default)
                            estimated_total = total_pages * 20
                            logger.debug(f"Estimated {estimated_total} documents for {agency_name} from {total_pages} pages")
                            return estimated_total
                        else:
                            # Direct count
                            count_str = matches[0].replace(',', '')
                            count = int(count_str)
                            logger.debug(f"Extracted count {count} for {agency_name} from pagination")
                            return count
                    except (ValueError, IndexError):
                        continue
        
        return None
    
    def _extract_count_from_agency_page(self, soup: BeautifulSoup, agency_name: str) -> Optional[int]:
        """
        Extract document count from agency page.
        
        Args:
            soup: BeautifulSoup object of the page
            agency_name: Name of the agency for logging
            
        Returns:
            Document count or None if not found
        """
        # Look for statistics or document counts on agency page
        patterns = [
            r'([\d,]+)\s+documents?',
            r'([\d,]+)\s+publications?',
            r'([\d,]+)\s+rules?',
            r'([\d,]+)\s+notices?',
        ]
        
        # Search in various elements
        text_sources = [
            str(soup.find('div', class_='agency-stats')),
            str(soup.find('div', class_='document-count')),
            str(soup.find('div', class_='statistics')),
            soup.get_text(),
        ]
        
        for text in text_sources:
            if not text:
                continue
                
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    try:
                        # Remove commas and convert to int
                        count_str = matches[0].replace(',', '')
                        count = int(count_str)
                        logger.debug(f"Extracted count {count} for {agency_name} from agency page")
                        return count
                    except (ValueError, IndexError):
                        continue
        
        return None
    
    def get_bulk_document_counts(self, agencies: List[Agency]) -> Dict[str, Tuple[int, bool, Optional[str]]]:
        """
        Get document counts for multiple agencies.
        
        Args:
            agencies: List of Agency objects
            
        Returns:
            Dictionary mapping agency slug to (count, success, error_message)
        """
        results = {}
        
        logger.info(f"Starting bulk document count fetch for {len(agencies)} agencies")
        
        for i, agency in enumerate(agencies, 1):
            logger.info(f"Processing agency {i}/{len(agencies)}: {agency.name}")
            
            count, success, error = self.get_agency_document_count(agency)
            results[agency.slug] = (count, success, error)
            
            # Progress logging
            if i % 10 == 0:
                successful = sum(1 for _, (_, s, _) in results.items() if s)
                logger.info(f"Progress: {i}/{len(agencies)} agencies processed, {successful} successful")
        
        successful = sum(1 for _, (_, s, _) in results.items() if s)
        logger.info(f"Bulk fetch completed: {successful}/{len(agencies)} agencies successful")
        
        return results
    
    def close(self):
        """Close the session."""
        if self.session:
            self.session.close()
            logger.debug("Direct fetcher session closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class DirectDocumentCounter:
    """Document counter using direct fetching instead of API."""
    
    def __init__(self, rate_limit: float = 2.0, timeout: int = 30):
        """
        Initialize the direct document counter.
        
        Args:
            rate_limit: Delay between requests in seconds
            timeout: Request timeout in seconds
        """
        self.fetcher = DirectFetcher(rate_limit=rate_limit, timeout=timeout)
        logger.info("Direct document counter initialized")
    
    def count_documents(self, agencies: List[Agency]) -> Dict[str, Tuple[int, bool, Optional[str]]]:
        """
        Count documents for agencies using direct fetching.
        
        Args:
            agencies: List of Agency objects
            
        Returns:
            Dictionary mapping agency slug to (count, success, error_message)
        """
        logger.info(f"Starting direct document counting for {len(agencies)} agencies")
        
        try:
            results = self.fetcher.get_bulk_document_counts(agencies)
            
            # Log summary
            successful = sum(1 for _, (_, s, _) in results.items() if s)
            total_docs = sum(count for _, (count, s, _) in results.items() if s)
            
            logger.info(f"Direct counting completed: {successful}/{len(agencies)} successful, {total_docs} total documents")
            
            return results
            
        except Exception as e:
            logger.error(f"Direct document counting failed: {str(e)}")
            raise APIError(f"Direct document counting failed: {str(e)}")
    
    def close(self):
        """Close the fetcher."""
        self.fetcher.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()