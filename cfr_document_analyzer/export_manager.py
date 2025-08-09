"""
Export manager for CFR Document Analyzer.

Handles exporting analysis results in various formats for agency staff presentation.
"""

import json
import csv
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .config import Config
from .utils import format_timestamp, clean_filename, extract_agency_name
from .llm_client import LLMClient


logger = logging.getLogger(__name__)


class ExportManager:
    """Manages export of analysis results in multiple formats."""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the export manager.
        
        Args:
            output_dir: Output directory (defaults to config)
        """
        self.output_dir = Path(output_dir or Config.OUTPUT_DIRECTORY)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize LLM client for agency synopsis generation
        self.llm_client = LLMClient()
        
        logger.info(f"Export manager initialized with output dir: {self.output_dir}")
    
    def export_session_results(self, results: List[Dict[str, Any]], session_id: str, 
                             formats: List[str] = None) -> Dict[str, str]:
        """
        Export analysis results for a session in multiple formats.
        
        Args:
            results: List of analysis result dictionaries
            session_id: Session identifier
            formats: List of formats to export (defaults to ['json', 'csv'])
            
        Returns:
            Dictionary mapping format to output file path
        """
        if not results:
            logger.warning("No results to export")
            return {}
        
        formats = formats or ['json', 'csv']
        exported_files = {}
        
        # Generate base filename
        timestamp = format_timestamp()
        agency_slug = results[0]['agency_slug'] if results else 'unknown'
        agency_name = clean_filename(extract_agency_name(agency_slug))
        
        base_filename = f"cfr_analysis_{agency_name}_{timestamp}"
        
        logger.info(f"Exporting {len(results)} results in formats: {formats}")
        
        for format_name in formats:
            try:
                if format_name == 'json':
                    filepath = self._export_json(results, session_id, base_filename)
                elif format_name == 'csv':
                    filepath = self._export_csv(results, session_id, base_filename)
                elif format_name == 'html':
                    filepath = self._export_html(results, session_id, base_filename)
                else:
                    logger.warning(f"Unsupported export format: {format_name}")
                    continue
                
                exported_files[format_name] = str(filepath)
                logger.info(f"Exported {format_name.upper()}: {filepath}")
                
            except Exception as e:
                logger.error(f"Failed to export {format_name}: {e}")
        
        return exported_files
    
    def _export_json(self, results: List[Dict[str, Any]], session_id: str, base_filename: str) -> Path:
        """Export results as JSON."""
        filepath = self.output_dir / f"{base_filename}.json"
        
        export_data = {
            'metadata': {
                'session_id': session_id,
                'exported_at': datetime.now().isoformat(),
                'total_documents': len(results),
                'export_format': 'json',
                'analyzer_version': '1.0.0'
            },
            'summary': self._generate_summary(results),
            'results': results
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def _export_csv(self, results: List[Dict[str, Any]], session_id: str, base_filename: str) -> Path:
        """Export results as CSV."""
        filepath = self.output_dir / f"{base_filename}.csv"
        
        # First pass: collect all possible justification keys to determine dynamic columns
        justification_keys = set()
        for result in results:
            analysis = result['analysis']
            justification_data = self._parse_justification_json(analysis.get('justification', ''))
            if justification_data:
                justification_keys.update(justification_data.keys())
        
        # Sort keys for consistent column order
        sorted_justification_keys = sorted(justification_keys)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header - restructured format (removed Category column)
            headers = [
                'Document Number',
                'Title',
                'Agency',
                'Publication Date',
                'Content Length',
                'Statutory References Count',
                'Statutory References',
                'Reform Recommendations Count',
                'Analysis Success',
                'Processing Time (s)'
            ]
            
            # Add dynamic justification columns
            headers.extend(sorted_justification_keys)
            
            writer.writerow(headers)
            
            # Write data rows
            for result in results:
                analysis = result['analysis']
                
                # Extract and format statutory references
                statutory_refs = self._extract_statutory_references(analysis)
                statutory_refs_str = self._format_statutory_references(statutory_refs)
                
                # Handle None values for reform recommendations
                reform_recs = analysis.get('reform_recommendations', [])
                reform_recs = reform_recs if reform_recs is not None else []
                
                # Handle None values for processing time
                processing_time = analysis.get('processing_time', 0)
                processing_time = processing_time if processing_time is not None else 0
                
                # Parse justification JSON
                justification_data = self._parse_justification_json(analysis.get('justification', ''))
                
                # Build base row (without Category column)
                row = [
                    result['document_number'],
                    result['title'],
                    extract_agency_name(result['agency_slug']),
                    result.get('publication_date', ''),
                    result.get('content_length', 0),
                    len(statutory_refs),
                    statutory_refs_str,
                    len(reform_recs),
                    'Yes' if analysis.get('success') else 'No',
                    f"{processing_time:.2f}"
                ]
                
                # Add justification data columns
                for key in sorted_justification_keys:
                    value = justification_data.get(key, '') if justification_data else ''
                    # Convert lists to pipe-separated strings for CSV compatibility
                    if isinstance(value, list):
                        value = '|'.join(str(item) for item in value)
                    elif value is None:
                        value = ''
                    row.append(str(value))
                
                writer.writerow(row)
        
        return filepath
    

    
    def _extract_statutory_references(self, analysis: Dict[str, Any]) -> List[str]:
        """Extract statutory references from analysis object."""
        refs = analysis.get('statutory_references', [])
        return refs if refs is not None else []
    
    def _format_statutory_references(self, statutory_refs: List[str]) -> str:
        """
        Format statutory references as pipe-separated string.
        
        Handles empty, single, and multiple statutory references cases.
        Provides proper escaping for CSV format compatibility.
        
        Args:
            statutory_refs: List of statutory reference strings
            
        Returns:
            Pipe-separated string of references, empty string if no references
        """
        if not statutory_refs:
            return ''
        
        # Clean and escape references for CSV compatibility
        cleaned_refs = []
        for ref in statutory_refs:
            if ref and isinstance(ref, str):
                # Remove any existing pipe characters to avoid conflicts
                cleaned_ref = ref.replace('|', ' ')
                # Strip whitespace
                cleaned_ref = cleaned_ref.strip()
                if cleaned_ref:
                    cleaned_refs.append(cleaned_ref)
        
        return '|'.join(cleaned_refs)
    
    def _parse_justification_json(self, justification: str) -> Optional[Dict[str, Any]]:
        """
        Parse justification field as JSON and extract keys.
        
        Args:
            justification: Justification text that may contain JSON
            
        Returns:
            Dictionary of parsed JSON data, or None if parsing fails
        """
        if not justification or not isinstance(justification, str):
            return None
        
        try:
            # Try to parse the entire justification as JSON
            return json.loads(justification)
        except json.JSONDecodeError:
            # If direct parsing fails, try to find JSON within the text
            try:
                # Look for JSON-like structures in the text
                import re
                
                # Try to find a JSON object within the text
                json_match = re.search(r'\{.*\}', justification, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    return json.loads(json_str)
                
                # Try to find a JSON array within the text
                json_array_match = re.search(r'\[.*\]', justification, re.DOTALL)
                if json_array_match:
                    json_str = json_array_match.group(0)
                    parsed = json.loads(json_str)
                    # If it's an array, convert to dict with indexed keys
                    if isinstance(parsed, list):
                        return {f"item_{i}": item for i, item in enumerate(parsed)}
                    return parsed
                
            except json.JSONDecodeError:
                pass
        
        # If all JSON parsing fails, try to extract structured data from text
        return self._extract_structured_data_from_text(justification)
    
    def _extract_structured_data_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from text using pattern matching.
        
        Args:
            text: Text to extract structured data from
            
        Returns:
            Dictionary of extracted data, or None if no structure found
        """
        if not text:
            return None
        
        extracted = {}
        
        # Common patterns to look for
        patterns = {
            'category': r'(?:CATEGORY|Category):\s*([^\n\r]+)',
            'statutory_authority': r'(?:STATUTORY AUTHORITY|Statutory Authority):\s*([^\n\r]+)',
            'legal_basis': r'(?:LEGAL BASIS|Legal Basis):\s*([^\n\r]+)',
            'justification': r'(?:JUSTIFICATION|Justification):\s*([^\n\r]+)',
            'analysis': r'(?:ANALYSIS|Analysis):\s*([^\n\r]+)',
            'recommendation': r'(?:RECOMMENDATION|Recommendation):\s*([^\n\r]+)',
            'summary': r'(?:SUMMARY|Summary):\s*([^\n\r]+)',
            'conclusion': r'(?:CONCLUSION|Conclusion):\s*([^\n\r]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                extracted[key] = match.group(1).strip()
        
        # If we found any structured data, return it
        return extracted if extracted else None
    
    def generate_agency_synopsis(self, agency_name: str) -> Dict[str, Any]:
        """
        Generate LLM-based agency synopsis using nimble-llm-caller.
        
        Args:
            agency_name: Name of the agency
            
        Returns:
            Dictionary with synopsis_text, generation_success, and error_message
        """
        synopsis_prompt = f"""
Provide a 100-word synopsis of {agency_name} including:
1. Statutory authority and legal foundation
2. Brief history and establishment
3. Informal description of its role and mission
4. Key issues and challenges in today's Washington political environment

Format as a single paragraph, exactly 100 words.

Agency: {agency_name}
"""
        
        try:
            logger.info(f"Generating agency synopsis for: {agency_name}")
            
            response_text, success, error_message = self.llm_client.analyze_document(
                content=f"Agency: {agency_name}",
                prompt=synopsis_prompt,
                document_id=f"agency_synopsis_{agency_name.replace(' ', '_')}"
            )
            
            if success and response_text:
                return {
                    'agency_name': agency_name,
                    'synopsis_text': response_text.strip(),
                    'generation_success': True,
                    'error_message': None
                }
            else:
                return {
                    'agency_name': agency_name,
                    'synopsis_text': '',
                    'generation_success': False,
                    'error_message': error_message or 'Unknown error during synopsis generation'
                }
                
        except Exception as e:
            logger.error(f"Failed to generate agency synopsis for {agency_name}: {e}")
            return {
                'agency_name': agency_name,
                'synopsis_text': '',
                'generation_success': False,
                'error_message': str(e)
            }
    
    def _export_html(self, results: List[Dict[str, Any]], session_id: str, base_filename: str) -> Path:
        """Export results as HTML report."""
        filepath = self.output_dir / f"{base_filename}.html"
        
        # Generate HTML content
        html_content = self._generate_html_report(results, session_id)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    def _generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for results."""
        if not results:
            return {}
        
        # Count by category
        categories = {}
        successful_analyses = 0
        total_processing_time = 0
        
        for result in results:
            analysis = result['analysis']
            category = analysis.get('category', 'UNKNOWN')
            categories[category] = categories.get(category, 0) + 1
            
            if analysis.get('success'):
                successful_analyses += 1
            
            total_processing_time += analysis.get('processing_time', 0)
        
        # Get agency info
        agency_slug = results[0]['agency_slug']
        agency_name = extract_agency_name(agency_slug)
        
        return {
            'agency_name': agency_name,
            'agency_slug': agency_slug,
            'total_documents': len(results),
            'successful_analyses': successful_analyses,
            'success_rate': (successful_analyses / len(results)) * 100,
            'total_processing_time': total_processing_time,
            'average_processing_time': total_processing_time / len(results),
            'category_breakdown': categories
        }
    
    def _generate_html_report(self, results: List[Dict[str, Any]], session_id: str) -> str:
        """Generate HTML report content."""
        summary = self._generate_summary(results)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CFR Document Analysis Report - {summary.get('agency_name', 'Unknown Agency')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .summary {{ background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .document {{ border: 1px solid #ddd; margin-bottom: 20px; padding: 15px; border-radius: 5px; }}
        .document h3 {{ margin-top: 0; color: #333; }}
        .category {{ font-weight: bold; padding: 3px 8px; border-radius: 3px; }}
        .category.SR {{ background-color: #ffebee; color: #c62828; }}
        .category.NSR {{ background-color: #fff3e0; color: #ef6c00; }}
        .category.NRAN {{ background-color: #e8f5e8; color: #2e7d32; }}
        .category.UNKNOWN {{ background-color: #f5f5f5; color: #666; }}
        .recommendations {{ margin-top: 10px; }}
        .recommendations ul {{ margin: 5px 0; padding-left: 20px; }}
        .justification {{ background-color: #f9f9f9; padding: 10px; border-left: 4px solid #ccc; margin-top: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f4f4f4; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>CFR Document Analysis Report</h1>
        <p><strong>Agency:</strong> {summary.get('agency_name', 'Unknown Agency')}</p>
        <p><strong>Session ID:</strong> {session_id}</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <table>
            <tr><th>Total Documents</th><td>{summary.get('total_documents', 0)}</td></tr>
            <tr><th>Successful Analyses</th><td>{summary.get('successful_analyses', 0)}</td></tr>
            <tr><th>Success Rate</th><td>{summary.get('success_rate', 0):.1f}%</td></tr>
            <tr><th>Total Processing Time</th><td>{summary.get('total_processing_time', 0):.2f}s</td></tr>
        </table>
        
        <h3>Category Breakdown</h3>
        <table>
            <tr><th>Category</th><th>Count</th><th>Description</th></tr>"""
        
        category_descriptions = {
            'SR': 'Statutorily Required',
            'NSR': 'Not Statutorily Required',
            'NRAN': 'Not Required but Agency Needs',
            'UNKNOWN': 'Analysis Incomplete'
        }
        
        for category, count in summary.get('category_breakdown', {}).items():
            description = category_descriptions.get(category, 'Unknown')
            html += f"""
            <tr>
                <td><span class="category {category}">{category}</span></td>
                <td>{count}</td>
                <td>{description}</td>
            </tr>"""
        
        html += """
        </table>
    </div>
    
    <h2>Document Analysis Details</h2>"""
        
        # Add individual document results
        for i, result in enumerate(results, 1):
            analysis = result['analysis']
            category = analysis.get('category', 'UNKNOWN')
            
            html += f"""
    <div class="document">
        <h3>{i}. {result['document_number']}</h3>
        <p><strong>Title:</strong> {result['title']}</p>
        <p><strong>Publication Date:</strong> {result.get('publication_date', 'Unknown')}</p>
        <p><strong>Category:</strong> <span class="category {category}">{category}</span></p>
        <p><strong>Analysis Success:</strong> {'Yes' if analysis.get('success') else 'No'}</p>"""
            
            if analysis.get('statutory_references'):
                html += """
        <div class="recommendations">
            <strong>Statutory References:</strong>
            <ul>"""
                for ref in analysis['statutory_references']:
                    html += f"<li>{ref}</li>"
                html += "</ul></div>"
            
            if analysis.get('reform_recommendations'):
                html += """
        <div class="recommendations">
            <strong>Reform Recommendations:</strong>
            <ul>"""
                for rec in analysis['reform_recommendations']:
                    html += f"<li>{rec}</li>"
                html += "</ul></div>"
            
            if analysis.get('justification'):
                html += f"""
        <div class="justification">
            <strong>Justification:</strong><br>
            {analysis['justification']}
        </div>"""
            
            html += "</div>"
        
        html += """
</body>
</html>"""
        
        return html
    
    def create_agency_presentation_summary(self, results: List[Dict[str, Any]], session_id: str) -> str:
        """
        Create a summary document suitable for agency staff presentation.
        
        Args:
            results: Analysis results
            session_id: Session identifier
            
        Returns:
            Path to generated summary file
        """
        if not results:
            return ""
        
        summary = self._generate_summary(results)
        timestamp = format_timestamp()
        agency_name = clean_filename(summary.get('agency_name', 'Unknown_Agency'))
        
        filename = f"agency_presentation_{agency_name}_{timestamp}.md"
        filepath = self.output_dir / filename
        
        # Generate agency synopsis
        agency_name = summary.get('agency_name', 'Unknown Agency')
        synopsis_result = self.generate_agency_synopsis(agency_name)
        
        # Generate markdown summary with synopsis
        content = f"""# CFR Document Analysis Summary
## {agency_name}

### Agency Overview
{synopsis_result['synopsis_text'] if synopsis_result['generation_success'] else "Agency overview could not be generated at this time."}

**Analysis Date:** {datetime.now().strftime('%Y-%m-%d')}  
**Session ID:** {session_id}  
**Documents Analyzed:** {summary.get('total_documents', 0)}

## Executive Summary

This analysis reviewed {summary.get('total_documents', 0)} CFR documents from {agency_name} using Department of Government Efficiency (DOGE) criteria to categorize regulations and identify reform opportunities.

### Key Findings

"""
        
        # Add category breakdown
        categories = summary.get('category_breakdown', {})
        for category, count in categories.items():
            percentage = (count / summary.get('total_documents', 1)) * 100
            category_name = {
                'SR': 'Statutorily Required',
                'NSR': 'Not Statutorily Required', 
                'NRAN': 'Not Required but Agency Needs',
                'UNKNOWN': 'Requires Further Analysis'
            }.get(category, category)
            
            content += f"- **{category_name}:** {count} documents ({percentage:.1f}%)\n"
        
        content += f"""
### Analysis Statistics

- **Success Rate:** {summary.get('success_rate', 0):.1f}%
- **Total Processing Time:** {summary.get('total_processing_time', 0):.1f} seconds
- **Average Time per Document:** {summary.get('average_processing_time', 0):.2f} seconds

## Detailed Findings

"""
        
        # Add document details
        for i, result in enumerate(results, 1):
            analysis = result['analysis']
            content += f"""### {i}. {result['document_number']}

**Title:** {result['title']}  
**Category:** {analysis.get('category', 'UNKNOWN')}  
**Publication Date:** {result.get('publication_date', 'Unknown')}

"""
            
            if analysis.get('reform_recommendations'):
                content += "**Reform Recommendations:**\n"
                for rec in analysis['reform_recommendations']:
                    content += f"- {rec}\n"
                content += "\n"
            
            if analysis.get('justification'):
                content += f"**Analysis:** {analysis['justification'][:300]}...\n\n"
        
        content += """## Next Steps

1. **Review Findings:** Agency staff should review the categorizations and recommendations
2. **Provide Feedback:** Submit corrections or additional context for any misclassified regulations
3. **Prioritize Reforms:** Identify which recommendations align with agency priorities
4. **Implementation Planning:** Develop timeline and process for implementing approved reforms

## Contact Information

For questions about this analysis or to provide feedback, please contact the regulatory reform team.

---
*Generated by CFR Document Analyzer v1.0*
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Created agency presentation summary: {filepath}")
        return str(filepath)