"""
Tests for statistics engine functionality.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from cfr_document_analyzer.statistics_engine import StatisticsEngine, AnalysisStatistics
from cfr_document_analyzer.database import Database


class TestStatisticsEngine:
    """Test statistics engine functionality."""
    
    @pytest.fixture
    def mock_database(self):
        """Mock database for testing."""
        return Mock(spec=Database)
    
    @pytest.fixture
    def statistics_engine(self, mock_database):
        """Statistics engine instance for testing."""
        return StatisticsEngine(mock_database)
    
    def test_get_overall_statistics(self, statistics_engine, mock_database):
        """Test overall statistics retrieval."""
        # Mock database responses
        mock_database.execute_query.side_effect = [
            [(100,)],  # Total documents
            [(5,)],    # Total sessions
            [('SR', 60), ('NSR', 25), ('NRAN', 15)],  # Category distribution
            [('agency-1', 40), ('agency-2', 35), ('agency-3', 25)],  # Agency distribution
            [(100, 95)],  # Success rate
            [(15.5,)],    # Average processing time
            [('2024-01-01', '2024-01-31')]  # Date range
        ]
        
        # Test statistics retrieval
        stats = statistics_engine.get_overall_statistics()
        
        # Verify statistics
        assert stats.total_documents == 100
        assert stats.total_sessions == 5
        assert stats.category_distribution['SR'] == 60
        assert stats.agency_distribution['agency-1'] == 40
        assert stats.success_rate == 95.0
        assert stats.average_processing_time == 15.5
    
    def test_analyze_patterns(self, statistics_engine, mock_database):
        """Test pattern analysis."""
        # Mock database responses
        mock_database.execute_query.side_effect = [
            # Statutory references
            [('["42 U.S.C. 1234", "15 U.S.C. 5678"]',),
             ('["42 U.S.C. 1234", "29 U.S.C. 9012"]',)],
            # Reform recommendations
            [('["Simplify reporting requirements", "Modernize data collection"]',),
             ('["Harmonize with other regulations", "Delete outdated provisions"]',)],
            # Category trends
            [('agency-1', 'SR', 30), ('agency-1', 'NSR', 10),
             ('agency-2', 'NRAN', 20), ('agency-2', 'SR', 15)]
        ]
        
        # Test pattern analysis
        patterns = statistics_engine.analyze_patterns()
        
        # Verify patterns
        assert len(patterns.common_statutory_references) > 0
        assert len(patterns.frequent_reform_recommendations) > 0
        assert 'agency-1' in patterns.category_trends
    
    def test_compare_agencies(self, statistics_engine, mock_database):
        """Test agency comparison."""
        # Mock database responses for each agency
        mock_database.execute_query.side_effect = [
            # Agency 1 stats
            [(50, 12.5, 95.0, 'SR', 30), (50, 12.5, 95.0, 'NSR', 20)],
            # Agency 2 stats
            [(30, 18.2, 90.0, 'SR', 20), (30, 18.2, 90.0, 'NRAN', 10)],
            # Strategy comparisons
            [('DOGE Criteria', 80, 15.0, 92.5)],
            # Temporal trends
            [('2024-01-01', 25), ('2024-01-02', 30), ('2024-01-03', 20)]
        ]
        
        # Test agency comparison
        comparison = statistics_engine.compare_agencies(['agency-1', 'agency-2'])
        
        # Verify comparison results
        assert 'agency-1' in comparison.agency_comparisons
        assert 'agency-2' in comparison.agency_comparisons
        assert 'DOGE Criteria' in comparison.strategy_comparisons
    
    def test_generate_cost_analysis(self, statistics_engine, mock_database):
        """Test cost analysis generation."""
        # Mock database responses
        mock_database.execute_query.side_effect = [
            [(50000, 625, 80)],  # Token usage
            [(1200.0, 15.0, 45.0, 5.0)]  # Processing time
        ]
        
        # Test cost analysis
        cost_analysis = statistics_engine.generate_cost_analysis()
        
        # Verify cost analysis
        assert cost_analysis['token_usage']['total_tokens'] == 50000
        assert cost_analysis['processing_time']['total_seconds'] == 1200.0
        assert 'cost_estimates' in cost_analysis
    
    def test_get_session_performance_metrics(self, statistics_engine, mock_database):
        """Test session performance metrics."""
        # Mock database responses
        mock_database.execute_query.side_effect = [
            # Session completion metrics
            [('completed', 8, 25.5), ('running', 2, None), ('failed', 1, None)],
            # Efficiency metrics
            [('session_1', 10, 10, 100.0, 30.0),
             ('session_2', 8, 10, 80.0, 25.0)]
        ]
        
        # Test performance metrics
        metrics = statistics_engine.get_session_performance_metrics()
        
        # Verify metrics
        assert metrics['session_status_distribution']['completed']['count'] == 8
        assert len(metrics['efficiency_metrics']) == 2
        assert metrics['total_sessions'] == 2
    
    def test_generate_comprehensive_report_dict(self, statistics_engine, mock_database):
        """Test comprehensive report generation in dict format."""
        # Mock all the database calls that would be made
        mock_database.execute_query.side_effect = [
            # Overall statistics calls
            [(100,)], [(5,)], [('SR', 60)], [('agency-1', 40)], [(100, 95)], [(15.5,)], [('2024-01-01', '2024-01-31')],
            # Pattern analysis calls
            [('["42 U.S.C. 1234"]',)], [('["Simplify requirements"]',)], [('agency-1', 'SR', 30)],
            # Cost analysis calls
            [(50000, 625, 80)], [(1200.0, 15.0, 45.0, 5.0)],
            # Performance metrics calls
            [('completed', 8, 25.5)], [('session_1', 10, 10, 100.0, 30.0)],
            # Comparative analysis calls (for top agencies)
            [(50, 12.5, 95.0, 'SR', 30)], [('DOGE Criteria', 80, 15.0, 92.5)], [('2024-01-01', 25)]
        ]
        
        # Test comprehensive report generation
        report = statistics_engine.generate_comprehensive_report('dict')
        
        # Verify report structure
        assert isinstance(report, dict)
        assert 'generated_at' in report
        assert 'overall_statistics' in report
        assert 'pattern_analysis' in report
    
    def test_generate_comprehensive_report_markdown(self, statistics_engine, mock_database):
        """Test comprehensive report generation in markdown format."""
        # Mock database calls (simplified for markdown test)
        mock_database.execute_query.side_effect = [
            # Overall statistics
            [(100,)], [(5,)], [('SR', 60)], [('agency-1', 40)], [(100, 95)], [(15.5,)], [('2024-01-01', '2024-01-31')],
            # Pattern analysis
            [('["42 U.S.C. 1234"]',)], [('["Simplify requirements"]',)], [('agency-1', 'SR', 30)],
            # Cost analysis
            [(50000, 625, 80)], [(1200.0, 15.0, 45.0, 5.0)],
            # Performance metrics
            [('completed', 8, 25.5)], [('session_1', 10, 10, 100.0, 30.0)],
            # Comparative analysis
            [(50, 12.5, 95.0, 'SR', 30)], [('DOGE Criteria', 80, 15.0, 92.5)], [('2024-01-01', 25)]
        ]
        
        # Test markdown report generation
        report = statistics_engine.generate_comprehensive_report('markdown')
        
        # Verify markdown format
        assert isinstance(report, str)
        assert '# CFR Document Analysis Report' in report
        assert '## Overall Statistics' in report
    
    def test_empty_data_handling(self, statistics_engine, mock_database):
        """Test handling of empty data sets."""
        # Mock empty database responses
        mock_database.execute_query.return_value = []
        
        # Test statistics with empty data
        stats = statistics_engine.get_overall_statistics()
        
        # Should handle empty data gracefully
        assert stats.total_documents == 0
        assert stats.total_sessions == 0
        assert stats.success_rate == 0.0
    
    def test_date_filtering(self, statistics_engine, mock_database):
        """Test date filtering in statistics queries."""
        # Mock database response
        mock_database.execute_query.return_value = [(50,)]
        
        # Test with date filters
        stats = statistics_engine.get_overall_statistics(
            date_from='2024-01-01',
            date_to='2024-01-31'
        )
        
        # Verify database was called with date parameters
        mock_database.execute_query.assert_called()
        
        # Check that date parameters were included in the call
        call_args = mock_database.execute_query.call_args
        assert '2024-01-01' in call_args[0][1] or '2024-01-01' in str(call_args)
    
    def test_error_handling(self, statistics_engine, mock_database):
        """Test error handling in statistics generation."""
        # Mock database error
        mock_database.execute_query.side_effect = Exception("Database error")
        
        # Test should handle errors gracefully
        stats = statistics_engine.get_overall_statistics()
        
        # Should return default values on error
        assert stats.total_documents == 0
        assert stats.total_sessions == 0
    
    @pytest.mark.integration
    def test_statistics_integration(self):
        """Integration test for statistics workflow."""
        # This would test the full statistics workflow
        # with a real database and sample data
        pass