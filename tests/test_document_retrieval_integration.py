"""
Integration tests for document retrieval fixes.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from cfr_document_analyzer.document_retriever import DocumentRetriever
from cfr_document_analyzer.database import Database


class TestDocumentRetrievalIntegration:
    """Integration tests for document retrieval system."""
    
    @pytest.fixture
    def mock_database(self):
        """Create a mock database."""
        return Mock(spec=Database)
    
    @pytest.fixture
    def document_retriever(self, mock_database):
        """Create DocumentRetriever with mock database."""
        return DocumentRetriever(mock_database, use_cache=False)
    
    def test_get_agency_documents_with_pagination(self, document_retriever, mock_database):
        """Test document retrieval with pagination handling."""
        # Mock JSON API responses for pagination
        page1_response = {
            'results': [
                {
                    'document_number': '2021-08964',
                    'title': 'Document 1',
                    'publication_date': '2021-04-29',
                    'full_text_xml_url': 'http://example.com/doc1.xml',
                    'cfr_references': []
                },
                {
                    'document_number': '2021-08965',
                    'title': 'Document 2',
                    'publication_date': '2021-04-30',
                    'full_text_xml_url': 'http://example.com/doc2.xml',
                    'cfr_references': []
                }
            ],
            'total_pages': 2
        }
        
        page2_response = {
            'results': [
                {
                    'document_number': '2021-08966',
                    'title': 'Document 3',
                    'publication_date': '2021-05-01',
                    'full_text_xml_url': 'http://example.com/doc3.xml',
                    'cfr_references': []
                }
            ],
            'total_pages': 2
        }
        
        # Mock XML content responses
        xml_content = """<?xml version="1.0"?>
        <document>
            <title>Test Document</title>
            <body>This is test content for the document with sufficient length to pass validation.</body>
        </document>"""
        
        def mock_get(url, **kwargs):
            mock_response = Mock()
            
            if 'documents.json' in url:
                # JSON API responses
                params = kwargs.get('params', {})
                page = params.get('page', 1)
                if page == 1:
                    mock_response.json.return_value = page1_response
                else:
                    mock_response.json.return_value = page2_response
            else:
                # XML content responses
                mock_response.content = xml_content.encode('utf-8')
            
            mock_response.raise_for_status.return_value = None
            return mock_response
        
        document_retriever.session.get = mock_get
        
        # Test retrieval without limit (should get all pages)
        documents = document_retriever.get_agency_documents('test-agency')
        
        assert len(documents) == 3
        assert documents[0].document_number == '2021-08964'
        assert documents[1].document_number == '2021-08965'
        assert documents[2].document_number == '2021-08966'
        
        # Verify all documents have content
        for doc in documents:
            assert doc.content is not None
            assert len(doc.content) > 50  # Should pass validation
    
    def test_get_agency_documents_with_limit(self, document_retriever, mock_database):
        """Test document retrieval respects limit parameter."""
        # Mock JSON API response
        api_response = {
            'results': [
                {
                    'document_number': f'2021-0896{i}',
                    'title': f'Document {i}',
                    'publication_date': '2021-04-29',
                    'full_text_xml_url': f'http://example.com/doc{i}.xml',
                    'cfr_references': []
                }
                for i in range(1, 6)  # 5 documents
            ],
            'total_pages': 1
        }
        
        xml_content = """<?xml version="1.0"?>
        <document>
            <title>Test Document</title>
            <body>This is test content for the document with sufficient length to pass validation.</body>
        </document>"""
        
        def mock_get(url, **kwargs):
            mock_response = Mock()
            
            if 'documents.json' in url:
                mock_response.json.return_value = api_response
            else:
                mock_response.content = xml_content.encode('utf-8')
            
            mock_response.raise_for_status.return_value = None
            return mock_response
        
        document_retriever.session.get = mock_get
        
        # Test with limit of 3
        documents = document_retriever.get_agency_documents('test-agency', limit=3)
        
        assert len(documents) == 3
        assert all(doc.content is not None for doc in documents)
    
    def test_get_agency_documents_with_xml_fallback_to_html(self, document_retriever, mock_database):
        """Test document retrieval falls back to HTML when XML fails."""
        # Mock JSON API response
        api_response = {
            'results': [
                {
                    'document_number': '2021-08964',
                    'title': 'Document 1',
                    'publication_date': '2021-04-29',
                    'full_text_xml_url': 'http://example.com/doc1.xml',
                    'cfr_references': []
                }
            ],
            'total_pages': 1
        }
        
        html_content = b"""
        <html>
            <body>
                <div class="full-text">
                    <h1>Test Document</h1>
                    <p>This is HTML content for the document with sufficient length to pass validation and testing.</p>
                </div>
            </body>
        </html>"""
        
        def mock_get(url, **kwargs):
            mock_response = Mock()
            
            if 'documents.json' in url:
                mock_response.json.return_value = api_response
            elif 'xml' in url:
                # XML request fails
                raise requests.exceptions.HTTPError("404 Not Found")
            else:
                # HTML request succeeds
                mock_response.content = html_content
            
            mock_response.raise_for_status.return_value = None
            return mock_response
        
        document_retriever.session.get = mock_get
        
        documents = document_retriever.get_agency_documents('test-agency')
        
        assert len(documents) == 1
        assert documents[0].content is not None
        assert 'Test Document' in documents[0].content
        assert 'HTML content' in documents[0].content
    
    def test_get_agency_documents_error_handling(self, document_retriever, mock_database):
        """Test document retrieval handles errors gracefully."""
        # Mock JSON API response with mix of valid and invalid documents
        api_response = {
            'results': [
                {
                    'document_number': '2021-08964',
                    'title': 'Valid Document',
                    'publication_date': '2021-04-29',
                    'full_text_xml_url': 'http://example.com/valid.xml',
                    'cfr_references': []
                },
                {
                    'document_number': '2021-08965',
                    'title': 'Invalid Document',
                    'publication_date': '2021-04-30',
                    'full_text_xml_url': 'http://example.com/invalid.xml',
                    'cfr_references': []
                }
            ],
            'total_pages': 1
        }
        
        xml_content = """<?xml version="1.0"?>
        <document>
            <title>Valid Document</title>
            <body>This is valid content for the document with sufficient length to pass validation.</body>
        </document>"""
        
        def mock_get(url, **kwargs):
            mock_response = Mock()
            
            if 'documents.json' in url:
                mock_response.json.return_value = api_response
            elif 'valid.xml' in url:
                mock_response.content = xml_content.encode('utf-8')
                mock_response.raise_for_status.return_value = None
            else:
                # Invalid document fails both XML and HTML
                raise requests.exceptions.HTTPError("404 Not Found")
            
            return mock_response
        
        document_retriever.session.get = mock_get
        
        documents = document_retriever.get_agency_documents('test-agency')
        
        # Should only get the valid document
        assert len(documents) == 1
        assert documents[0].document_number == '2021-08964'
        assert documents[0].content is not None
    
    def test_get_agency_documents_no_documents_found(self, document_retriever, mock_database):
        """Test behavior when no documents are found for agency."""
        # Mock empty JSON API response
        api_response = {
            'results': [],
            'total_pages': 0
        }
        
        def mock_get(url, **kwargs):
            mock_response = Mock()
            mock_response.json.return_value = api_response
            mock_response.raise_for_status.return_value = None
            return mock_response
        
        document_retriever.session.get = mock_get
        
        documents = document_retriever.get_agency_documents('nonexistent-agency')
        
        assert len(documents) == 0
    
    @patch('time.sleep')  # Speed up tests by mocking sleep
    def test_get_agency_documents_rate_limiting(self, mock_sleep, document_retriever, mock_database):
        """Test that rate limiting is applied between requests."""
        # Mock JSON API response
        api_response = {
            'results': [
                {
                    'document_number': '2021-08964',
                    'title': 'Document 1',
                    'publication_date': '2021-04-29',
                    'full_text_xml_url': 'http://example.com/doc1.xml',
                    'cfr_references': []
                }
            ],
            'total_pages': 1
        }
        
        xml_content = """<?xml version="1.0"?>
        <document>
            <title>Test Document</title>
            <body>This is test content for the document with sufficient length to pass validation.</body>
        </document>"""
        
        def mock_get(url, **kwargs):
            mock_response = Mock()
            
            if 'documents.json' in url:
                mock_response.json.return_value = api_response
            else:
                mock_response.content = xml_content.encode('utf-8')
            
            mock_response.raise_for_status.return_value = None
            return mock_response
        
        document_retriever.session.get = mock_get
        
        documents = document_retriever.get_agency_documents('test-agency')
        
        assert len(documents) == 1
        # Should have called sleep for rate limiting
        assert mock_sleep.call_count >= 1