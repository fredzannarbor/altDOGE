"""
Report Generator for formatting and exporting document counting results.

This module handles the generation of reports in various formats (CSV, JSON)
with proper formatting, metadata, and summary statistics.
"""

import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import CountingResults, AgencyDocumentCount


logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates reports from document counting results in various formats."""
    
    def __init__(self, output_directory: str = "./results"):
        """
        Initialize the report generator.
        
        Args:
            output_directory: Directory to save generated reports
        """
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Report generator initialized with output directory: {self.output_directory}")
    
    def generate_csv_report(self, results: CountingResults, filename: Optional[str] = None) -> str:
        """
        Generate a CSV report from counting results.
        
        Args:
            results: CountingResults object with data to export
            filename: Optional custom filename (default: auto-generated)
            
        Returns:
            Path to the generated CSV file
            
        Raises:
            IOError: If file cannot be written
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cfr_agency_document_counts_{timestamp}.csv"
        
        filepath = self.output_directory / filename
        
        logger.info(f"Generating CSV report: {filepath}")
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'agency_name',
                    'agency_slug',
                    'cfr_citation',
                    'parent_agency',
                    'active',
                    'document_count',
                    'query_successful',
                    'error_message',
                    'last_updated'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
                writer.writeheader()
                
                for result in results.results:
                    writer.writerow({
                        'agency_name': self._escape_csv_value(result.agency.name),
                        'agency_slug': result.agency.slug,
                        'cfr_citation': self._escape_csv_value(result.agency.cfr_citation),
                        'parent_agency': self._escape_csv_value(result.agency.parent_agency),
                        'active': result.agency.active,
                        'document_count': result.document_count,
                        'query_successful': result.query_successful,
                        'error_message': self._escape_csv_value(result.error_message or ''),
                        'last_updated': result.last_updated.isoformat()
                    })
            
            logger.info(f"CSV report generated successfully: {filepath}")
            return str(filepath)
            
        except IOError as e:
            logger.error(f"Failed to write CSV report: {e}")
            raise IOError(f"Failed to write CSV report to {filepath}: {e}")
    
    def generate_json_report(self, results: CountingResults, filename: Optional[str] = None, 
                           include_metadata: bool = True) -> str:
        """
        Generate a JSON report from counting results.
        
        Args:
            results: CountingResults object with data to export
            filename: Optional custom filename (default: auto-generated)
            include_metadata: Whether to include metadata and summary statistics
            
        Returns:
            Path to the generated JSON file
            
        Raises:
            IOError: If file cannot be written
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cfr_agency_document_counts_{timestamp}.json"
        
        filepath = self.output_directory / filename
        
        logger.info(f"Generating JSON report: {filepath}")
        
        try:
            report_data = self._build_json_report_data(results, include_metadata)
            
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(report_data, jsonfile, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"JSON report generated successfully: {filepath}")
            return str(filepath)
            
        except IOError as e:
            logger.error(f"Failed to write JSON report: {e}")
            raise IOError(f"Failed to write JSON report to {filepath}: {e}")
    
    def generate_summary_report(self, results: CountingResults, filename: Optional[str] = None) -> str:
        """
        Generate a human-readable summary report.
        
        Args:
            results: CountingResults object with data to summarize
            filename: Optional custom filename (default: auto-generated)
            
        Returns:
            Path to the generated summary file
            
        Raises:
            IOError: If file cannot be written
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cfr_agency_summary_{timestamp}.txt"
        
        filepath = self.output_directory / filename
        
        logger.info(f"Generating summary report: {filepath}")
        
        try:
            with open(filepath, 'w', encoding='utf-8') as summaryfile:
                summaryfile.write(self._build_summary_content(results))
            
            logger.info(f"Summary report generated successfully: {filepath}")
            return str(filepath)
            
        except IOError as e:
            logger.error(f"Failed to write summary report: {e}")
            raise IOError(f"Failed to write summary report to {filepath}: {e}")
    
    def generate_all_reports(self, results: CountingResults, base_filename: Optional[str] = None) -> Dict[str, str]:
        """
        Generate all report formats (CSV, JSON, Summary).
        
        Args:
            results: CountingResults object with data to export
            base_filename: Optional base filename (timestamp will be added)
            
        Returns:
            Dictionary mapping report type to file path
        """
        logger.info("Generating all report formats")
        
        if base_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"cfr_agency_document_counts_{timestamp}"
        
        reports = {}
        
        try:
            reports['csv'] = self.generate_csv_report(results, f"{base_filename}.csv")
            reports['json'] = self.generate_json_report(results, f"{base_filename}.json")
            reports['summary'] = self.generate_summary_report(results, f"{base_filename}_summary.txt")
            
            logger.info(f"All reports generated successfully: {len(reports)} files")
            return reports
            
        except Exception as e:
            logger.error(f"Failed to generate all reports: {e}")
            raise
    
    def _escape_csv_value(self, value: str) -> str:
        """
        Escape CSV values to handle special characters.
        
        Args:
            value: String value to escape
            
        Returns:
            Escaped string safe for CSV
        """
        if not value:
            return ""
        
        # Remove any null bytes and normalize whitespace
        cleaned = str(value).replace('\x00', '').strip()
        
        # Replace line breaks with spaces
        cleaned = cleaned.replace('\n', ' ').replace('\r', ' ')
        
        # Normalize multiple spaces
        cleaned = ' '.join(cleaned.split())
        
        return cleaned
    
    def _build_json_report_data(self, results: CountingResults, include_metadata: bool) -> Dict[str, Any]:
        """
        Build the JSON report data structure.
        
        Args:
            results: CountingResults object
            include_metadata: Whether to include metadata
            
        Returns:
            Dictionary with report data
        """
        report_data = {}
        
        if include_metadata:
            report_data['metadata'] = {
                'generated_at': datetime.now().isoformat(),
                'total_agencies': results.total_agencies,
                'successful_queries': results.successful_queries,
                'failed_queries': results.failed_queries,
                'agencies_with_documents': results.agencies_with_documents,
                'agencies_without_documents': results.agencies_without_documents,
                'total_documents': results.total_documents,
                'execution_time_seconds': results.execution_time,
                'success_rate_percent': results.success_rate,
                'processing_timestamp': results.timestamp.isoformat()
            }
            
            report_data['summary'] = results.get_summary()
        
        # Convert results to JSON-serializable format
        report_data['agencies'] = []
        for result in results.results:
            agency_data = {
                'agency': {
                    'name': result.agency.name,
                    'slug': result.agency.slug,
                    'cfr_citation': result.agency.cfr_citation,
                    'parent_agency': result.agency.parent_agency,
                    'active': result.agency.active,
                    'description': result.agency.description
                },
                'document_count': result.document_count,
                'query_successful': result.query_successful,
                'error_message': result.error_message,
                'last_updated': result.last_updated.isoformat()
            }
            report_data['agencies'].append(agency_data)
        
        return report_data
    
    def _build_summary_content(self, results: CountingResults) -> str:
        """
        Build the content for the summary report.
        
        Args:
            results: CountingResults object
            
        Returns:
            Formatted summary content
        """
        lines = []
        lines.append("="*80)
        lines.append("CFR AGENCY DOCUMENT COUNTER - SUMMARY REPORT")
        lines.append("="*80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Processing completed: {results.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Overall statistics
        lines.append("OVERALL STATISTICS")
        lines.append("-" * 40)
        lines.append(f"Total agencies processed: {results.total_agencies}")
        lines.append(f"Successful queries: {results.successful_queries}")
        lines.append(f"Failed queries: {results.failed_queries}")
        lines.append(f"Success rate: {results.success_rate:.1f}%")
        lines.append(f"Execution time: {results.execution_time:.1f} seconds")
        lines.append("")
        
        # Document statistics
        lines.append("DOCUMENT STATISTICS")
        lines.append("-" * 40)
        lines.append(f"Agencies with documents: {results.agencies_with_documents}")
        lines.append(f"Agencies without documents: {results.agencies_without_documents}")
        lines.append(f"Total documents found: {results.total_documents:,}")
        
        if results.agencies_with_documents > 0:
            avg_docs = results.total_documents / results.agencies_with_documents
            lines.append(f"Average documents per agency (with docs): {avg_docs:.1f}")
        
        lines.append("")
        
        # Top agencies by document count
        successful_results = [r for r in results.results if r.query_successful and r.document_count > 0]
        if successful_results:
            top_agencies = sorted(successful_results, key=lambda x: x.document_count, reverse=True)[:10]
            
            lines.append("TOP 10 AGENCIES BY DOCUMENT COUNT")
            lines.append("-" * 40)
            for i, result in enumerate(top_agencies, 1):
                lines.append(f"{i:2d}. {result.agency.name}: {result.document_count:,} documents")
            lines.append("")
        
        # Failed queries
        failed_results = [r for r in results.results if not r.query_successful]
        if failed_results:
            lines.append("FAILED QUERIES")
            lines.append("-" * 40)
            lines.append(f"Total failed: {len(failed_results)}")
            
            # Group by error message
            error_groups = {}
            for result in failed_results:
                error_msg = result.error_message or "Unknown error"
                if error_msg not in error_groups:
                    error_groups[error_msg] = []
                error_groups[error_msg].append(result.agency.name)
            
            for error_msg, agencies in error_groups.items():
                lines.append(f"\nError: {error_msg}")
                lines.append(f"Affected agencies ({len(agencies)}):")
                for agency in sorted(agencies)[:5]:  # Show first 5
                    lines.append(f"  - {agency}")
                if len(agencies) > 5:
                    lines.append(f"  ... and {len(agencies) - 5} more")
            lines.append("")
        
        # Agencies without documents
        zero_doc_agencies = [r for r in results.results if r.query_successful and r.document_count == 0]
        if zero_doc_agencies:
            lines.append("AGENCIES WITH ZERO DOCUMENTS")
            lines.append("-" * 40)
            lines.append(f"Total: {len(zero_doc_agencies)}")
            for result in sorted(zero_doc_agencies, key=lambda x: x.agency.name)[:10]:
                lines.append(f"  - {result.agency.name}")
            if len(zero_doc_agencies) > 10:
                lines.append(f"  ... and {len(zero_doc_agencies) - 10} more")
            lines.append("")
        
        lines.append("="*80)
        lines.append("End of Report")
        lines.append("="*80)
        
        return "\n".join(lines)
    
    def validate_output_format(self, format_name: str) -> bool:
        """
        Validate if the output format is supported.
        
        Args:
            format_name: Name of the format to validate
            
        Returns:
            True if format is supported
        """
        supported_formats = {'csv', 'json', 'summary', 'txt'}
        return format_name.lower() in supported_formats
    
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported output formats.
        
        Returns:
            List of supported format names
        """
        return ['csv', 'json', 'summary']
    
    def cleanup_old_reports(self, days_old: int = 30) -> int:
        """
        Clean up old report files.
        
        Args:
            days_old: Remove files older than this many days
            
        Returns:
            Number of files removed
        """
        if not self.output_directory.exists():
            return 0
        
        cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        removed_count = 0
        
        for file_path in self.output_directory.glob("cfr_agency_*"):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    removed_count += 1
                    logger.info(f"Removed old report: {file_path}")
                except OSError as e:
                    logger.warning(f"Failed to remove old report {file_path}: {e}")
        
        logger.info(f"Cleanup completed: {removed_count} old reports removed")
        return removed_count