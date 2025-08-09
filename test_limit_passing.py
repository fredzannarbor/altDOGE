#!/usr/bin/env python3
"""
Test script to verify that document limits are being passed correctly.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from cfr_document_analyzer.database import Database
from cfr_document_analyzer.analysis_engine import AnalysisEngine

def test_limit_passing():
    """Test that document limits are passed correctly through the system."""
    
    print("🧪 Testing document limit passing...")
    
    # Test with different limits
    test_limits = [5, 15, 25]
    
    for limit in test_limits:
        print(f"\n📊 Testing with limit: {limit}")
        
        try:
            # Initialize components
            db = Database(':memory:')
            engine = AnalysisEngine(db)
            
            # Mock the LLM client to avoid actual API calls
            def mock_analyze(*args, **kwargs):
                return "Mock analysis", True, None
            
            engine.llm_client.analyze_document = mock_analyze
            engine.llm_client.analyze_document_with_doge_prompts = lambda content, doc_id: type('MockDOGE', (), {
                'category': 'SR',
                'statutory_references': ['Mock statute'],
                'reform_recommendations': ['Mock recommendation'],
                'justification': 'Mock justification'
            })()
            
            # Get documents directly from retriever to see how many are available
            documents = engine.document_retriever.get_agency_documents('engraving-and-printing-bureau', limit)
            
            print(f"  📄 Documents retrieved: {len(documents)}")
            
            # Check if the limit was respected
            if len(documents) <= limit:
                print(f"  ✅ Limit respected: {len(documents)} <= {limit}")
            else:
                print(f"  ❌ Limit exceeded: {len(documents)} > {limit}")
            
            engine.close()
            
        except Exception as e:
            print(f"  ❌ Error: {e}")

def main():
    test_limit_passing()

if __name__ == '__main__':
    main()