"""
Document retriever for CFR Document Analyzer.

Uses direct fetching approach to retrieve full document content
from the Federal Register website with XML parsing and caching.
"""

import time
import logging
import requests
import xml.etree.ElementTree as ET
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from .config import Config
from .models import Document
from .database import Database
from .utils import truncate_text


logger = logging.getLogger(__name__)


class DocumentRetriever:
    """Document retriever using direct fetching with content extraction capabilities."""
    
    def __init__(self, database: Database, use_cache: bool = True):
        """
        Initialize the document retriever.
        
        Args:
            database: Database instance for caching
            use_cache: Whether to use document caching
        """
        self.database = database
        self.use_cache = use_cache
        self.rate_limit = Config.FR_API_RATE_LIMIT
        self.session = requests.Session()
        
        # Set realistic headers to avoid blocking
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        logger.info("Document retriever initialized with direct fetching")
    
    def get_agency_documents(self, agency_slug: str, limit: Optional[int] = None) -> List[Document]:
        """
        Get documents for a specific agency with full content.
        
        Args:
            agency_slug: Agency identifier
            limit: Maximum number of documents to retrieve
            
        Returns:
            List of Document objects with content
        """
        logger.info(f"Retrieving documents for agency: {agency_slug}")
        
        # Check cache first if enabled
        if self.use_cache:
            cached_docs = self.database.get_documents_by_agency(agency_slug, limit)
            if cached_docs:
                logger.info(f"Found {len(cached_docs)} cached documents for {agency_slug}")
                return [self._dict_to_document(doc) for doc in cached_docs]
        
        # Fetch from web
        try:
            documents = self._fetch_documents_from_web(agency_slug, limit)
            
            # Fetch content for each document
            documents_with_content = []
            for i, doc_data in enumerate(documents):
                if limit and i >= limit:
                    break
                
                logger.info(f"Processing document {i+1}/{min(len(documents), limit or len(documents))}: {doc_data.get('document_number', 'unknown')}")
                
                document = self._create_document_with_content(doc_data, agency_slug)
                if document and document.content:
                    documents_with_content.append(document)
                    
                    # Cache the document
                    if self.use_cache:
                        self._cache_document(document)
                
                # Rate limiting
                time.sleep(self.rate_limit)
            
            logger.info(f"Retrieved {len(documents_with_content)} documents with content for {agency_slug}")
            return documents_with_content
            
        except Exception as e:
            logger.error(f"Failed to retrieve documents for {agency_slug}: {e}")
            return []
    
    def _fetch_documents_from_web(self, agency_slug: str, limit: Optional[int]) -> List[Dict]:
        """
        Fetch document metadata by scraping Federal Register website.
        
        Args:
            agency_slug: Agency identifier
            limit: Maximum documents to fetch
            
        Returns:
            List of document metadata dictionaries
        """
        documents = []
        
        try:
            # Build search URL for the agency
            search_url = "https://www.federalregister.gov/documents/search"
            params = {
                'conditions[agencies][]': agency_slug,
                'order': 'newest',
                'per_page': min(limit or 20, 20)
            }
            
            logger.info(f"Fetching documents from {search_url} for agency {agency_slug}")
            
            response = self.session.get(search_url, params=params, timeout=Config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # Parse HTML to extract document information
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find document entries on the page
            document_elements = soup.find_all(['div', 'article'], class_=re.compile(r'document|result'))
            
            if not document_elements:
                # Try alternative selectors
                document_elements = soup.find_all('li', class_=re.compile(r'document'))
                
            if not document_elements:
                # Try finding links to individual documents
                document_links = soup.find_all('a', href=re.compile(r'/documents/\d{4}/\d{2}/\d{2}/'))
                document_elements = [link.parent for link in document_links if link.parent]
            
            logger.info(f"Found {len(document_elements)} document elements on page")
            
            for i, element in enumerate(document_elements):
                if limit and i >= limit:
                    break
                
                doc_data = self._extract_document_info_from_element(element, agency_slug)
                if doc_data:
                    documents.append(doc_data)
            
            # If we didn't find enough documents, try the JSON API as fallback
            if len(documents) < (limit or 5):
                logger.info("Trying JSON API as fallback...")
                json_docs = self._try_json_api_fallback(agency_slug, limit)
                documents.extend(json_docs)
                
                # Remove duplicates based on document_number
                seen = set()
                unique_docs = []
                for doc in documents:
                    doc_num = doc.get('document_number')
                    if doc_num and doc_num not in seen:
                        seen.add(doc_num)
                        unique_docs.append(doc)
                documents = unique_docs
            
            logger.info(f"Fetched {len(documents)} document records from web scraping")
            return documents[:limit] if limit else documents
            
        except Exception as e:
            logger.error(f"Error fetching documents for {agency_slug}: {e}")
            return []
    
    def _create_document_with_content(self, doc_data: Dict, agency_slug: str) -> Optional[Document]:
        """
        Create Document object with full content from API data.
        
        Args:
            doc_data: Document metadata from API
            agency_slug: Agency identifier
            
        Returns:
            Document object with content or None if failed
        """
        try:
            # Extract basic metadata
            document_number = doc_data.get('document_number', '')
            title = doc_data.get('title', '')
            publication_date = doc_data.get('publication_date', '')
            xml_url = doc_data.get('full_text_xml_url', '')
            
            if not document_number or not title:
                logger.warning(f"Missing required fields for document: {doc_data}")
                return None
            
            # Extract CFR references
            cfr_citation = None
            cfr_refs = doc_data.get('cfr_references', [])
            if cfr_refs and isinstance(cfr_refs, list) and len(cfr_refs) > 0:
                cfr_citation = cfr_refs[0].get('citation', '')
            
            # Fetch document content
            content = ""
            if xml_url:
                content = self._fetch_document_content(xml_url)
            
            if not content:
                logger.warning(f"No content retrieved for document {document_number}")
                return None
            
            # Create Document object
            document = Document(
                document_number=document_number,
                title=title,
                agency_slug=agency_slug,
                publication_date=publication_date,
                cfr_citation=cfr_citation,
                content=content,
                content_length=len(content)
            )
            
            return document
            
        except Exception as e:
            logger.error(f"Error creating document from API data: {e}")
            return None
    
    def _fetch_document_content(self, xml_url: str) -> str:
        """
        Fetch and parse document content from XML URL.
        
        Args:
            xml_url: URL to document XML
            
        Returns:
            Extracted text content
        """
        try:
            logger.debug(f"Fetching content from: {xml_url}")
            
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
            
            # Truncate if too long
            if len(content) > Config.MAX_DOCUMENT_LENGTH:
                content = truncate_text(content, Config.MAX_DOCUMENT_LENGTH)
                logger.warning(f"Document content truncated to {Config.MAX_DOCUMENT_LENGTH} characters")
            
            return content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error fetching content from {xml_url}: {e}")
            return ""
        except ET.ParseError as e:
            logger.error(f"XML parsing error for {xml_url}: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error fetching content from {xml_url}: {e}")
            return ""
    
    def _cache_document(self, document: Document) -> None:
        """
        Cache document in database.
        
        Args:
            document: Document to cache
        """
        try:
            doc_data = {
                'document_number': document.document_number,
                'title': document.title,
                'agency_slug': document.agency_slug,
                'publication_date': document.publication_date,
                'cfr_citation': document.cfr_citation,
                'content': document.content
            }
            
            doc_id = self.database.store_document(doc_data)
            document.id = doc_id
            logger.debug(f"Cached document {document.document_number} with ID {doc_id}")
            
        except Exception as e:
            logger.error(f"Error caching document {document.document_number}: {e}")
    
    def _dict_to_document(self, doc_dict: Dict) -> Document:
        """
        Convert database dictionary to Document object.
        
        Args:
            doc_dict: Document data from database
            
        Returns:
            Document object
        """
        return Document(
            id=doc_dict['id'],
            document_number=doc_dict['document_number'],
            title=doc_dict['title'],
            agency_slug=doc_dict['agency_slug'],
            publication_date=doc_dict['publication_date'],
            cfr_citation=doc_dict['cfr_citation'],
            content=doc_dict['content'],
            content_length=doc_dict['content_length']
        )
    
    def get_cached_document_count(self, agency_slug: str) -> int:
        """
        Get count of cached documents for an agency.
        
        Args:
            agency_slug: Agency identifier
            
        Returns:
            Number of cached documents
        """
        try:
            query = "SELECT COUNT(*) FROM documents WHERE agency_slug = ?"
            result = self.database.execute_query(query, (agency_slug,))
            return result[0][0] if result else 0
        except Exception as e:
            logger.error(f"Error getting cached document count: {e}")
            return 0
    
    def _extract_document_info_from_element(self, element, agency_slug: str) -> Optional[Dict]:
        """
        Extract document information from HTML element.
        
        Args:
            element: BeautifulSoup element containing document info
            agency_slug: Agency identifier
            
        Returns:
            Document metadata dictionary or None
        """
        try:
            # Look for document number and title
            doc_number = None
            title = None
            pub_date = None
            xml_url = None
            
            # Try to find document number
            doc_link = element.find('a', href=re.compile(r'/documents/\d{4}/\d{2}/\d{2}/'))
            if doc_link:
                href = doc_link.get('href', '')
                # Extract document number from URL pattern
                match = re.search(r'/documents/\d{4}/\d{2}/\d{2}/([^/]+)', href)
                if match:
                    doc_number = match.group(1)
                
                # Get title from link text or nearby elements
                title = doc_link.get_text(strip=True)
                if not title:
                    title_elem = element.find(['h2', 'h3', 'h4', 'strong'])
                    if title_elem:
                        title = title_elem.get_text(strip=True)
            
            # Try alternative methods if not found
            if not doc_number:
                # Look for document number in text
                text = element.get_text()
                doc_match = re.search(r'(\d{4}-\d{5}|\d{4}-\w+-\d+)', text)
                if doc_match:
                    doc_number = doc_match.group(1)
            
            if not title and doc_number:
                # Use document number as fallback title
                title = f"Document {doc_number}"
            
            # Look for publication date
            date_elem = element.find(['time', 'span'], class_=re.compile(r'date'))
            if date_elem:
                pub_date = date_elem.get('datetime') or date_elem.get_text(strip=True)
            
            # Construct XML URL if we have document info
            if doc_number and '/' in doc_number:
                # Convert document number to XML URL
                xml_url = f"https://www.federalregister.gov/documents/full_text/xml/{doc_number}.xml"
            elif doc_link:
                # Try to construct from document page URL
                doc_url = doc_link.get('href')
                if doc_url:
                    xml_url = doc_url.replace('/documents/', '/documents/full_text/xml/') + '.xml'
            
            if doc_number and title:
                return {
                    'document_number': doc_number,
                    'title': title,
                    'publication_date': pub_date,
                    'full_text_xml_url': xml_url,
                    'cfr_references': []
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting document info: {e}")
            return None
    
    def _try_json_api_fallback(self, agency_slug: str, limit: Optional[int]) -> List[Dict]:
        """
        Try JSON API as fallback when HTML scraping doesn't find enough documents.
        
        Args:
            agency_slug: Agency identifier
            limit: Maximum documents to fetch
            
        Returns:
            List of document metadata dictionaries
        """
        try:
            api_url = "https://www.federalregister.gov/api/v1/documents.json"
            params = {
                'conditions[agencies][]': agency_slug,
                'per_page': min(limit or 10, 10),
                'fields[]': ['title', 'document_number', 'publication_date', 'full_text_xml_url', 'cfr_references']
            }
            
            # Set JSON accept header
            headers = self.session.headers.copy()
            headers['Accept'] = 'application/json'
            
            response = self.session.get(api_url, params=params, headers=headers, timeout=Config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            documents = data.get('results', [])
            
            logger.info(f"JSON API fallback found {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.debug(f"JSON API fallback failed: {e}")
            return []
    
    def close(self):
        """Clean up resources."""
        if self.session:
            self.session.close()