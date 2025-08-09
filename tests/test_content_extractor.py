"""
Tests for ContentExtractor class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

from cfr_document_analyzer.content_extractor import ContentExtractor


class TestContentExtractor:
    """Test cases for ContentExtractor class."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock requests session."""
        return Mock(spec=requests.Session)
    
    @pytest.fixture
    def content_extractor(self, mock_session):
        """Create ContentExtractor instance with mock session."""
        return ContentExtractor(mock_session)
    
    def test_extract_content_xml_success(self, content_extractor, mock_session):
        """Test successful content extraction from XML."""
        # Mock XML response
        xml_content = """<?xml version="1.0"?>
        <document>
            <title>Test Document</title>
            <body>This is test content for the document.</body>
        </document>"""
        
        mock_response = Mock()
        mock_response.content = xml_content.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        
        document_data = {
            'document_number': '2021-08964',
            'publication_date': '2021-04-29'
        }
        
        with patch('cfr_document_analyzer.content_extractor.URLBuilder') as mock_url_builder:
            mock_url_builder.build_xml_url.return_value = 'http://example.com/test.xml'
            mock_url_builder.build_html_url.return_value = 'http://example.com/test.html'
            
            content, source = content_extractor.extract_content(document_data)
            
            assert content is not None
            assert source == 'xml'
            assert 'Test Document' in content
            assert 'This is test content' in content
    
    def test_extract_content_xml_fails_html_success(self, content_extractor, mock_session):
        """Test content extraction falls back to HTML when XML fails."""
        # Mock XML failure and HTML success
        def mock_get(url, **kwargs):
            if 'xml' in url:
                raise requests.exceptions.HTTPError("404 Not Found")
            else:
                mock_response = Mock()
                mock_response.content = b"""
                <html>
                    <body>
                        <div class="full-text">
                            <h1>Test Document</h1>
                            <p>This is HTML content for the document.</p>
                        </div>
                    </body>
                </html>"""
                mock_response.raise_for_status.return_value = None
                return mock_response
        
        mock_session.get.side_effect = mock_get
        
        document_data = {
            'document_number': '2021-08964',
            'publication_date': '2021-04-29'
        }
        
        with patch('cfr_document_analyzer.content_extractor.URLBuilder') as mock_url_builder:
            mock_url_builder.build_xml_url.return_value = 'http://example.com/test.xml'
            mock_url_builder.build_html_url.return_value = 'http://example.com/test.html'
            
            content, source = content_extractor.extract_content(document_data)
            
            assert content is not None
            assert source == 'html'
            assert 'Test Document' in content
            assert 'This is HTML content' in content
    
    def test_extract_content_both_fail(self, content_extractor, mock_session):
        """Test content extraction when both XML and HTML fail."""
        mock_session.get.side_effect = requests.exceptions.HTTPError("404 Not Found")
        
        document_data = {
            'document_number': '2021-08964',
            'publication_date': '2021-04-29'
        }
        
        with patch('cfr_document_analyzer.content_extractor.URLBuilder') as mock_url_builder:
            mock_url_builder.build_xml_url.return_value = 'http://example.com/test.xml'
            mock_url_builder.build_html_url.return_value = 'http://example.com/test.html'
            
            content, source = content_extractor.extract_content(document_data)
            
            assert content is None
            assert source is None
    
    def test_clean_and_validate_content_valid(self, content_extractor):
        """Test content cleaning and validation with valid content."""
        content = "   This is a test document with   multiple   spaces   and content.   "
        
        cleaned = content_extractor._clean_and_validate_content(content)
        
        assert cleaned == "This is a test document with multiple spaces and content."
    
    def test_clean_and_validate_content_too_short(self, content_extractor):
        """Test content validation rejects content that's too short."""
        content = "Short"
        
        cleaned = content_extractor._clean_and_validate_content(content)
        
        assert cleaned is None
    
    def test_clean_and_validate_content_empty(self, content_extractor):
        """Test content validation rejects empty content."""
        content = "   "
        
        cleaned = content_extractor._clean_and_validate_content(content)
        
        assert cleaned is None
    
    @patch('cfr_document_analyzer.content_extractor.Config.MAX_DOCUMENT_LENGTH', 100)
    def test_clean_and_validate_content_truncation(self, content_extractor):
        """Test content truncation when too long."""
        content = "A" * 200  # 200 characters
        
        cleaned = content_extractor._clean_and_validate_content(content)
        
        assert len(cleaned) == 100
        assert cleaned == "A" * 100
    
    def test_extract_from_xml_with_retry_success(self, content_extractor, mock_session):
        """Test XML extraction with retry logic success."""
        xml_content = """<?xml version="1.0"?>
        <document>
            <title>Test Document</title>
            <body>This is test content.</body>
        </document>"""
        
        mock_response = Mock()
        mock_response.content = xml_content.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        
        content = content_extractor._extract_from_xml('http://example.com/test.xml')
        
        assert content is not None
        assert 'Test Document' in content
        assert 'This is test content' in content
    
    def test_extract_from_xml_with_retry_failure(self, content_extractor, mock_session):
        """Test XML extraction with retry logic failure."""
        mock_session.get.side_effect = requests.exceptions.HTTPError("404 Not Found")
        
        content = content_extractor._extract_from_xml('http://example.com/test.xml')
        
        assert content is None
    
    def test_extract_from_html_with_retry_success(self, content_extractor, mock_session):
        """Test HTML extraction with retry logic success."""
        html_content = b"""
        <html>
            <body>
                <div class="full-text">
                    <h1>Test Document</h1>
                    <p>This is HTML content for the document.</p>
                </div>
            </body>
        </html>"""
        
        mock_response = Mock()
        mock_response.content = html_content
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        
        content = content_extractor._extract_from_html('http://example.com/test.html')
        
        assert content is not None
        assert 'Test Document' in content
        assert 'This is HTML content' in content
    
    def test_extract_from_html_fallback_selectors(self, content_extractor, mock_session):
        """Test HTML extraction with fallback content selectors."""
        html_content = b"""
        <html>
            <body>
                <nav>Navigation</nav>
                <div class="document-body">
                    <h1>Test Document</h1>
                    <p>This is the main content.</p>
                </div>
                <footer>Footer</footer>
            </body>
        </html>"""
        
        mock_response = Mock()
        mock_response.content = html_content
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        
        content = content_extractor._extract_from_html('http://example.com/test.html')
        
        assert content is not None
        assert 'Test Document' in content
        assert 'This is the main content' in content
        assert 'Navigation' not in content
        assert 'Footer' not in content