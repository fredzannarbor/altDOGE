"""
Content extractor for Federal Register documents.

Handles extraction of document content from XML and HTML sources with fallback mechanisms.
"""

import logging
import requests
import xml.etree.ElementTree as ET
from typing import Optional, Tuple
from bs4 import BeautifulSoup

from .config import Config
from .url_builder import URLBuilder
from .retry_handler import RetryHandler

logger = logging.getLogger(__name__)


class ContentExtractor:
    """Extracts document content with multiple fallback methods."""
    
    def __init__(self, session: requests.Session):
        """
        Initialize the content extractor.
        
        Args:
            session: Requests session for HTTP calls
        """
        self.session = session
        self.retry_handler = RetryHandler()
    
    def extract_content(self, document_data: dict) -> Tuple[Optional[str], str]:
        """
        Extract content with fallback methods.
        
        Args:
            document_data: Document metadata dictionary
            
        Returns:
            Tuple of (content, source) where source is 'xml', 'html', or None
        """
        document_number = document_data.get('document_number', 'unknown')
        
        # Try XML extraction first
        xml_url = URLBuilder.build_xml_url(document_data)
        if xml_url:
            logger.debug(f"Attempting XML extraction for {document_number}: {xml_url}")
            content = self._extract_from_xml(xml_url)
            if content:
                logger.debug(f"Successfully extracted content from XML for {document_number}")
                return content, 'xml'
            else:
                logger.debug(f"XML extraction failed for {document_number}")
        
        # Try HTML extraction as fallback
        html_url = URLBuilder.build_html_url(document_data)
        if html_url:
            logger.debug(f"Attempting HTML extraction for {document_number}: {html_url}")
            content = self._extract_from_html(html_url)
            if content:
                logger.debug(f"Successfully extracted content from HTML for {document_number}")
                return content, 'html'
            else:
                logger.debug(f"HTML extraction failed for {document_number}")
        
        logger.warning(f"All content extraction methods failed for {document_number}")
        return None, None
    
    def _extract_from_xml(self, xml_url: str) -> Optional[str]:
        """
        Extract content from XML URL with retry logic.
        
        Args:
            xml_url: URL to XML document
            
        Returns:
            Extracted text content or None if failed
        """
        def _fetch_and_parse_xml():
            response = self.session.get(xml_url, timeout=Config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # Parse XML content
            root = ET.fromstring(response.content)
            
            # Extract text from all elements
            text_parts = []
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    text_parts.append(elem.text.strip())
                if elem.tail and elem.tail.strip():
                    text_parts.append(elem.tail.strip())
            
            # Join and clean up text
            content = ' '.join(text_parts)
            content = ' '.join(content.split())  # Normalize whitespace
            
            return self._clean_and_validate_content(content)
        
        # Execute with retry logic
        result, success, error = self.retry_handler.execute_with_retry(_fetch_and_parse_xml)
        
        if not success:
            logger.debug(f"Failed to extract XML content from {xml_url}: {error}")
            return None
        
        return result
    
    def _extract_from_html(self, html_url: str) -> Optional[str]:
        """
        Extract content from HTML URL with retry logic.
        
        Args:
            html_url: URL to HTML document page
            
        Returns:
            Extracted text content or None if failed
        """
        def _fetch_and_parse_html():
            response = self.session.get(html_url, timeout=Config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find the main document content
            content_selectors = [
                '.full-text',
                '.document-content',
                '.body-column',
                '.document-body',
                'article',
                '.content'
            ]
            
            content_element = None
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    break
            
            if not content_element:
                # Fallback to body content, excluding navigation and headers
                content_element = soup.find('body')
                if content_element:
                    # Remove navigation, headers, footers, and sidebars
                    for unwanted in content_element.find_all(['nav', 'header', 'footer', 'aside', 'script', 'style']):
                        unwanted.decompose()
            
            if content_element:
                # Extract text content
                text = content_element.get_text(separator=' ', strip=True)
                return self._clean_and_validate_content(text)
            else:
                logger.debug(f"No content element found in HTML from {html_url}")
                return None
        
        # Execute with retry logic
        result, success, error = self.retry_handler.execute_with_retry(_fetch_and_parse_html)
        
        if not success:
            logger.debug(f"Failed to extract HTML content from {html_url}: {error}")
            return None
        
        return result
    
    def _clean_and_validate_content(self, content: str) -> Optional[str]:
        """
        Clean and validate extracted content.
        
        Args:
            content: Raw extracted content
            
        Returns:
            Cleaned content or None if invalid
        """
        if not content or not content.strip():
            return None
        
        # Clean up whitespace
        content = ' '.join(content.split())
        
        # Check minimum content length
        if len(content) < 50:
            logger.debug(f"Content too short ({len(content)} chars), likely not actual document content")
            return None
        
        # Truncate if too long
        if len(content) > Config.MAX_DOCUMENT_LENGTH:
            logger.warning(f"Content truncated from {len(content)} to {Config.MAX_DOCUMENT_LENGTH} characters")
            content = content[:Config.MAX_DOCUMENT_LENGTH]
        
        return content