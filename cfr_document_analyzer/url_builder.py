"""
URL builder for Federal Register document URLs.

Handles correct construction of XML and HTML URLs for Federal Register documents.
"""

import re
import logging
from typing import Dict, Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class URLBuilder:
    """Builder class for Federal Register document URLs."""
    
    # Federal Register base URLs
    BASE_URL = "https://www.federalregister.gov"
    XML_BASE_URL = "https://www.federalregister.gov/documents/full_text/xml"
    
    # Document number patterns
    DOCUMENT_NUMBER_PATTERNS = [
        r'^\d{4}-\d{5}$',           # Standard format: 2021-08964
        r'^\d{4}-\w+-\d+$',         # Alternative format: 2021-ABC-123
        r'^E\d-\d{5}$',             # Executive format: E9-30894
        r'^\d{4}/\d{2}/\d{2}/[\w-]+$'  # Date-based format: 2021/04/29/document-slug
    ]
    
    @staticmethod
    def validate_document_number(doc_number: str) -> bool:
        """
        Validate document number format.
        
        Args:
            doc_number: Document number to validate
            
        Returns:
            True if valid format, False otherwise
        """
        if not doc_number:
            return False
            
        for pattern in URLBuilder.DOCUMENT_NUMBER_PATTERNS:
            if re.match(pattern, doc_number):
                return True
                
        logger.debug(f"Invalid document number format: {doc_number}")
        return False
    
    @staticmethod
    def build_xml_url(document_data: Dict) -> Optional[str]:
        """
        Build XML URL from document metadata.
        
        Args:
            document_data: Document metadata dictionary
            
        Returns:
            XML URL string or None if cannot be constructed
        """
        try:
            # First try to use the provided XML URL
            xml_url = document_data.get('full_text_xml_url')
            if xml_url and xml_url.startswith('http'):
                return xml_url
            
            # Extract document number and publication date
            doc_number = document_data.get('document_number', '')
            pub_date = document_data.get('publication_date', '')
            
            if not doc_number:
                logger.warning("No document number provided for XML URL construction")
                return None
            
            # Validate document number
            if not URLBuilder.validate_document_number(doc_number):
                logger.warning(f"Invalid document number for XML URL: {doc_number}")
                return None
            
            # Handle different document number formats
            if '/' in doc_number:
                # Date-based format: already includes path structure
                xml_url = f"{URLBuilder.XML_BASE_URL}/{doc_number}.xml"
            elif pub_date:
                # Standard format with publication date
                try:
                    # Parse publication date (assuming YYYY-MM-DD format)
                    date_parts = pub_date.split('-')
                    if len(date_parts) >= 3:
                        year, month, day = date_parts[0], date_parts[1], date_parts[2]
                        xml_url = f"{URLBuilder.XML_BASE_URL}/{year}/{month}/{day}/{doc_number}.xml"
                    else:
                        # Fallback to simple format
                        xml_url = f"{URLBuilder.XML_BASE_URL}/{doc_number}.xml"
                except (ValueError, IndexError):
                    # Fallback to simple format
                    xml_url = f"{URLBuilder.XML_BASE_URL}/{doc_number}.xml"
            else:
                # Simple format without date
                xml_url = f"{URLBuilder.XML_BASE_URL}/{doc_number}.xml"
            
            logger.debug(f"Built XML URL: {xml_url}")
            return xml_url
            
        except Exception as e:
            logger.error(f"Error building XML URL: {e}")
            return None
    
    @staticmethod
    def build_html_url(document_data: Dict) -> Optional[str]:
        """
        Build HTML URL from document metadata as fallback.
        
        Args:
            document_data: Document metadata dictionary
            
        Returns:
            HTML URL string or None if cannot be constructed
        """
        try:
            # Extract document number and publication date
            doc_number = document_data.get('document_number', '')
            pub_date = document_data.get('publication_date', '')
            
            if not doc_number:
                logger.warning("No document number provided for HTML URL construction")
                return None
            
            # Validate document number
            if not URLBuilder.validate_document_number(doc_number):
                logger.warning(f"Invalid document number for HTML URL: {doc_number}")
                return None
            
            # Handle different document number formats
            if '/' in doc_number:
                # Date-based format: already includes path structure
                html_url = f"{URLBuilder.BASE_URL}/documents/{doc_number}"
            elif pub_date:
                # Standard format with publication date
                try:
                    # Parse publication date (assuming YYYY-MM-DD format)
                    date_parts = pub_date.split('-')
                    if len(date_parts) >= 3:
                        year, month, day = date_parts[0], date_parts[1], date_parts[2]
                        html_url = f"{URLBuilder.BASE_URL}/documents/{year}/{month}/{day}/{doc_number}"
                    else:
                        # Fallback to simple format
                        html_url = f"{URLBuilder.BASE_URL}/documents/{doc_number}"
                except (ValueError, IndexError):
                    # Fallback to simple format
                    html_url = f"{URLBuilder.BASE_URL}/documents/{doc_number}"
            else:
                # Simple format without date
                html_url = f"{URLBuilder.BASE_URL}/documents/{doc_number}"
            
            logger.debug(f"Built HTML URL: {html_url}")
            return html_url
            
        except Exception as e:
            logger.error(f"Error building HTML URL: {e}")
            return None
    
    @staticmethod
    def extract_document_number_from_url(url: str) -> Optional[str]:
        """
        Extract document number from Federal Register URL.
        
        Args:
            url: Federal Register document URL
            
        Returns:
            Document number or None if cannot be extracted
        """
        try:
            # Pattern to match document URLs
            patterns = [
                r'/documents/(\d{4}/\d{2}/\d{2}/[\w-]+)',
                r'/documents/(\d{4}-\d{5})',
                r'/documents/(\d{4}-\w+-\d+)',
                r'/documents/(E\d-\d{5})'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            logger.debug(f"Could not extract document number from URL: {url}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting document number from URL: {e}")
            return None