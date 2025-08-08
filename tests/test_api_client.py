"""Tests for the API client module."""

import pytest
import responses
import time
from unittest.mock import patch, MagicMock
from cfr_agency_counter.api_client import FederalRegisterClient, FederalRegisterAPIError


class TestFederalRegisterClient:
    """Test cases for the FederalRegisterClient class."""
    
    def test_client_initialization(self):
        """Test client initialization with default and custom parameters."""
        # Test with defaults
        client = FederalRegisterClient()
        assert client.base_url == 'https://www.federalregister.gov/api/v1'
        assert client.rate_limit == 1.0
        
        # Test with custom parameters
        client = FederalRegisterClient(
            base_url='https://test.example.com/api',
            rate_limit=2.0
        )
        assert client.base_url == 'https://test.example.com/api'
        assert client.rate_limit == 2.0
    
    @patch('time.sleep')
    def test_rate_limiting(self, mock_sleep):
        """Test that rate limiting is enforced."""
        client = FederalRegisterClient(rate_limit=2.0)  # 2 requests per second
        
        # First request should not sleep
        client._enforce_rate_limit()
        mock_sleep.assert_not_called()
        
        # Second request immediately after should sleep
        client._enforce_rate_limit()
        mock_sleep.assert_called_once()
        
        # Check that sleep time is approximately correct (0.5s for 2 req/s)
        sleep_time = mock_sleep.call_args[0][0]
        assert 0.4 < sleep_time < 0.6
    
    @responses.activate
    def test_successful_api_request(self):
        """Test successful API request."""
        responses.add(
            responses.GET,
            'https://www.federalregister.gov/api/v1/test',
            json={'result': 'success'},
            status=200
        )
        
        client = FederalRegisterClient()
        result = client._make_request('/test')
        
        assert result == {'result': 'success'}
    
    @responses.activate
    def test_api_request_with_params(self):
        """Test API request with query parameters."""
        responses.add(
            responses.GET,
            'https://www.federalregister.gov/api/v1/test',
            json={'result': 'success'},
            status=200
        )
        
        client = FederalRegisterClient()
        result = client._make_request('/test', {'param1': 'value1', 'param2': 'value2'})
        
        assert result == {'result': 'success'}
        assert len(responses.calls) == 1
        assert 'param1=value1' in responses.calls[0].request.url
        assert 'param2=value2' in responses.calls[0].request.url
    
    @responses.activate
    def test_http_error_handling(self):
        """Test handling of HTTP errors."""
        responses.add(
            responses.GET,
            'https://www.federalregister.gov/api/v1/test',
            status=404
        )
        
        client = FederalRegisterClient()
        
        with pytest.raises(FederalRegisterAPIError, match="HTTP error: 404"):
            client._make_request('/test')
    
    @responses.activate
    def test_server_error_retry(self):
        """Test retry logic for server errors."""
        # First two requests return 500, third succeeds
        responses.add(
            responses.GET,
            'https://www.federalregister.gov/api/v1/test',
            status=500
        )
        responses.add(
            responses.GET,
            'https://www.federalregister.gov/api/v1/test',
            status=500
        )
        responses.add(
            responses.GET,
            'https://www.federalregister.gov/api/v1/test',
            json={'result': 'success'},
            status=200
        )
        
        client = FederalRegisterClient()
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = client._make_request('/test')
        
        assert result == {'result': 'success'}
        assert len(responses.calls) == 3
    
    @responses.activate
    def test_rate_limit_handling(self):
        """Test handling of rate limit responses from server."""
        responses.add(
            responses.GET,
            'https://www.federalregister.gov/api/v1/test',
            status=429,
            headers={'Retry-After': '1'}
        )
        responses.add(
            responses.GET,
            'https://www.federalregister.gov/api/v1/test',
            json={'result': 'success'},
            status=200
        )
        
        client = FederalRegisterClient()
        
        with patch('time.sleep') as mock_sleep:
            result = client._make_request('/test')
        
        assert result == {'result': 'success'}
        mock_sleep.assert_called_with(1)  # Should sleep for Retry-After duration
    
    @responses.activate
    def test_get_agency_document_counts(self):
        """Test getting agency document counts."""
        mock_response = {
            'facets': {
                'agency': {
                    'agriculture-department': 1234,
                    'treasury-department': 567,
                    'defense-department': 890
                }
            }
        }
        
        responses.add(
            responses.GET,
            'https://www.federalregister.gov/api/v1/documents/facets/agency',
            json=mock_response,
            status=200
        )
        
        client = FederalRegisterClient()
        counts = client.get_agency_document_counts()
        
        expected = {
            'agriculture-department': 1234,
            'treasury-department': 567,
            'defense-department': 890
        }
        assert counts == expected
    
    @responses.activate
    def test_get_agency_document_counts_empty_response(self):
        """Test handling of empty facets response."""
        responses.add(
            responses.GET,
            'https://www.federalregister.gov/api/v1/documents/facets/agency',
            json={'facets': {}},
            status=200
        )
        
        client = FederalRegisterClient()
        counts = client.get_agency_document_counts()
        
        assert counts == {}
    
    @responses.activate
    def test_get_agency_details(self):
        """Test getting agency details."""
        mock_response = {
            'name': 'Department of Agriculture',
            'slug': 'agriculture-department',
            'description': 'Test description'
        }
        
        responses.add(
            responses.GET,
            'https://www.federalregister.gov/api/v1/agencies/agriculture-department',
            json=mock_response,
            status=200
        )
        
        client = FederalRegisterClient()
        details = client.get_agency_details('agriculture-department')
        
        assert details == mock_response
    
    @responses.activate
    def test_get_agency_details_not_found(self):
        """Test handling of agency not found."""
        responses.add(
            responses.GET,
            'https://www.federalregister.gov/api/v1/agencies/nonexistent-agency',
            status=404
        )
        
        client = FederalRegisterClient()
        details = client.get_agency_details('nonexistent-agency')
        
        assert details is None
    
    @responses.activate
    def test_get_all_agencies(self):
        """Test getting all agencies."""
        mock_response = {
            'agencies': [
                {'name': 'Agency 1', 'slug': 'agency-1'},
                {'name': 'Agency 2', 'slug': 'agency-2'}
            ]
        }
        
        responses.add(
            responses.GET,
            'https://www.federalregister.gov/api/v1/agencies',
            json=mock_response,
            status=200
        )
        
        client = FederalRegisterClient()
        agencies = client.get_all_agencies()
        
        assert len(agencies) == 2
        assert agencies[0]['name'] == 'Agency 1'
        assert agencies[1]['name'] == 'Agency 2'
    
    @responses.activate
    def test_search_documents(self):
        """Test searching documents for an agency."""
        mock_response = {
            'count': 100,
            'results': [
                {'title': 'Document 1', 'document_number': '2023-12345'},
                {'title': 'Document 2', 'document_number': '2023-12346'}
            ]
        }
        
        responses.add(
            responses.GET,
            'https://www.federalregister.gov/api/v1/documents.json',
            json=mock_response,
            status=200
        )
        
        client = FederalRegisterClient()
        results = client.search_documents('agriculture-department')
        
        assert results['count'] == 100
        assert len(results['results']) == 2
        
        # Check that the request included the agency parameter
        request_url = responses.calls[0].request.url
        assert 'conditions%5Bagencies%5D%5B%5D=agriculture-department' in request_url
    
    @responses.activate
    def test_get_document_count_for_agency(self):
        """Test getting document count for a specific agency."""
        mock_response = {
            'count': 1234,
            'results': [
                {'document_number': '2023-12345'}
            ]
        }
        
        responses.add(
            responses.GET,
            'https://www.federalregister.gov/api/v1/documents.json',
            json=mock_response,
            status=200
        )
        
        client = FederalRegisterClient()
        count = client.get_document_count_for_agency('agriculture-department')
        
        assert count == 1234
    
    def test_client_close(self):
        """Test closing the client session."""
        client = FederalRegisterClient()
        mock_session = MagicMock()
        client.session = mock_session
        
        client.close()
        
        mock_session.close.assert_called_once()
    
    @responses.activate
    def test_invalid_json_response(self):
        """Test handling of invalid JSON response."""
        responses.add(
            responses.GET,
            'https://www.federalregister.gov/api/v1/test',
            body='invalid json',
            status=200
        )
        
        client = FederalRegisterClient()
        
        with pytest.raises(FederalRegisterAPIError, match="Invalid JSON response"):
            client._make_request('/test')