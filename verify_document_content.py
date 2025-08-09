#!/usr/bin/env python3
"""
Diagnostic script to verify document content retrieval.

This script will check exactly how many documents have retrievable content
vs how many are just metadata without content.
"""

import sys
import logging
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from cfr_document_analyzer.database import Database
from cfr_document_analyzer.document_retriever import DocumentRetriever

# Set up logging to see detailed information
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verify_document_content(agency_slug: str, limit: int = 50):
    """
    Verify document content retrieval for an agency.
    
    Args:
        agency_slug: Agency identifier
        limit: Maximum number of documents to check
    """
    print(f"🔍 Verifying document content for: {agency_slug}")
    print(f"📊 Checking up to {limit} documents")
    print("=" * 60)
    
    try:
        # Initialize components
        db = Database(':memory:')
        retriever = DocumentRetriever(db, use_cache=False)
        
        # First, let's see what the JSON API returns (metadata only)
        print("📋 Step 1: Fetching document metadata from JSON API...")
        
        # We'll manually call the JSON API method to see raw metadata
        json_docs = retriever._fetch_documents_from_json_api(agency_slug, limit)
        
        print(f"✅ Found {len(json_docs)} documents in JSON API")
        
        if not json_docs:
            print("❌ No documents found in JSON API")
            return
        
        # Show sample of metadata
        print(f"\n📄 Sample document metadata:")
        for i, doc in enumerate(json_docs[:3]):
            print(f"  {i+1}. {doc.get('document_number', 'Unknown')}")
            print(f"     Title: {doc.get('title', 'No title')[:80]}...")
            print(f"     XML URL: {doc.get('full_text_xml_url', 'No XML URL')}")
            print()
        
        # Now let's check content retrieval
        print("🔄 Step 2: Testing content retrieval for each document...")
        
        content_stats = {
            'total_checked': 0,
            'has_content': 0,
            'no_content': 0,
            'xml_success': 0,
            'html_success': 0,
            'both_failed': 0
        }
        
        failed_documents = []
        
        for i, doc_data in enumerate(json_docs):
            if i >= limit:
                break
                
            doc_number = doc_data.get('document_number', f'doc_{i}')
            content_stats['total_checked'] += 1
            
            print(f"  📄 {i+1}/{min(len(json_docs), limit)}: {doc_number}")
            
            # Try to extract content using our ContentExtractor
            content, source = retriever.content_extractor.extract_content(doc_data)
            
            if content:
                content_stats['has_content'] += 1
                if source == 'xml':
                    content_stats['xml_success'] += 1
                elif source == 'html':
                    content_stats['html_success'] += 1
                
                print(f"    ✅ Content retrieved from {source}: {len(content)} chars")
            else:
                content_stats['no_content'] += 1
                content_stats['both_failed'] += 1
                failed_documents.append({
                    'document_number': doc_number,
                    'title': doc_data.get('title', 'No title')[:50],
                    'xml_url': doc_data.get('full_text_xml_url', 'No URL')
                })
                print(f"    ❌ No content retrieved")
        
        # Summary statistics
        print("\n" + "=" * 60)
        print("📊 CONTENT RETRIEVAL SUMMARY")
        print("=" * 60)
        
        print(f"Total documents checked: {content_stats['total_checked']}")
        print(f"Documents with content: {content_stats['has_content']}")
        print(f"Documents without content: {content_stats['no_content']}")
        
        if content_stats['total_checked'] > 0:
            success_rate = (content_stats['has_content'] / content_stats['total_checked']) * 100
            print(f"Content retrieval success rate: {success_rate:.1f}%")
        
        print(f"\nContent source breakdown:")
        print(f"  XML successful: {content_stats['xml_success']}")
        print(f"  HTML successful: {content_stats['html_success']}")
        print(f"  Both failed: {content_stats['both_failed']}")
        
        # Show failed documents
        if failed_documents:
            print(f"\n❌ FAILED DOCUMENTS ({len(failed_documents)}):")
            print("-" * 60)
            for i, doc in enumerate(failed_documents[:10]):  # Show first 10
                print(f"{i+1}. {doc['document_number']}")
                print(f"   Title: {doc['title']}...")
                print(f"   XML URL: {doc['xml_url']}")
                print()
            
            if len(failed_documents) > 10:
                print(f"   ... and {len(failed_documents) - 10} more")
        
        # Conclusion
        print("\n🎯 CONCLUSION:")
        if content_stats['has_content'] == content_stats['total_checked']:
            print("✅ All documents have retrievable content!")
        elif content_stats['has_content'] > 0:
            print(f"⚠️  Only {content_stats['has_content']} out of {content_stats['total_checked']} documents have retrievable content.")
            print("   This explains why LLM analysis was limited to those documents.")
        else:
            print("❌ No documents have retrievable content - there may be a systematic issue.")
        
        retriever.close()
        
    except Exception as e:
        logger.error(f"Error during verification: {e}")
        print(f"❌ Error: {e}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify document content retrieval")
    parser.add_argument('--agency', default='engraving-and-printing-bureau', 
                       help='Agency slug to check')
    parser.add_argument('--limit', type=int, default=50,
                       help='Maximum documents to check')
    
    args = parser.parse_args()
    
    verify_document_content(args.agency, args.limit)


if __name__ == '__main__':
    main()