#!/usr/bin/env python3
"""
Command-line interface for CFR Document Analyzer.

Provides CLI access to document analysis functionality.
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import List, Optional

from .config import Config
from .database import Database
from .analysis_engine import AnalysisEngine
from .export_manager import ExportManager
from .error_handler import ErrorHandler, AnalysisError
from .models import SessionStatus
from .utils import extract_agency_name


def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="CFR Document Analyzer - Analyze CFR documents using LLM-based analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s analyze --agency national-credit-union-administration --limit 5
  %(prog)s analyze --agency farm-credit-administration --strategy "DOGE Criteria"
  %(prog)s list-agencies
  %(prog)s results --session session_20250807_123456
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze documents for an agency')
    analyze_parser.add_argument(
        '--agency', '-a',
        required=True,
        help='Agency slug to analyze (e.g., national-credit-union-administration)'
    )
    analyze_parser.add_argument(
        '--strategy', '-s',
        default=Config.DEFAULT_PROMPT_STRATEGY,
        help=f'Analysis strategy to use (default: {Config.DEFAULT_PROMPT_STRATEGY})'
    )
    analyze_parser.add_argument(
        '--limit', '-l',
        type=int,
        default=Config.DEFAULT_DOCUMENT_LIMIT,
        help=f'Maximum number of documents to analyze (default: {Config.DEFAULT_DOCUMENT_LIMIT})'
    )
    analyze_parser.add_argument(
        '--output', '-o',
        help='Output file for results (default: auto-generated)'
    )
    
    # Results command
    results_parser = subparsers.add_parser('results', help='View analysis results')
    results_parser.add_argument(
        '--session', '-s',
        help='Session ID to view results for'
    )
    results_parser.add_argument(
        '--agency', '-a',
        help='Show results for specific agency'
    )
    results_parser.add_argument(
        '--format', '-f',
        choices=['table', 'json', 'csv'],
        default='table',
        help='Output format (default: table)'
    )
    
    # List agencies command
    list_parser = subparsers.add_parser('list-agencies', help='List available test agencies')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status and statistics')
    
    # Global options
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress output except errors'
    )
    parser.add_argument(
        '--database', '-d',
        default=Config.DATABASE_PATH,
        help=f'Database path (default: {Config.DATABASE_PATH})'
    )
    
    return parser


def cmd_analyze(args: argparse.Namespace) -> int:
    """Handle analyze command."""
    logger = logging.getLogger(__name__)
    
    try:
        # Validate inputs
        ErrorHandler.validate_agency_slug(args.agency)
        ErrorHandler.validate_document_limit(args.limit)
        
        # Initialize components
        db = Database(args.database)
        engine = AnalysisEngine(db)
        
        # Validate prompt strategy
        available_strategies = engine.prompt_manager.get_available_packages()
        ErrorHandler.validate_prompt_strategy(args.strategy, available_strategies)
        
        logger.info(f"Starting analysis for agency: {args.agency}")
        logger.info(f"Strategy: {args.strategy}")
        logger.info(f"Document limit: {args.limit}")
        
        # Run analysis
        session = engine.analyze_agency_documents(
            agency_slug=args.agency,
            prompt_strategy=args.strategy,
            document_limit=args.limit
        )
        
        # Print results
        print(f"\nAnalysis completed!")
        print(f"Session ID: {session.session_id}")
        print(f"Status: {session.status.value}")
        print(f"Documents processed: {session.documents_processed}/{session.total_documents}")
        
        if session.status == SessionStatus.COMPLETED and session.documents_processed > 0:
            # Get detailed results
            results = engine.get_analysis_results(session.session_id)
            
            print(f"\nResults Summary:")
            print(f"Total documents analyzed: {len(results)}")
            
            # Count by category
            categories = {}
            for result in results:
                category = result['analysis']['category'] or 'UNKNOWN'
                categories[category] = categories.get(category, 0) + 1
            
            for category, count in categories.items():
                print(f"  {category}: {count}")
            
            # Show usage stats
            stats = engine.get_usage_statistics()
            print(f"\nLLM Usage:")
            print(f"  Total calls: {stats['total_calls']}")
            print(f"  Success rate: {stats['success_rate']:.1f}%")
            print(f"  Total time: {stats['total_time']:.1f}s")
            
            # Save results if requested
            if args.output:
                save_results_to_file(results, args.output, session.session_id)
                print(f"\nResults saved to: {args.output}")
            else:
                # Auto-generate exports for agency presentation
                export_manager = ExportManager()
                exported_files = export_manager.export_session_results(
                    results, session.session_id, ['json', 'csv', 'html']
                )
                
                # Create agency presentation summary
                summary_file = export_manager.create_agency_presentation_summary(
                    results, session.session_id
                )
                
                print(f"\nAuto-generated exports:")
                for format_name, filepath in exported_files.items():
                    print(f"  {format_name.upper()}: {filepath}")
                if summary_file:
                    print(f"  Agency Summary: {summary_file}")
            
            print(f"\nTo view detailed results, run:")
            print(f"  {sys.argv[0]} results --session {session.session_id}")
        
        engine.close()
        return 0
        
    except AnalysisError as e:
        logger.error(f"Analysis failed: {e.message}")
        print(f"Error: {ErrorHandler.get_user_friendly_message(e)}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_results(args: argparse.Namespace) -> int:
    """Handle results command."""
    logger = logging.getLogger(__name__)
    
    try:
        db = Database(args.database)
        engine = AnalysisEngine(db)
        
        if args.session:
            # Show results for specific session
            results = engine.get_analysis_results(args.session)
            
            if not results:
                print(f"No results found for session: {args.session}")
                return 1
            
            print(f"\nResults for session: {args.session}")
            print(f"Total documents: {len(results)}")
            print("-" * 80)
            
            for i, result in enumerate(results, 1):
                print(f"\n{i}. Document: {result['document_number']}")
                print(f"   Title: {result['title'][:100]}...")
                print(f"   Agency: {extract_agency_name(result['agency_slug'])}")
                print(f"   Category: {result['analysis']['category']}")
                print(f"   Success: {result['analysis']['success']}")
                
                if result['analysis']['statutory_references']:
                    print(f"   Statutory References: {len(result['analysis']['statutory_references'])}")
                
                if result['analysis']['reform_recommendations']:
                    print(f"   Reform Recommendations: {len(result['analysis']['reform_recommendations'])}")
                
                if result['analysis']['justification']:
                    justification = result['analysis']['justification'][:200]
                    print(f"   Justification: {justification}...")
        
        else:
            # Show recent sessions
            query = "SELECT * FROM sessions ORDER BY created_at DESC LIMIT 10"
            sessions = db.execute_query(query)
            
            if not sessions:
                print("No analysis sessions found.")
                return 0
            
            print("\nRecent Analysis Sessions:")
            print("-" * 80)
            
            for session in sessions:
                session_dict = dict(session)
                print(f"Session: {session_dict['session_id']}")
                print(f"  Status: {session_dict['status']}")
                print(f"  Strategy: {session_dict['prompt_strategy']}")
                print(f"  Progress: {session_dict['documents_processed']}/{session_dict['total_documents']}")
                print(f"  Created: {session_dict['created_at']}")
                print()
        
        engine.close()
        return 0
        
    except Exception as e:
        logger.error(f"Failed to retrieve results: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_list_agencies(args: argparse.Namespace) -> int:
    """Handle list-agencies command."""
    print("\nAvailable Test Agencies:")
    print("-" * 50)
    
    for i, agency_slug in enumerate(Config.TEST_AGENCIES, 1):
        agency_name = extract_agency_name(agency_slug)
        print(f"{i}. {agency_name}")
        print(f"   Slug: {agency_slug}")
        print()
    
    print("Note: These are small agencies selected for proof of concept testing.")
    print("Use the agency slug in the --agency parameter.")
    
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Handle status command."""
    logger = logging.getLogger(__name__)
    
    try:
        db = Database(args.database)
        
        # Database statistics
        doc_count = db.execute_query("SELECT COUNT(*) FROM documents")[0][0]
        analysis_count = db.execute_query("SELECT COUNT(*) FROM analyses")[0][0]
        session_count = db.execute_query("SELECT COUNT(*) FROM sessions")[0][0]
        
        print("\nCFR Document Analyzer Status:")
        print("-" * 40)
        print(f"Database: {args.database}")
        print(f"Documents cached: {doc_count}")
        print(f"Analyses completed: {analysis_count}")
        print(f"Sessions created: {session_count}")
        
        # Recent activity
        if session_count > 0:
            recent_session = db.execute_query(
                "SELECT * FROM sessions ORDER BY created_at DESC LIMIT 1"
            )[0]
            session_dict = dict(recent_session)
            
            print(f"\nMost Recent Session:")
            print(f"  ID: {session_dict['session_id']}")
            print(f"  Status: {session_dict['status']}")
            print(f"  Created: {session_dict['created_at']}")
        
        # Configuration
        print(f"\nConfiguration:")
        print(f"  Default model: {Config.DEFAULT_MODEL}")
        print(f"  Default strategy: {Config.DEFAULT_PROMPT_STRATEGY}")
        print(f"  Default limit: {Config.DEFAULT_DOCUMENT_LIMIT}")
        print(f"  Output directory: {Config.OUTPUT_DIRECTORY}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1


def save_results_to_file(results: List[dict], output_path: str, session_id: str):
    """Save analysis results to file."""
    import json
    from datetime import datetime
    
    output_data = {
        'session_id': session_id,
        'generated_at': datetime.now().isoformat(),
        'total_documents': len(results),
        'results': results
    }
    
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)


def main() -> int:
    """Main CLI entry point."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Set up logging
    if args.verbose:
        Config.setup_logging(verbose=True)
    elif args.quiet:
        logging.basicConfig(level=logging.ERROR)
    else:
        Config.setup_logging(verbose=False)
    
    # Validate configuration
    try:
        Config.validate()
    except Exception as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    
    # Handle commands
    if args.command == 'analyze':
        return cmd_analyze(args)
    elif args.command == 'results':
        return cmd_results(args)
    elif args.command == 'list-agencies':
        return cmd_list_agencies(args)
    elif args.command == 'status':
        return cmd_status(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())