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
from .url_builder import URLBuilder
from .content_extractor import ContentExtractor


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
        self.content_extractor = ContentExtractor(self.session)
        
        # Set realistic headers to avoid blocking
        self.session.headers.update({
            'User-Agent': 'CFR-Document-Analyzer/1.0 (Educational Research Tool)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
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
                    
                    # Always store document in database to get an ID (required for analysis)
                    # Even if caching is disabled, we need the document ID for analysis storage
                    self._cache_document(document)
                
                # Rate limiting
                time.sleep(self.rate_limit)
            
            # Log summary statistics
            total_attempted = len(documents)
            successful_retrievals = len(documents_with_content)
            failed_retrievals = total_attempted - successful_retrievals
            success_rate = (successful_retrievals / total_attempted * 100) if total_attempted > 0 else 0
            
            logger.info(f"Document retrieval summary for {agency_slug}:")
            logger.info(f"  Total documents attempted: {total_attempted}")
            logger.info(f"  Successful retrievals: {successful_retrievals}")
            logger.info(f"  Failed retrievals: {failed_retrievals}")
            logger.info(f"  Success rate: {success_rate:.1f}%")
            
            return documents_with_content
            
        except Exception as e:
            logger.error(f"Failed to retrieve documents for {agency_slug}: {e}")
            return []
    
    def _fetch_documents_from_web(self, agency_slug: str, limit: Optional[int]) -> List[Dict]:
        """
        Fetch document metadata by scraping Federal Register website with pagination.
        
        Args:
            agency_slug: Agency identifier
            limit: Maximum documents to fetch
            
        Returns:
            List of document metadata dictionaries
        """
        documents = []
        
        try:
            # Try JSON API first as it's more reliable for pagination
            logger.info("Trying JSON API for document retrieval...")
            json_docs = self._fetch_documents_from_json_api(agency_slug, limit)
            if json_docs:
                logger.info(f"Successfully fetched {len(json_docs)} documents from JSON API")
                return json_docs
            
            # Fallback to HTML scraping if JSON API fails
            logger.info("JSON API failed, falling back to HTML scraping...")
            
            # Build search URL for the agency
            search_url = "https://www.federalregister.gov/documents/search"
            params = {
                'conditions[agencies][]': agency_slug,
                'order': 'newest',
                'per_page': min(limit or 100, 100)  # Increased default from 20 to 100
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
            
            # Fetch document content using ContentExtractor
            content, content_source = self.content_extractor.extract_content(doc_data)
            
            if not content:
                logger.warning(f"No content retrieved for document {document_number}")
                return None
            
            logger.debug(f"Content retrieved from {content_source} for document {document_number}")
            
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
                # Look for document number in text with expanded patterns
                text = element.get_text()
                doc_match = re.search(r'(\d{4}-\d{5}|\d{4}-\w+-\d+|E\d-\d{5})', text)
                if doc_match:
                    doc_number = doc_match.group(1)
            
            if not title and doc_number:
                # Use document number as fallback title
                title = f"Document {doc_number}"
            
            # Look for publication date
            date_elem = element.find(['time', 'span'], class_=re.compile(r'date'))
            if date_elem:
                pub_date = date_elem.get('datetime') or date_elem.get_text(strip=True)
            
            # Construct XML URL using URLBuilder
            if doc_number:
                doc_data_temp = {
                    'document_number': doc_number,
                    'publication_date': pub_date
                }
                xml_url = URLBuilder.build_xml_url(doc_data_temp)
            
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
    
    def _fetch_documents_from_json_api(self, agency_slug: str, limit: Optional[int]) -> List[Dict]:
        """
        Fetch document metadata from Federal Register JSON API with pagination.
        
        Args:
            agency_slug: Agency identifier
            limit: Maximum documents to fetch
            
        Returns:
            List of document metadata dictionaries
        """
        documents = []
        page = 1
        per_page = 100  # Maximum allowed by API
        
        try:
            api_url = "https://www.federalregister.gov/api/v1/documents.json"
            
            # Set JSON accept header
            headers = self.session.headers.copy()
            headers['Accept'] = 'application/json'
            
            while True:
                params = {
                    'conditions[agencies][]': agency_slug,
                    'per_page': per_page,
                    'page': page,
                    'fields[]': ['title', 'document_number', 'publication_date', 'full_text_xml_url', 'cfr_references']
                }
                
                logger.debug(f"Fetching page {page} from JSON API for {agency_slug}")
                
                response = self.session.get(api_url, params=params, headers=headers, timeout=Config.REQUEST_TIMEOUT)
                response.raise_for_status()
                
                data = response.json()
                page_documents = data.get('results', [])
                
                if not page_documents:
                    logger.debug(f"No more documents found on page {page}")
                    break
                
                documents.extend(page_documents)
                logger.info(f"Retrieved {len(page_documents)} documents from page {page}, total: {len(documents)}")
                
                # Check if we've reached the limit
                if limit and len(documents) >= limit:
                    documents = documents[:limit]
                    logger.info(f"Reached document limit of {limit}")
                    break
                
                # Check if there are more pages
                total_pages = data.get('total_pages', 1)
                if page >= total_pages:
                    logger.debug(f"Reached last page ({total_pages})")
                    break
                
                page += 1
                
                # Rate limiting between pages
                time.sleep(self.rate_limit)
            
            logger.info(f"JSON API retrieved {len(documents)} total documents for {agency_slug}")
            return documents
            
        except Exception as e:
            logger.error(f"JSON API failed for {agency_slug}: {e}")
            return []
    
    def close(self):
        """Clean up resources."""
        if self.session:
            self.session.close()