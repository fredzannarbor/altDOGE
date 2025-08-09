"""
Tests for URLBuilder class.
"""

import pytest
from cfr_document_analyzer.url_builder import URLBuilder


class TestURLBuilder:
    """Test cases for URLBuilder class."""
    
    def test_validate_document_number_standard_format(self):
        """Test validation of standard document number format."""
        assert URLBuilder.validate_document_number("2021-08964")
        assert URLBuilder.validate_document_number("2020-24826")
        assert URLBuilder.validate_document_number("2019-24802")
    
    def test_validate_document_number_alternative_format(self):
        """Test validation of alternative document number format."""
        assert URLBuilder.validate_document_number("2021-ABC-123")
        assert URLBuilder.validate_document_number("2020-DEF-456")
    
    def test_validate_document_number_executive_format(self):
        """Test validation of executive document number format."""
        assert URLBuilder.validate_document_number("E9-30894")
        assert URLBuilder.validate_document_number("E9-23154")
    
    def test_validate_document_number_date_based_format(self):
        """Test validation of date-based document number format."""
        assert URLBuilder.validate_document_number("2021/04/29/document-slug")
        assert URLBuilder.validate_document_number("2020/11/09/another-document")
    
    def test_validate_document_number_invalid_formats(self):
        """Test validation rejects invalid document number formats."""
        assert not URLBuilder.validate_document_number("")
        assert not URLBuilder.validate_document_number("invalid")
        assert not URLBuilder.validate_document_number("2021")
        assert not URLBuilder.validate_document_number("2021-")
        assert not URLBuilder.validate_document_number("abc-123")
    
    def test_build_xml_url_with_provided_url(self):
        """Test XML URL building when URL is already provided."""
        document_data = {
            'document_number': '2021-08964',
            'full_text_xml_url': 'https://www.federalregister.gov/documents/full_text/xml/2021/04/29/2021-08964/test.xml'
        }
        
        url = URLBuilder.build_xml_url(document_data)
        assert url == 'https://www.federalregister.gov/documents/full_text/xml/2021/04/29/2021-08964/test.xml'
    
    def test_build_xml_url_with_publication_date(self):
        """Test XML URL building with publication date."""
        document_data = {
            'document_number': '2021-08964',
            'publication_date': '2021-04-29'
        }
        
        url = URLBuilder.build_xml_url(document_data)
        expected = 'https://www.federalregister.gov/documents/full_text/xml/2021/04/29/2021-08964.xml'
        assert url == expected
    
    def test_build_xml_url_without_publication_date(self):
        """Test XML URL building without publication date."""
        document_data = {
            'document_number': '2021-08964'
        }
        
        url = URLBuilder.build_xml_url(document_data)
        expected = 'https://www.federalregister.gov/documents/full_text/xml/2021-08964.xml'
        assert url == expected
    
    def test_build_xml_url_date_based_format(self):
        """Test XML URL building with date-based document number."""
        document_data = {
            'document_number': '2021/04/29/document-slug'
        }
        
        url = URLBuilder.build_xml_url(document_data)
        expected = 'https://www.federalregister.gov/documents/full_text/xml/2021/04/29/document-slug.xml'
        assert url == expected
    
    def test_build_xml_url_invalid_document_number(self):
        """Test XML URL building with invalid document number."""
        document_data = {
            'document_number': 'invalid'
        }
        
        url = URLBuilder.build_xml_url(document_data)
        assert url is None
    
    def test_build_xml_url_missing_document_number(self):
        """Test XML URL building with missing document number."""
        document_data = {}
        
        url = URLBuilder.build_xml_url(document_data)
        assert url is None
    
    def test_build_html_url_with_publication_date(self):
        """Test HTML URL building with publication date."""
        document_data = {
            'document_number': '2021-08964',
            'publication_date': '2021-04-29'
        }
        
        url = URLBuilder.build_html_url(document_data)
        expected = 'https://www.federalregister.gov/documents/2021/04/29/2021-08964'
        assert url == expected
    
    def test_build_html_url_without_publication_date(self):
        """Test HTML URL building without publication date."""
        document_data = {
            'document_number': '2021-08964'
        }
        
        url = URLBuilder.build_html_url(document_data)
        expected = 'https://www.federalregister.gov/documents/2021-08964'
        assert url == expected
    
    def test_build_html_url_date_based_format(self):
        """Test HTML URL building with date-based document number."""
        document_data = {
            'document_number': '2021/04/29/document-slug'
        }
        
        url = URLBuilder.build_html_url(document_data)
        expected = 'https://www.federalregister.gov/documents/2021/04/29/document-slug'
        assert url == expected
    
    def test_extract_document_number_from_url_standard(self):
        """Test extracting document number from standard URL."""
        url = 'https://www.federalregister.gov/documents/2021-08964'
        doc_number = URLBuilder.extract_document_number_from_url(url)
        assert doc_number == '2021-08964'
    
    def test_extract_document_number_from_url_date_based(self):
        """Test extracting document number from date-based URL."""
        url = 'https://www.federalregister.gov/documents/2021/04/29/document-slug'
        doc_number = URLBuilder.extract_document_number_from_url(url)
        assert doc_number == '2021/04/29/document-slug'
    
    def test_extract_document_number_from_url_executive(self):
        """Test extracting executive document number from URL."""
        url = 'https://www.federalregister.gov/documents/E9-30894'
        doc_number = URLBuilder.extract_document_number_from_url(url)
        assert doc_number == 'E9-30894'
    
    def test_extract_document_number_from_url_invalid(self):
        """Test extracting document number from invalid URL."""
        url = 'https://www.example.com/invalid'
        doc_number = URLBuilder.extract_document_number_from_url(url)
        assert doc_number is None