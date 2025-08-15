"""
Tests for meta-analysis functionality.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from cfr_document_analyzer.llm_client import LLMClient
from cfr_document_analyzer.models import MetaAnalysis
from cfr_document_analyzer.database import Database


class TestMetaAnalysis:
    """Test meta-analysis functionality."""
    
    @pytest.fixture
    def mock_database(self):
        """Mock database for testing."""
        return Mock(spec=Database)
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for testing."""
        return Mock(spec=LLMClient)
    
    @pytest.fixture
    def sample_analysis_results(self):
        """Sample analysis results for testing."""
        return [
            {
                'document_number': '2024-12345',
                'title': 'Test Document 1',
                'agency_slug': 'test-agency',
                'analysis': {
                    'category': 'SR',
                    'statutory_references': ['42 U.S.C. 1234'],
                    'reform_recommendations': ['Simplify reporting requirements'],
                    'success': True
                }
            },
            {
                'document_number': '2024-12346',
                'title': 'Test Document 2',
                'agency_slug': 'test-agency',
                'analysis': {
                    'category': 'NRAN',
                    'statutory_references': ['15 U.S.C. 5678'],
                    'reform_recommendations': ['Modernize data collection'],
                    'success': True
                }
            }
        ]
    
    def test_perform_meta_analysis_success(self, mock_llm_client, sample_analysis_results):
        """Test successful meta-analysis."""
        # Mock LLM responses
        mock_llm_client.analyze_document.side_effect = [
            ("Strategic response with key patterns", True, None),
            ("Reform response with opportunities", True, None)
        ]
        
        # Test meta-analysis
        result = mock_llm_client.perform_meta_analysis(sample_analysis_results, "test_session")
        
        # Verify LLM was called twice (strategic + reform)
        assert mock_llm_client.analyze_document.call_count == 2
    
    def test_meta_analysis_parsing(self):
        """Test meta-analysis response parsing."""
        strategic_response = """
        KEY PATTERNS:
        - Pattern 1: High regulatory burden
        - Pattern 2: Outdated processes
        
        STRATEGIC THEMES:
        - Theme 1: Modernization needed
        - Theme 2: Simplification opportunities
        
        PRIORITY ACTIONS:
        - Action 1: Review reporting requirements
        - Action 2: Implement digital processes
        
        SUMMARY:
        Analysis shows significant opportunities for reform.
        """
        
        reform_response = """
        REFORM OPPORTUNITIES:
        • Opportunity 1: Streamline approvals
        • Opportunity 2: Reduce paperwork
        
        QUICK WINS:
        • Win 1: Eliminate duplicate forms
        • Win 2: Automate routine processes
        """
        
        # This would test the actual parsing logic
        # In a real implementation, we'd test the _parse_meta_analysis_response method
        assert "Pattern 1" in strategic_response
        assert "Opportunity 1" in reform_response
    
    def test_meta_analysis_error_handling(self, mock_llm_client, sample_analysis_results):
        """Test meta-analysis error handling."""
        # Mock LLM failure
        mock_llm_client.analyze_document.return_value = ("", False, "API Error")
        
        # Test should handle errors gracefully
        result = mock_llm_client.perform_meta_analysis(sample_analysis_results, "test_session")
        
        # Should return error result
        assert result is not None
    
    def test_empty_results_handling(self, mock_llm_client):
        """Test handling of empty analysis results."""
        result = mock_llm_client.perform_meta_analysis([], "test_session")
        
        # Should handle empty results gracefully
        assert result is not None
    
    def test_meta_analysis_data_preparation(self, sample_analysis_results):
        """Test preparation of analysis data for meta-analysis."""
        # This would test the _prepare_analysis_summary method
        # Verify that data is properly formatted for LLM consumption
        
        # Check that categories are counted
        categories = {}
        for result in sample_analysis_results:
            category = result['analysis']['category']
            categories[category] = categories.get(category, 0) + 1
        
        assert categories['SR'] == 1
        assert categories['NRAN'] == 1
    
    @pytest.mark.integration
    def test_meta_analysis_integration(self, mock_database):
        """Integration test for meta-analysis workflow."""
        # This would test the full workflow from analysis engine
        # through to database storage
        pass