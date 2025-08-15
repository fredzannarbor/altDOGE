#!/usr/bin/env python3
"""
Command-line interface for CFR Document Analyzer.

Provides CLI access to document analysis functionality.
"""

import argparse
import sys
import logging
import csv
from pathlib import Path
from typing import List, Optional

from .config import Config
from .database import Database
from .analysis_engine import AnalysisEngine
from .export_manager import ExportManager
from .statistics_engine import StatisticsEngine
from .session_manager import SessionManager
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
  %(prog)s analyze --agencies-file agencies.csv --limit 10
  %(prog)s results --session session_20250807_123456
  %(prog)s meta-analysis --session session_20250807_123456 --format markdown
  %(prog)s statistics --include-patterns --format markdown
  %(prog)s sessions list --status completed --limit 10
  %(prog)s export --session session_20250807_123456 --format all
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze documents for an agency or agencies from CSV')
    
    # Create mutually exclusive group for agency input
    agency_group = analyze_parser.add_mutually_exclusive_group(required=True)
    agency_group.add_argument(
        '--agency', '-a',
        help='Single agency slug to analyze (e.g., national-credit-union-administration)'
    )
    agency_group.add_argument(
        '--agencies-csv', '-c',
        help='CSV file containing agencies to analyze (must have "agency_slug" column)'
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
    analyze_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    analyze_parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress output except errors'
    )
    analyze_parser.add_argument(
        '--database', '-d',
        default=Config.DATABASE_PATH,
        help=f'Database path (default: {Config.DATABASE_PATH})'
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
    results_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    results_parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress output except errors'
    )
    results_parser.add_argument(
        '--database', '-d',
        default=Config.DATABASE_PATH,
        help=f'Database path (default: {Config.DATABASE_PATH})'
    )
    
    # List agencies command
    list_parser = subparsers.add_parser('list-agencies', help='List available test agencies')
    list_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    list_parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress output except errors'
    )
    list_parser.add_argument(
        '--database', '-d',
        default=Config.DATABASE_PATH,
        help=f'Database path (default: {Config.DATABASE_PATH})'
    )
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status and statistics')
    status_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    status_parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress output except errors'
    )
    status_parser.add_argument(
        '--database', '-d',
        default=Config.DATABASE_PATH,
        help=f'Database path (default: {Config.DATABASE_PATH})'
    )
    
    # Meta-analysis command
    meta_parser = subparsers.add_parser('meta-analysis', help='Perform meta-analysis on session results')
    meta_parser.add_argument(
        '--session', '-s',
        required=True,
        help='Session ID to perform meta-analysis on'
    )
    meta_parser.add_argument(
        '--output', '-o',
        help='Output file for meta-analysis results (default: auto-generated)'
    )
    meta_parser.add_argument(
        '--format', '-f',
        choices=['json', 'markdown', 'text'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    meta_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    meta_parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress output except errors'
    )
    meta_parser.add_argument(
        '--database', '-d',
        default=Config.DATABASE_PATH,
        help=f'Database path (default: {Config.DATABASE_PATH})'
    )
    
    # Statistics command
    stats_parser = subparsers.add_parser('statistics', help='Generate analysis statistics and reports')
    stats_parser.add_argument(
        '--format', '-f',
        choices=['table', 'json', 'markdown'],
        default='table',
        help='Output format (default: table)'
    )
    stats_parser.add_argument(
        '--output', '-o',
        help='Output file for statistics (default: console output)'
    )
    stats_parser.add_argument(
        '--date-from',
        help='Start date for statistics (YYYY-MM-DD)'
    )
    stats_parser.add_argument(
        '--date-to',
        help='End date for statistics (YYYY-MM-DD)'
    )
    stats_parser.add_argument(
        '--agencies',
        nargs='+',
        help='Specific agencies to analyze'
    )
    stats_parser.add_argument(
        '--include-patterns',
        action='store_true',
        help='Include pattern analysis'
    )
    stats_parser.add_argument(
        '--include-costs',
        action='store_true',
        help='Include cost analysis'
    )
    stats_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    stats_parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress output except errors'
    )
    stats_parser.add_argument(
        '--database', '-d',
        default=Config.DATABASE_PATH,
        help=f'Database path (default: {Config.DATABASE_PATH})'
    )
    
    # Sessions command
    sessions_parser = subparsers.add_parser('sessions', help='Manage analysis sessions')
    sessions_subparsers = sessions_parser.add_subparsers(dest='sessions_action', help='Session actions')
    
    # List sessions
    list_sessions_parser = sessions_subparsers.add_parser('list', help='List analysis sessions')
    list_sessions_parser.add_argument(
        '--status',
        choices=['created', 'running', 'completed', 'failed', 'cancelled'],
        help='Filter by session status'
    )
    list_sessions_parser.add_argument(
        '--limit', '-l',
        type=int,
        default=20,
        help='Maximum number of sessions to show (default: 20)'
    )
    list_sessions_parser.add_argument(
        '--format', '-f',
        choices=['table', 'json'],
        default='table',
        help='Output format (default: table)'
    )
    
    # Resume session
    resume_session_parser = sessions_subparsers.add_parser('resume', help='Resume interrupted session')
    resume_session_parser.add_argument(
        '--session', '-s',
        required=True,
        help='Session ID to resume'
    )
    
    # Cancel session
    cancel_session_parser = sessions_subparsers.add_parser('cancel', help='Cancel running session')
    cancel_session_parser.add_argument(
        '--session', '-s',
        required=True,
        help='Session ID to cancel'
    )
    
    # Archive session
    archive_session_parser = sessions_subparsers.add_parser('archive', help='Archive session to file')
    archive_session_parser.add_argument(
        '--session', '-s',
        required=True,
        help='Session ID to archive'
    )
    archive_session_parser.add_argument(
        '--output', '-o',
        help='Archive file path (default: auto-generated)'
    )
    
    # Cleanup sessions
    cleanup_sessions_parser = sessions_subparsers.add_parser('cleanup', help='Clean up old sessions')
    cleanup_sessions_parser.add_argument(
        '--days-old',
        type=int,
        default=30,
        help='Age threshold in days (default: 30)'
    )
    cleanup_sessions_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be cleaned up without actually doing it'
    )
    
    # Add common arguments to all session subcommands
    for subparser in [list_sessions_parser, resume_session_parser, cancel_session_parser, 
                     archive_session_parser, cleanup_sessions_parser]:
        subparser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose logging'
        )
        subparser.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='Suppress output except errors'
        )
        subparser.add_argument(
            '--database', '-d',
            default=Config.DATABASE_PATH,
            help=f'Database path (default: {Config.DATABASE_PATH})'
        )
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export analysis results')
    export_parser.add_argument(
        '--session', '-s',
        required=True,
        help='Session ID to export'
    )
    export_parser.add_argument(
        '--format', '-f',
        choices=['json', 'csv', 'html', 'markdown', 'all'],
        default='all',
        help='Export format (default: all)'
    )
    export_parser.add_argument(
        '--output-dir', '-o',
        default='exports',
        help='Output directory (default: exports)'
    )
    export_parser.add_argument(
        '--include-meta-analysis',
        action='store_true',
        help='Include meta-analysis in export'
    )
    export_parser.add_argument(
        '--include-raw-responses',
        action='store_true',
        help='Include raw LLM responses'
    )
    export_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    export_parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress output except errors'
    )
    export_parser.add_argument(
        '--database', '-d',
        default=Config.DATABASE_PATH,
        help=f'Database path (default: {Config.DATABASE_PATH})'
    )
    

    
    return parser


def load_agencies_from_csv(csv_file_path: str) -> List[str]:
    """
    Load agency slugs from a CSV file.
    
    Args:
        csv_file_path: Path to CSV file containing agencies
        
    Returns:
        List of agency slugs
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV file is malformed or missing required columns
    """
    csv_path = Path(csv_file_path)
    
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file_path}")
    
    agencies = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Check for required column
            if 'agency_slug' not in reader.fieldnames:
                raise ValueError(f"CSV file must contain 'agency_slug' column. Found columns: {reader.fieldnames}")
            
            for row_num, row in enumerate(reader, 2):  # Start at 2 since header is row 1
                agency_slug = row.get('agency_slug', '').strip()
                
                if not agency_slug:
                    print(f"Warning: Empty agency_slug in row {row_num}, skipping")
                    continue
                
                agencies.append(agency_slug)
        
        if not agencies:
            raise ValueError(f"No valid agency slugs found in CSV file: {csv_file_path}")
        
        return agencies
        
    except csv.Error as e:
        raise ValueError(f"Error reading CSV file {csv_file_path}: {e}")


def cmd_analyze(args: argparse.Namespace) -> int:
    """Handle analyze command for single agency or CSV file of agencies."""
    logger = logging.getLogger(__name__)
    
    try:
        # Determine agencies to analyze
        if args.agency:
            # Single agency mode
            agencies = [args.agency]
            logger.info(f"Single agency mode: {args.agency}")
        elif args.agencies_csv:
            # CSV file mode
            agencies = load_agencies_from_csv(args.agencies_csv)
            logger.info(f"CSV mode: loaded {len(agencies)} agencies from {args.agencies_csv}")
        else:
            raise ValueError("Either --agency or --agencies-csv must be specified")
        
        # Validate inputs
        ErrorHandler.validate_document_limit(args.limit)
        
        # Initialize components
        db = Database(args.database)
        engine = AnalysisEngine(db)
        
        # Validate prompt strategy
        available_strategies = engine.prompt_manager.get_available_packages()
        ErrorHandler.validate_prompt_strategy(args.strategy, available_strategies)
        
        logger.info(f"Strategy: {args.strategy}")
        logger.info(f"Document limit per agency: {args.limit}")
        
        # Process each agency
        all_sessions = []
        total_documents_processed = 0
        
        for i, agency_slug in enumerate(agencies, 1):
            print(f"\n{'='*60}")
            print(f"Processing agency {i}/{len(agencies)}: {agency_slug}")
            print(f"{'='*60}")
            
            try:
                # Validate agency slug
                ErrorHandler.validate_agency_slug(agency_slug)
                
                # Run analysis for this agency
                session = engine.analyze_agency_documents(
                    agency_slug=agency_slug,
                    prompt_strategy=args.strategy,
                    document_limit=args.limit
                )
                
                all_sessions.append(session)
                total_documents_processed += session.documents_processed
                
                # Print individual agency results
                print(f"Agency: {extract_agency_name(agency_slug)}")
                print(f"Session ID: {session.session_id}")
                print(f"Status: {session.status.value}")
                print(f"Documents processed: {session.documents_processed}/{session.total_documents}")
                
                if session.status == SessionStatus.COMPLETED and session.documents_processed > 0:
                    # Get results for this agency
                    results = engine.get_analysis_results(session.session_id)
                    
                    # Count by category
                    categories = {}
                    for result in results:
                        category = result['analysis']['category'] or 'UNKNOWN'
                        categories[category] = categories.get(category, 0) + 1
                    
                    print(f"Categories:")
                    for category, count in categories.items():
                        print(f"  {category}: {count}")
                    
                    # Auto-generate exports for this agency
                    export_manager = ExportManager()
                    exported_files = export_manager.export_session_results(
                        results, session.session_id, ['json', 'csv', 'html']
                    )
                    
                    # Create agency presentation summary
                    summary_file = export_manager.create_agency_presentation_summary(
                        results, session.session_id
                    )
                    
                    print(f"Exports:")
                    for format_name, filepath in exported_files.items():
                        print(f"  {format_name.upper()}: {filepath}")
                    if summary_file:
                        print(f"  Summary: {summary_file}")
                
            except Exception as e:
                logger.error(f"Failed to analyze agency {agency_slug}: {e}")
                print(f"❌ Error analyzing {agency_slug}: {e}")
                continue
        
        # Print overall summary
        print(f"\n{'='*60}")
        print(f"BATCH ANALYSIS SUMMARY")
        print(f"{'='*60}")
        print(f"Total agencies processed: {len(all_sessions)}")
        print(f"Total documents processed: {total_documents_processed}")
        
        successful_sessions = [s for s in all_sessions if s.status == SessionStatus.COMPLETED]
        print(f"Successful agencies: {len(successful_sessions)}")
        
        if successful_sessions:
            # Show usage stats
            stats = engine.get_usage_statistics()
            print(f"\nOverall LLM Usage:")
            print(f"  Total calls: {stats['total_calls']}")
            print(f"  Success rate: {stats['success_rate']:.1f}%")
            print(f"  Total time: {stats['total_time']:.1f}s")
            
            print(f"\nSession IDs for detailed results:")
            for session in successful_sessions:
                agency_name = extract_agency_name(session.agency_slugs[0]) if session.agency_slugs else "Unknown"
                print(f"  {agency_name}: {session.session_id}")
        
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


def cmd_meta_analysis(args: argparse.Namespace) -> int:
    """Handle meta-analysis command."""
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize components
        database = Database(args.database)
        engine = AnalysisEngine(database)
        
        logger.info(f"Starting meta-analysis for session: {args.session}")
        
        # Check if session exists
        session_results = engine.get_analysis_results(args.session)
        if not session_results:
            print(f"Error: No analysis results found for session {args.session}", file=sys.stderr)
            return 1
        
        print(f"Performing meta-analysis on {len(session_results)} document analyses...")
        
        # Perform meta-analysis
        meta_analysis = engine.perform_meta_analysis(args.session)
        
        if not meta_analysis or not meta_analysis.success:
            error_msg = meta_analysis.error_message if meta_analysis else "Unknown error"
            print(f"Error: Meta-analysis failed: {error_msg}", file=sys.stderr)
            return 1
        
        print(f"Meta-analysis completed successfully in {meta_analysis.processing_time:.2f}s")
        
        # Generate output
        if args.output:
            output_path = Path(args.output)
        else:
            # Auto-generate filename
            timestamp = meta_analysis.created_at.strftime('%Y%m%d_%H%M%S') if meta_analysis.created_at else 'unknown'
            filename = f"meta_analysis_{args.session}_{timestamp}.{args.format}"
            output_path = Path(filename)
        
        # Save results based on format
        if args.format == 'json':
            save_meta_analysis_json(meta_analysis, output_path)
        elif args.format == 'markdown':
            save_meta_analysis_markdown(meta_analysis, output_path)
        else:  # text
            save_meta_analysis_text(meta_analysis, output_path)
        
        print(f"\nMeta-analysis results saved to: {output_path}")
        
        # Display summary
        if not args.quiet:
            print(f"\n=== META-ANALYSIS SUMMARY ===")
            if meta_analysis.executive_summary:
                print(f"\nExecutive Summary:")
                print(f"  {meta_analysis.executive_summary}")
            
            if meta_analysis.key_patterns:
                print(f"\nKey Patterns ({len(meta_analysis.key_patterns)}):")
                for i, pattern in enumerate(meta_analysis.key_patterns[:3], 1):
                    print(f"  {i}. {pattern}")
            
            if meta_analysis.priority_actions:
                print(f"\nTop Priority Actions ({len(meta_analysis.priority_actions)}):")
                for i, action in enumerate(meta_analysis.priority_actions[:3], 1):
                    print(f"  {i}. {action}")
            
            if meta_analysis.quick_wins:
                print(f"\nQuick Wins ({len(meta_analysis.quick_wins)}):")
                for i, win in enumerate(meta_analysis.quick_wins[:3], 1):
                    print(f"  {i}. {win}")
        
        engine.close()
        return 0
        
    except Exception as e:
        logger.error(f"Meta-analysis command failed: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1


def save_meta_analysis_json(meta_analysis, output_path: Path):
    """Save meta-analysis results as JSON."""
    import json
    from datetime import datetime
    
    data = {
        'session_id': meta_analysis.session_id,
        'generated_at': datetime.now().isoformat(),
        'processing_time': meta_analysis.processing_time,
        'success': meta_analysis.success,
        'key_patterns': meta_analysis.key_patterns,
        'strategic_themes': meta_analysis.strategic_themes,
        'priority_actions': meta_analysis.priority_actions,
        'goal_alignment': meta_analysis.goal_alignment,
        'implementation_roadmap': meta_analysis.implementation_roadmap,
        'executive_summary': meta_analysis.executive_summary,
        'reform_opportunities': meta_analysis.reform_opportunities,
        'implementation_challenges': meta_analysis.implementation_challenges,
        'stakeholder_impact': meta_analysis.stakeholder_impact,
        'resource_requirements': meta_analysis.resource_requirements,
        'risk_assessment': meta_analysis.risk_assessment,
        'quick_wins': meta_analysis.quick_wins,
        'long_term_strategy': meta_analysis.long_term_strategy
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_meta_analysis_markdown(meta_analysis, output_path: Path):
    """Save meta-analysis results as Markdown."""
    from datetime import datetime
    
    content = [
        f"# Meta-Analysis Report",
        f"",
        f"**Session ID:** {meta_analysis.session_id}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Processing Time:** {meta_analysis.processing_time:.2f} seconds",
        f"",
    ]
    
    if meta_analysis.executive_summary:
        content.extend([
            f"## Executive Summary",
            f"",
            f"{meta_analysis.executive_summary}",
            f"",
        ])
    
    if meta_analysis.key_patterns:
        content.extend([
            f"## Key Patterns",
            f"",
        ])
        for pattern in meta_analysis.key_patterns:
            content.append(f"- {pattern}")
        content.append("")
    
    if meta_analysis.strategic_themes:
        content.extend([
            f"## Strategic Themes",
            f"",
        ])
        for theme in meta_analysis.strategic_themes:
            content.append(f"- {theme}")
        content.append("")
    
    if meta_analysis.priority_actions:
        content.extend([
            f"## Priority Actions",
            f"",
        ])
        for i, action in enumerate(meta_analysis.priority_actions, 1):
            content.append(f"{i}. {action}")
        content.append("")
    
    if meta_analysis.quick_wins:
        content.extend([
            f"## Quick Wins",
            f"",
        ])
        for win in meta_analysis.quick_wins:
            content.append(f"- {win}")
        content.append("")
    
    if meta_analysis.reform_opportunities:
        content.extend([
            f"## Reform Opportunities",
            f"",
        ])
        for opportunity in meta_analysis.reform_opportunities:
            content.append(f"- {opportunity}")
        content.append("")
    
    if meta_analysis.implementation_challenges:
        content.extend([
            f"## Implementation Challenges",
            f"",
        ])
        for challenge in meta_analysis.implementation_challenges:
            content.append(f"- {challenge}")
        content.append("")
    
    if meta_analysis.goal_alignment:
        content.extend([
            f"## Goal Alignment",
            f"",
            f"{meta_analysis.goal_alignment}",
            f"",
        ])
    
    if meta_analysis.implementation_roadmap:
        content.extend([
            f"## Implementation Roadmap",
            f"",
            f"{meta_analysis.implementation_roadmap}",
            f"",
        ])
    
    if meta_analysis.long_term_strategy:
        content.extend([
            f"## Long-Term Strategy",
            f"",
            f"{meta_analysis.long_term_strategy}",
            f"",
        ])
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))


def save_meta_analysis_text(meta_analysis, output_path: Path):
    """Save meta-analysis results as plain text."""
    from datetime import datetime
    
    content = [
        f"META-ANALYSIS REPORT",
        f"=" * 50,
        f"",
        f"Session ID: {meta_analysis.session_id}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Processing Time: {meta_analysis.processing_time:.2f} seconds",
        f"",
    ]
    
    if meta_analysis.executive_summary:
        content.extend([
            f"EXECUTIVE SUMMARY",
            f"-" * 20,
            f"{meta_analysis.executive_summary}",
            f"",
        ])
    
    if meta_analysis.key_patterns:
        content.extend([
            f"KEY PATTERNS",
            f"-" * 15,
        ])
        for i, pattern in enumerate(meta_analysis.key_patterns, 1):
            content.append(f"{i}. {pattern}")
        content.append("")
    
    if meta_analysis.priority_actions:
        content.extend([
            f"PRIORITY ACTIONS",
            f"-" * 20,
        ])
        for i, action in enumerate(meta_analysis.priority_actions, 1):
            content.append(f"{i}. {action}")
        content.append("")
    
    if meta_analysis.quick_wins:
        content.extend([
            f"QUICK WINS",
            f"-" * 15,
        ])
        for i, win in enumerate(meta_analysis.quick_wins, 1):
            content.append(f"{i}. {win}")
        content.append("")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))


def cmd_statistics(args: argparse.Namespace) -> int:
    """Handle statistics command."""
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize components
        database = Database(args.database)
        stats_engine = StatisticsEngine(database)
        
        logger.info("Generating statistics report")
        
        # Get overall statistics
        overall_stats = stats_engine.get_overall_statistics(
            date_from=args.date_from,
            date_to=args.date_to
        )
        
        # Generate report based on format
        if args.format == 'json':
            report_data = {
                'overall_statistics': {
                    'total_documents': overall_stats.total_documents,
                    'total_sessions': overall_stats.total_sessions,
                    'success_rate': overall_stats.success_rate,
                    'average_processing_time': overall_stats.average_processing_time,
                    'date_range': overall_stats.date_range
                },
                'category_distribution': overall_stats.category_distribution,
                'agency_distribution': dict(list(overall_stats.agency_distribution.items())[:20])
            }
            
            # Add pattern analysis if requested
            if args.include_patterns:
                patterns = stats_engine.analyze_patterns()
                report_data['pattern_analysis'] = {
                    'common_statutory_references': patterns.common_statutory_references[:10],
                    'frequent_reform_recommendations': patterns.frequent_reform_recommendations[:10]
                }
            
            # Add cost analysis if requested
            if args.include_costs:
                report_data['cost_analysis'] = stats_engine.generate_cost_analysis()
            
            output = json.dumps(report_data, indent=2, ensure_ascii=False)
            
        elif args.format == 'markdown':
            output = stats_engine.generate_comprehensive_report('markdown')
            
        else:  # table format
            output = f"""
CFR DOCUMENT ANALYZER STATISTICS
{'='*50}

OVERALL STATISTICS:
  Total Documents Analyzed: {overall_stats.total_documents:,}
  Total Sessions: {overall_stats.total_sessions:,}
  Success Rate: {overall_stats.success_rate:.1f}%
  Average Processing Time: {overall_stats.average_processing_time:.2f} seconds
  Date Range: {overall_stats.date_range[0]} to {overall_stats.date_range[1]}

CATEGORY DISTRIBUTION:
"""
            for category, count in overall_stats.category_distribution.items():
                percentage = (count / max(1, overall_stats.total_documents)) * 100
                output += f"  {category}: {count:,} ({percentage:.1f}%)\n"
            
            output += "\nTOP AGENCIES:\n"
            for agency, count in list(overall_stats.agency_distribution.items())[:10]:
                output += f"  {agency}: {count:,} documents\n"
        
        # Output results
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Statistics saved to: {output_path}")
        else:
            print(output)
        
        return 0
        
    except Exception as e:
        logger.error(f"Statistics command failed: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_sessions(args: argparse.Namespace) -> int:
    """Handle sessions command."""
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize components
        database = Database(args.database)
        session_manager = SessionManager(database)
        
        if args.sessions_action == 'list':
            # List sessions
            status_filter = SessionStatus(args.status) if args.status else None
            sessions = session_manager.list_sessions(limit=args.limit, status_filter=status_filter)
            
            if not sessions:
                print("No sessions found.")
                return 0
            
            if args.format == 'json':
                session_data = []
                for session in sessions:
                    session_data.append({
                        'session_id': session.session_id,
                        'agency_slugs': session.agency_slugs,
                        'prompt_strategy': session.prompt_strategy,
                        'document_limit': session.document_limit,
                        'status': session.status.value,
                        'documents_processed': session.documents_processed,
                        'total_documents': session.total_documents,
                        'progress_percentage': session.progress_percentage,
                        'created_at': session.created_at.isoformat() if session.created_at else None,
                        'completed_at': session.completed_at.isoformat() if session.completed_at else None
                    })
                
                print(json.dumps(session_data, indent=2, ensure_ascii=False))
            
            else:  # table format
                print(f"\n{'Session ID':<30} {'Agencies':<40} {'Status':<12} {'Progress':<12} {'Created':<20}")
                print("-" * 120)
                
                for session in sessions:
                    agencies_str = ", ".join(session.agency_slugs)[:35] + "..." if len(", ".join(session.agency_slugs)) > 35 else ", ".join(session.agency_slugs)
                    progress_str = f"{session.documents_processed}/{session.total_documents}"
                    created_str = session.created_at.strftime("%Y-%m-%d %H:%M") if session.created_at else "Unknown"
                    
                    print(f"{session.session_id:<30} {agencies_str:<40} {session.status.value:<12} {progress_str:<12} {created_str:<20}")
        
        elif args.sessions_action == 'resume':
            # Resume session
            session = session_manager.resume_session(args.session)
            if session:
                print(f"Resumed session: {args.session}")
                print(f"Status: {session.status.value}")
                print(f"Progress: {session.documents_processed}/{session.total_documents}")
            else:
                print(f"Failed to resume session: {args.session}")
                return 1
        
        elif args.sessions_action == 'cancel':
            # Cancel session
            success = session_manager.cancel_session(args.session)
            if success:
                print(f"Cancelled session: {args.session}")
            else:
                print(f"Failed to cancel session: {args.session}")
                return 1
        
        elif args.sessions_action == 'archive':
            # Archive session
            success = session_manager.archive_session(args.session, args.output)
            if success:
                archive_path = args.output or f"{args.session}_archive.json"
                print(f"Archived session {args.session} to: {archive_path}")
            else:
                print(f"Failed to archive session: {args.session}")
                return 1
        
        elif args.sessions_action == 'cleanup':
            # Cleanup old sessions
            if args.dry_run:
                print(f"Dry run: Would clean up sessions older than {args.days_old} days")
                # This would show what would be cleaned up
                print("(Dry run functionality not implemented)")
            else:
                cleaned_count = session_manager.cleanup_old_sessions(args.days_old)
                print(f"Cleaned up {cleaned_count} old sessions")
        
        return 0
        
    except Exception as e:
        logger.error(f"Sessions command failed: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_export(args: argparse.Namespace) -> int:
    """Handle export command."""
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize components
        database = Database(args.database)
        engine = AnalysisEngine(database)
        export_manager = ExportManager(args.output_dir)
        
        logger.info(f"Exporting results for session: {args.session}")
        
        # Get session results
        results = engine.get_session_results(args.session)
        
        if not results:
            print(f"No results found for session: {args.session}")
            return 1
        
        # Determine export formats
        if args.format == 'all':
            formats = ['json', 'csv', 'html']
        else:
            formats = [args.format]
        
        # Export results
        exported_files = export_manager.export_session_results(
            results, args.session, formats
        )
        
        print(f"Exported {len(results)} results in {len(formats)} format(s):")
        for format_type, filepath in exported_files.items():
            print(f"  {format_type.upper()}: {filepath}")
        
        # Export meta-analysis if requested
        if args.include_meta_analysis:
            meta_analysis = engine.get_meta_analysis(args.session)
            if meta_analysis:
                # Save meta-analysis as markdown
                meta_path = Path(args.output_dir) / f"meta_analysis_{args.session}.md"
                save_meta_analysis_markdown(meta_analysis, meta_path)
                print(f"  META-ANALYSIS: {meta_path}")
            else:
                print("  Meta-analysis not available for this session")
        
        return 0
        
    except Exception as e:
        logger.error(f"Export command failed: {e}")
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
    elif args.command == 'meta-analysis':
        return cmd_meta_analysis(args)
    elif args.command == 'statistics':
        return cmd_statistics(args)
    elif args.command == 'sessions':
        return cmd_sessions(args)
    elif args.command == 'export':
        return cmd_export(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())