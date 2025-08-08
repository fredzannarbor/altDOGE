#!/usr/bin/env python3
"""
Main script for the CFR Agency Document Counter.

This script orchestrates the entire document counting process, from loading
agency data to generating reports with comprehensive configuration handling.
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import List, Optional

from .config import Config
from .data_loader import AgencyDataLoader
from .api_client import FederalRegisterClient
from .document_counter import DocumentCounter
from .progress_tracker import ProgressTracker
from .report_generator import ReportGenerator


def setup_argument_parser() -> argparse.ArgumentParser:
    """
    Set up command-line argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Count documents for CFR agencies using the Federal Register API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s agencies.csv
  %(prog)s agencies.csv --output-dir ./reports --format csv json
  %(prog)s agencies.csv --rate-limit 0.5 --timeout 60 --verbose
  %(prog)s agencies.csv --active-only --progress-interval 5
        """
    )
    
    # Required arguments
    parser.add_argument(
        'agencies_file',
        help='Path to the agencies CSV file'
    )
    
    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument(
        '--output-dir', '-o',
        default=Config.OUTPUT_DIRECTORY,
        help=f'Output directory for reports (default: {Config.OUTPUT_DIRECTORY})'
    )
    output_group.add_argument(
        '--format', '-f',
        nargs='+',
        choices=['csv', 'json', 'summary'],
        default=Config.DEFAULT_OUTPUT_FORMATS,
        help=f'Output formats (default: {" ".join(Config.DEFAULT_OUTPUT_FORMATS)})'
    )
    output_group.add_argument(
        '--filename',
        help='Base filename for reports (default: auto-generated with timestamp)'
    )
    
    # API configuration
    api_group = parser.add_argument_group('API Configuration')
    api_group.add_argument(
        '--api-url',
        default=Config.FR_API_BASE_URL,
        help=f'Federal Register API base URL (default: {Config.FR_API_BASE_URL})'
    )
    api_group.add_argument(
        '--rate-limit',
        type=float,
        default=Config.FR_API_RATE_LIMIT,
        help=f'API rate limit in requests per second (default: {Config.FR_API_RATE_LIMIT})'
    )
    api_group.add_argument(
        '--timeout',
        type=int,
        default=Config.REQUEST_TIMEOUT,
        help=f'Request timeout in seconds (default: {Config.REQUEST_TIMEOUT})'
    )
    api_group.add_argument(
        '--max-retries',
        type=int,
        default=Config.MAX_RETRIES,
        help=f'Maximum number of retries for failed requests (default: {Config.MAX_RETRIES})'
    )
    api_group.add_argument(
        '--direct-fetch',
        action='store_true',
        help='Use direct web scraping instead of API (bypasses API rate limiting issues)'
    )
    
    # Filtering options
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument(
        '--active-only',
        action='store_true',
        help='Process only active agencies'
    )
    filter_group.add_argument(
        '--cfr-only',
        action='store_true',
        default=True,
        help='Process only agencies with CFR citations (default: True)'
    )
    filter_group.add_argument(
        '--include-inactive',
        action='store_true',
        help='Include inactive agencies (overrides --active-only)'
    )
    
    # Progress and logging
    progress_group = parser.add_argument_group('Progress and Logging')
    progress_group.add_argument(
        '--progress-interval',
        type=float,
        default=10.0,
        help='Progress update interval as percentage (default: 10.0)'
    )
    progress_group.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    progress_group.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress progress output (logging only)'
    )
    progress_group.add_argument(
        '--log-file',
        help='Log file path (default: cfr_agency_counter.log)'
    )
    
    # Validation and testing
    test_group = parser.add_argument_group('Validation and Testing')
    test_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration and agencies without making API calls'
    )
    test_group.add_argument(
        '--limit',
        type=int,
        help='Limit processing to first N agencies (for testing)'
    )
    test_group.add_argument(
        '--validate-config',
        action='store_true',
        help='Validate configuration and exit'
    )
    
    return parser


def validate_arguments(args: argparse.Namespace) -> List[str]:
    """
    Validate command-line arguments.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check agencies file exists
    agencies_file = Path(args.agencies_file)
    if not agencies_file.exists():
        errors.append(f"Agencies file not found: {agencies_file}")
    elif not agencies_file.is_file():
        errors.append(f"Agencies path is not a file: {agencies_file}")
    
    # Validate numeric arguments
    if args.rate_limit <= 0:
        errors.append("Rate limit must be positive")
    
    if args.timeout <= 0:
        errors.append("Timeout must be positive")
    
    if args.max_retries < 0:
        errors.append("Max retries cannot be negative")
    
    if args.progress_interval <= 0 or args.progress_interval > 100:
        errors.append("Progress interval must be between 0 and 100")
    
    if args.limit is not None and args.limit <= 0:
        errors.append("Limit must be positive")
    
    # Validate conflicting options
    if args.verbose and args.quiet:
        errors.append("Cannot specify both --verbose and --quiet")
    
    # Validate output directory
    try:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        errors.append(f"Cannot create output directory {args.output_dir}: {e}")
    
    return errors


def setup_logging(args: argparse.Namespace) -> None:
    """
    Set up logging configuration.
    
    Args:
        args: Parsed command-line arguments
    """
    log_level = logging.DEBUG if args.verbose else logging.INFO
    if args.quiet:
        log_level = logging.WARNING
    
    # Configure logging
    log_format = Config.LOG_FORMAT
    handlers = []
    
    # Console handler
    if not args.quiet:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(console_handler)
    
    # File handler
    log_file = args.log_file or 'cfr_agency_counter.log'
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)  # Always debug level for file
    file_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        format=log_format
    )
    
    # Reduce noise from urllib3
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def load_agencies(args: argparse.Namespace) -> List:
    """
    Load and filter agencies from the CSV file.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        List of filtered Agency objects
        
    Raises:
        SystemExit: If agency loading fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        loader = AgencyDataLoader()
        agencies = loader.load_agencies(args.agencies_file)
        
        logger.info(f"Loaded {len(agencies)} agencies from {args.agencies_file}")
        
        # Apply filters
        if args.cfr_only:
            agencies = loader.filter_cfr_agencies(agencies)
            logger.info(f"Filtered to {len(agencies)} agencies with CFR citations")
        
        if args.active_only and not args.include_inactive:
            agencies = loader.get_active_agencies(agencies)
            logger.info(f"Filtered to {len(agencies)} active agencies")
        
        # Apply limit for testing
        if args.limit:
            agencies = agencies[:args.limit]
            logger.info(f"Limited to first {len(agencies)} agencies for testing")
        
        if not agencies:
            logger.error("No agencies to process after filtering")
            sys.exit(1)
        
        # Log statistics
        stats = loader.get_agency_statistics(agencies)
        logger.info(f"Agency statistics: {stats}")
        
        return agencies
        
    except Exception as e:
        logger.error(f"Failed to load agencies: {e}")
        sys.exit(1)


def create_api_client(args: argparse.Namespace) -> FederalRegisterClient:
    """
    Create and configure the Federal Register API client.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Configured FederalRegisterClient instance
    """
    logger = logging.getLogger(__name__)
    
    try:
        client = FederalRegisterClient(
            base_url=args.api_url,
            rate_limit=args.rate_limit
        )
        
        # Update configuration
        Config.REQUEST_TIMEOUT = args.timeout
        Config.MAX_RETRIES = args.max_retries
        
        logger.info(f"API client configured: {args.api_url}, rate limit: {args.rate_limit}/s")
        return client
        
    except Exception as e:
        logger.error(f"Failed to create API client: {e}")
        sys.exit(1)


def process_agencies(agencies: List, api_client: Optional[FederalRegisterClient], 
                    args: argparse.Namespace) -> 'CountingResults':
    """
    Process agencies and count documents.
    
    Args:
        agencies: List of Agency objects to process
        api_client: Configured API client (optional if using direct fetch)
        args: Parsed command-line arguments
        
    Returns:
        CountingResults with processing results
    """
    logger = logging.getLogger(__name__)
    
    # Create document counter
    counter = DocumentCounter(
        api_client=api_client,
        use_direct_fetch=args.direct_fetch,
        rate_limit=args.rate_limit
    )
    
    # Set up progress tracking
    if not args.quiet:
        progress_tracker = ProgressTracker(
            total_items=len(agencies),
            update_interval=args.progress_interval
        )
        progress_tracker.start()
        
        # Monkey patch the counter to update progress
        original_process = counter._process_single_agency
        
        def progress_wrapper(agency, api_counts):
            progress_tracker.set_current_item(agency.name)
            result = original_process(agency, api_counts)
            progress_tracker.update(agency.name, result.query_successful)
            return result
        
        counter._process_single_agency = progress_wrapper
    
    try:
        logger.info(f"Starting document counting for {len(agencies)} agencies")
        results = counter.count_documents_by_agency(agencies)
        
        if not args.quiet:
            progress_tracker.finish()
        
        logger.info("Document counting completed successfully")
        logger.info(results.get_summary())
        
        return results
        
    except Exception as e:
        logger.error(f"Document counting failed: {e}")
        if not args.quiet:
            progress_tracker.finish()
        raise


def generate_reports(results: 'CountingResults', args: argparse.Namespace) -> None:
    """
    Generate reports from counting results.
    
    Args:
        results: CountingResults to generate reports from
        args: Parsed command-line arguments
    """
    logger = logging.getLogger(__name__)
    
    try:
        generator = ReportGenerator(args.output_dir)
        
        if len(args.format) == 1:
            # Generate single format
            format_name = args.format[0]
            if format_name == 'csv':
                filepath = generator.generate_csv_report(results, args.filename)
            elif format_name == 'json':
                filepath = generator.generate_json_report(results, args.filename)
            elif format_name == 'summary':
                filepath = generator.generate_summary_report(results, args.filename)
            
            logger.info(f"Report generated: {filepath}")
            print(f"Report saved to: {filepath}")
            
        else:
            # Generate multiple formats
            reports = generator.generate_all_reports(results, args.filename)
            
            logger.info(f"Generated {len(reports)} reports")
            print("Reports generated:")
            for format_name, filepath in reports.items():
                if format_name in args.format:
                    print(f"  {format_name.upper()}: {filepath}")
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise


def main() -> int:
    """
    Main entry point for the CFR Agency Document Counter.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Parse command-line arguments
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Validate arguments
    validation_errors = validate_arguments(args)
    if validation_errors:
        print("Configuration errors:", file=sys.stderr)
        for error in validation_errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    
    # Set up logging
    setup_logging(args)
    logger = logging.getLogger(__name__)
    
    # Validate configuration if requested
    if args.validate_config:
        try:
            Config.validate()
            print("Configuration is valid")
            return 0
        except Exception as e:
            print(f"Configuration error: {e}", file=sys.stderr)
            return 1
    
    logger.info("CFR Agency Document Counter starting")
    logger.info(f"Arguments: {vars(args)}")
    
    try:
        # Load agencies
        agencies = load_agencies(args)
        
        # Dry run mode
        if args.dry_run:
            print(f"Dry run: Would process {len(agencies)} agencies")
            print("Configuration validated successfully")
            return 0
        
        # Create API client (only if not using direct fetch)
        api_client = None
        if not args.direct_fetch:
            api_client = create_api_client(args)
        else:
            logger.info("Using direct fetch mode - skipping API client creation")
        
        # Process agencies
        results = process_agencies(agencies, api_client, args)
        
        # Generate reports
        generate_reports(results, args)
        
        # Clean up
        if api_client:
            api_client.close()
        
        logger.info("CFR Agency Document Counter completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        print("\nProcess interrupted by user")
        return 130
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())