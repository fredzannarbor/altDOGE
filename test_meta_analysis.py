#!/usr/bin/env python3
"""
Test script for meta-analysis functionality.
"""

import logging
from cfr_document_analyzer.database import Database
from cfr_document_analyzer.analysis_engine import AnalysisEngine

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_meta_analysis():
    """Test meta-analysis functionality with existing session data."""
    try:
        # Initialize components
        database = Database("cfr_document_analyzer.db")
        engine = AnalysisEngine(database)
        
        # Find a recent session with results
        query = """
        SELECT DISTINCT s.session_id, s.agency_slugs, COUNT(a.id) as analysis_count
        FROM sessions s
        JOIN documents d ON JSON_EXTRACT(s.agency_slugs, '$[0]') = d.agency_slug
        JOIN analyses a ON d.id = a.document_id
        WHERE s.status = 'completed'
        GROUP BY s.session_id
        HAVING analysis_count > 0
        ORDER BY s.created_at DESC
        LIMIT 1
        """
        
        results = database.execute_query(query)
        
        if not results:
            logger.error("No completed sessions with analysis results found")
            return False
        
        session_data = dict(results[0])
        session_id = session_data['session_id']
        analysis_count = session_data['analysis_count']
        
        logger.info(f"Testing meta-analysis on session {session_id} with {analysis_count} analyses")
        
        # Perform meta-analysis
        meta_analysis = engine.perform_meta_analysis(session_id)
        
        if meta_analysis and meta_analysis.success:
            logger.info(f"Meta-analysis completed successfully in {meta_analysis.processing_time:.2f}s")
            
            # Display results
            print(f"\n=== META-ANALYSIS RESULTS ===")
            print(f"Session ID: {session_id}")
            
            if meta_analysis.executive_summary:
                print(f"\nExecutive Summary:")
                print(f"  {meta_analysis.executive_summary}")
            
            if meta_analysis.key_patterns:
                print(f"\nKey Patterns ({len(meta_analysis.key_patterns)}):")
                for i, pattern in enumerate(meta_analysis.key_patterns, 1):
                    print(f"  {i}. {pattern}")
            
            if meta_analysis.priority_actions:
                print(f"\nPriority Actions ({len(meta_analysis.priority_actions)}):")
                for i, action in enumerate(meta_analysis.priority_actions, 1):
                    print(f"  {i}. {action}")
            
            if meta_analysis.quick_wins:
                print(f"\nQuick Wins ({len(meta_analysis.quick_wins)}):")
                for i, win in enumerate(meta_analysis.quick_wins, 1):
                    print(f"  {i}. {win}")
            
            return True
        else:
            error_msg = meta_analysis.error_message if meta_analysis else "Unknown error"
            logger.error(f"Meta-analysis failed: {error_msg}")
            return False
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False
    finally:
        engine.close()

if __name__ == "__main__":
    success = test_meta_analysis()
    exit(0 if success else 1)