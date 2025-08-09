# CFR Analysis Tools

A comprehensive suite of Python tools for analyzing Federal Register documents and CFR (Code of Federal Regulations) agencies.

## Tools Overview

### 1. CFR Agency Document Counter
A Python tool for counting Federal Register documents by CFR agency using the Federal Register API.

### 2. CFR Document Analyzer
An advanced tool for analyzing CFR documents using LLM-based analysis to categorize regulations according to DOGE (Department of Government Efficiency) criteria.

#### Document Retrieval System

The CFR Document Analyzer includes a robust document retrieval system with the following features:

- **Automatic Pagination**: Retrieves all available documents without artificial limits
- **Content Fallback**: Falls back to HTML extraction when XML fails  
- **Retry Logic**: Exponential backoff for temporary failures
- **Rate Limiting**: Complies with Federal Register API guidelines
- **Comprehensive Logging**: Detailed statistics and error reporting

The system works with any Federal Register agency and provides detailed retrieval statistics including success rates and content sources.

## Overview

The CFR Agency Document Counter processes a CSV file of federal agencies and queries the Federal Register API to count how many documents each agency has published. It provides comprehensive reporting, progress tracking, and robust error handling.

## Features

- **CSV Data Processing**: Load and filter agency data from CSV files
- **Dual Data Fetching Methods**: 
  - Federal Register API integration with rate limiting and retry logic
  - Direct web scraping as fallback when API is unavailable
- **Progress Tracking**: Real-time progress updates with time estimation
- **Multiple Output Formats**: Generate reports in CSV, JSON, and human-readable summary formats
- **Comprehensive Error Handling**: Graceful degradation and detailed error reporting
- **Configurable**: Extensive command-line options and environment variable support
- **Performance Optimized**: Memory-efficient processing with rate limiting compliance

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Required Dependencies

- `requests` - HTTP client for API calls
- `pytest` - Testing framework (development)
- `responses` - HTTP mocking for tests (development)

## Quick Start

### Basic Usage

```bash
python -m cfr_agency_counter.main agencies.csv
```

This will:
1. Load agencies from `agencies.csv`
2. Query the Federal Register API for document counts
3. Generate reports in CSV, JSON, and summary formats
4. Save results to the `./results` directory

### Example CSV Format

Your agencies CSV file should have these columns:

```csv
active,cfr_citation,parent_agency_name,agency_name,description
1,12 CFR 100-199,Treasury Department,Office of the Comptroller of the Currency,Banking regulation
1,13 CFR 200-299,Small Business Administration,Small Business Administration,Small business support
0,14 CFR 300-399,Transportation Department,Federal Aviation Administration,Aviation regulation
```

## Command Line Options

### Basic Options

```bash
# Specify output directory
python -m cfr_agency_counter.main agencies.csv --output-dir ./my-reports

# Choose output formats
python -m cfr_agency_counter.main agencies.csv --format csv json

# Custom filename
python -m cfr_agency_counter.main agencies.csv --filename my_report
```

### Data Fetching Options

```bash
# Use direct web scraping instead of API (bypasses API issues)
python -m cfr_agency_counter.main agencies.csv --direct-fetch

# Use direct fetch with custom rate limiting
python -m cfr_agency_counter.main agencies.csv --direct-fetch --rate-limit 0.5
```

### API Configuration

```bash
# Adjust rate limiting (requests per second)
python -m cfr_agency_counter.main agencies.csv --rate-limit 0.5

# Set request timeout
python -m cfr_agency_counter.main agencies.csv --timeout 60

# Configure retry attempts
python -m cfr_agency_counter.main agencies.csv --max-retries 5
```

### Filtering Options

```bash
# Process only active agencies
python -m cfr_agency_counter.main agencies.csv --active-only

# Include inactive agencies
python -m cfr_agency_counter.main agencies.csv --include-inactive

# Limit processing for testing
python -m cfr_agency_counter.main agencies.csv --limit 10
```

### Progress and Logging

```bash
# Verbose logging
python -m cfr_agency_counter.main agencies.csv --verbose

# Quiet mode (no progress output)
python -m cfr_agency_counter.main agencies.csv --quiet

# Custom log file
python -m cfr_agency_counter.main agencies.csv --log-file my_log.log

# Adjust progress update frequency
python -m cfr_agency_counter.main agencies.csv --progress-interval 5
```

### Validation and Testing

```bash
# Validate configuration without processing
python -m cfr_agency_counter.main agencies.csv --validate-config

# Dry run (validate agencies and config)
python -m cfr_agency_counter.main agencies.csv --dry-run
```

## Complete Command Reference

```bash
python -m cfr_agency_counter.main [OPTIONS] AGENCIES_FILE

Arguments:
  AGENCIES_FILE         Path to the agencies CSV file

Output Options:
  --output-dir, -o DIR  Output directory for reports (default: ./results)
  --format, -f FORMAT   Output formats: csv, json, summary (default: csv json)
  --filename NAME       Base filename for reports (default: auto-generated)

API Configuration:
  --api-url URL         Federal Register API base URL
  --rate-limit FLOAT    API rate limit in requests per second (default: 1.0)
  --timeout INT         Request timeout in seconds (default: 30)
  --max-retries INT     Maximum number of retries (default: 3)

Filtering Options:
  --active-only         Process only active agencies
  --cfr-only            Process only agencies with CFR citations (default: True)
  --include-inactive    Include inactive agencies

Progress and Logging:
  --progress-interval FLOAT  Progress update interval as percentage (default: 10.0)
  --verbose, -v         Enable verbose logging
  --quiet, -q           Suppress progress output
  --log-file FILE       Log file path (default: cfr_agency_counter.log)

Validation and Testing:
  --dry-run             Validate configuration without making API calls
  --limit INT           Limit processing to first N agencies
  --validate-config     Validate configuration and exit

Help:
  --help, -h            Show help message and exit
```

## Output Formats

### CSV Report

Contains detailed information for each agency:

```csv
agency_name,agency_slug,cfr_citation,parent_agency,active,document_count,query_successful,error_message,last_updated
Office of the Comptroller of the Currency,comptroller-currency,12 CFR 100-199,Treasury Department,True,1234,True,,2025-01-08T10:30:00
Small Business Administration,small-business-administration,13 CFR 200-299,Small Business Administration,True,567,True,,2025-01-08T10:30:01
```

### JSON Report

Structured data with metadata:

```json
{
  "metadata": {
    "generated_at": "2025-01-08T10:30:00",
    "total_agencies": 2,
    "successful_queries": 2,
    "failed_queries": 0,
    "total_documents": 1801,
    "execution_time_seconds": 5.2,
    "success_rate_percent": 100.0
  },
  "agencies": [
    {
      "agency": {
        "name": "Office of the Comptroller of the Currency",
        "slug": "comptroller-currency",
        "cfr_citation": "12 CFR 100-199",
        "parent_agency": "Treasury Department",
        "active": true
      },
      "document_count": 1234,
      "query_successful": true,
      "last_updated": "2025-01-08T10:30:00"
    }
  ]
}
```

### Summary Report

Human-readable summary with statistics:

```
================================================================================
CFR AGENCY DOCUMENT COUNTER - SUMMARY REPORT
================================================================================
Generated: 2025-01-08 10:30:00
Processing completed: 2025-01-08 10:25:00

OVERALL STATISTICS
----------------------------------------
Total agencies processed: 466
Successful queries: 450
Failed queries: 16
Success rate: 96.6%
Execution time: 285.3 seconds

DOCUMENT STATISTICS
----------------------------------------
Agencies with documents: 425
Agencies without documents: 25
Total documents found: 2,847,392
Average documents per agency (with docs): 6,699.7

TOP 10 AGENCIES BY DOCUMENT COUNT
----------------------------------------
 1. Environmental Protection Agency: 234,567 documents
 2. Department of Health and Human Services: 189,234 documents
 3. Department of Transportation: 156,789 documents
...
```

## Environment Variables

You can configure the tool using environment variables:

```bash
# API settings
export FR_API_BASE_URL="https://www.federalregister.gov/api/v1"
export FR_API_RATE_LIMIT="1.0"
export REQUEST_TIMEOUT="30"
export MAX_RETRIES="3"

# Output settings
export OUTPUT_DIRECTORY="./results"

# Logging
export LOG_LEVEL="INFO"
```

## Error Handling

The tool provides comprehensive error handling:

### Common Issues and Solutions

#### 1. CSV File Not Found
```
Error: Agencies file not found: agencies.csv
```
**Solution**: Ensure the CSV file path is correct and the file exists.

#### 2. Invalid CSV Format
```
Error: Missing required columns in CSV: {'active', 'agency_name'}
```
**Solution**: Ensure your CSV has all required columns: `active`, `cfr_citation`, `parent_agency_name`, `agency_name`, `description`.

#### 3. API Rate Limiting
```
Warning: Rate limited by server, waiting 60s
```
**Solution**: The tool automatically handles rate limiting. You can adjust the rate limit with `--rate-limit`.

#### 4. Network Connectivity Issues
```
Error: Connection failed after all retries
```
**Solution**: Check your internet connection and firewall settings. The Federal Register API requires internet access.

#### 5. Permission Errors
```
Error: Cannot create output directory ./results: Permission denied
```
**Solution**: Ensure you have write permissions to the output directory or specify a different directory with `--output-dir`.

### Error Recovery

The tool implements several error recovery mechanisms:

- **Automatic Retries**: Failed API requests are automatically retried with exponential backoff
- **Graceful Degradation**: Individual agency failures don't stop the entire process
- **Partial Results**: Even if some agencies fail, results are generated for successful ones
- **Detailed Logging**: All errors are logged with context for debugging

## Performance Considerations

### Rate Limiting

The Federal Register API has rate limits. The tool defaults to 1 request per second, which is conservative and should work reliably. You can adjust this:

```bash
# More aggressive (use with caution)
python -m cfr_agency_counter.main agencies.csv --rate-limit 2.0

# More conservative (for unreliable connections)
python -m cfr_agency_counter.main agencies.csv --rate-limit 0.5
```

### Memory Usage

For large datasets (1000+ agencies), the tool uses approximately:
- 50-100 MB of RAM for processing
- Minimal disk space for output files
- Network bandwidth proportional to the number of agencies

### Processing Time

Typical processing times:
- 100 agencies: ~2-3 minutes
- 500 agencies: ~8-10 minutes  
- 1000 agencies: ~15-20 minutes

Time depends on:
- Network latency to the Federal Register API
- Rate limiting settings
- Number of retry attempts needed

## Development

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/test_models.py          # Unit tests
python -m pytest tests/test_integration.py     # Integration tests

# Run with coverage
python -m pytest --cov=cfr_agency_counter

# Verbose output
python -m pytest -v
```

### Project Structure

```
cfr_agency_counter/
├── __init__.py              # Package initialization
├── main.py                  # Main CLI script
├── config.py                # Configuration management
├── models.py                # Data models
├── data_loader.py           # CSV data loading
├── api_client.py            # Federal Register API client
├── document_counter.py      # Document counting logic
├── progress_tracker.py      # Progress tracking
├── report_generator.py      # Report generation
└── error_handler.py         # Error handling utilities

tests/
├── test_models.py           # Model tests
├── test_data_loader.py      # Data loader tests
├── test_api_client.py       # API client tests
├── test_document_counter.py # Document counter tests
├── test_progress_tracker.py # Progress tracker tests
├── test_report_generator.py # Report generator tests
├── test_error_handler.py    # Error handler tests
├── test_main.py             # Main script tests
└── test_integration.py      # Integration tests
```

## Troubleshooting

### API Rate Limiting Issues

If you encounter API rate limiting or blocking issues:

```bash
# Use direct fetch mode to bypass API issues
python -m cfr_agency_counter.main agencies.csv --direct-fetch

# Adjust rate limiting for direct fetch
python -m cfr_agency_counter.main agencies.csv --direct-fetch --rate-limit 0.5
```

**When to use direct fetch:**
- Federal Register API returns HTML instead of JSON
- API rate limiting is too restrictive
- API is temporarily unavailable
- You need more reliable data access

**Direct fetch advantages:**
- Bypasses API rate limiting issues
- More reliable access to document counts
- Uses web scraping with realistic browser headers
- Automatic fallback between search methods

**Direct fetch considerations:**
- Slower than API (requires web page parsing)
- May be less accurate for some agencies
- Respects rate limiting to avoid being blocked

### Common Issues

**"Received HTML response" error:**
```bash
# Switch to direct fetch mode
python -m cfr_agency_counter.main agencies.csv --direct-fetch
```

**Slow processing:**
```bash
# Reduce rate limit for faster processing (use carefully)
python -m cfr_agency_counter.main agencies.csv --rate-limit 2.0

# Test with limited agencies first
python -m cfr_agency_counter.main agencies.csv --limit 10
```

**Memory issues with large datasets:**
```bash
# Process in smaller batches
python -m cfr_agency_counter.main agencies.csv --limit 100
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## API Reference

The tool uses the Federal Register API v1:
- **Base URL**: https://www.federalregister.gov/api/v1
- **Documentation**: https://www.federalregister.gov/developers/api/v1
- **Rate Limits**: Approximately 1000 requests per hour per IP

### Key Endpoints Used

- `GET /documents/facets/agency` - Get document counts by agency
- `GET /agencies/{slug}` - Get agency details
- `GET /documents.json` - Search documents (for individual counts)

---

## CFR Document Analyzer

The CFR Document Analyzer provides advanced LLM-based analysis of CFR documents to categorize regulations and identify reform opportunities.

### Key Features

- **LLM-Powered Analysis**: Uses AI to analyze regulatory documents and categorize them according to DOGE criteria
- **Multiple Export Formats**: Generates results in CSV, JSON, and HTML formats
- **Agency Synopsis Generation**: Creates AI-generated agency overviews for presentation reports
- **Structured Data Extraction**: Extracts statutory references, reform recommendations, and categorizations
- **Comprehensive Testing**: Full unit and integration test coverage

### CSV Export Format

The CFR Document Analyzer exports analysis results in a restructured CSV format optimized for data analysis:

#### New CSV Structure (v2.0)
```csv
Document Number,Title,Agency,Publication Date,Content Length,Category,Statutory References Count,Statutory References,Reform Recommendations Count,Analysis Success,Processing Time (s)
2024-12345,Credit Union Capital Requirements,National Credit Union Administration,2024-01-15,2500,SR,2,12 U.S.C. 1751|12 U.S.C. 1790d,1,Yes,3.20
```

#### Key Improvements
- **Structured Statutory References**: Pipe-separated list of actual statutory citations
- **Standardized Categories**: SR (Statutorily Required), NSR (Not Statutorily Required), NRAN (Not Required but Agency Needs), UNKNOWN
- **Removed Justification Preview**: Full justification available in JSON/HTML formats
- **Enhanced Data Accessibility**: Optimized for spreadsheet applications and data analysis tools

#### Documentation
- **[CSV Format Specification](CSV_FORMAT_SPECIFICATION.md)**: Complete format documentation with examples
- **[Migration Guide](CSV_MIGRATION_GUIDE.md)**: Step-by-step guide for migrating from the old format
- **[Example Files](examples/)**: Sample CSV outputs in both old and new formats

### Agency Synopsis Feature

The analyzer now includes AI-generated agency synopses in presentation reports:

- **100-word overviews** covering statutory authority, history, role, and current issues
- **Automatic integration** into agency presentation documents
- **Graceful fallback** when LLM services are unavailable
- **Error handling** with placeholder text for failed generations

### Usage Examples

#### Basic Analysis
```bash
# Analyze documents for a specific agency
python -m cfr_document_analyzer.cli analyze --agency national-credit-union-administration --limit 10

# Export results in multiple formats
python -m cfr_document_analyzer.cli analyze --agency farm-credit-administration --format csv json html
```

#### View Results
```bash
# View analysis results
python -m cfr_document_analyzer.cli results --session session_20250807_123456

# Export specific session results
python -m cfr_document_analyzer.cli results --session session_20250807_123456 --format csv
```

### Migration from Old CSV Format

If you're upgrading from the previous CSV format:

1. **Review the [Migration Guide](CSV_MIGRATION_GUIDE.md)** for detailed instructions
2. **Update column references** to use the new structure
3. **Parse statutory references** from the pipe-separated format
4. **Use JSON/HTML exports** for full justification text
5. **Test with sample data** before processing large datasets

---

## License

This project is released under the MIT License. See LICENSE file for details.

## Support

For issues and questions:

### CFR Agency Document Counter
1. Check the troubleshooting section above
2. Review the command-line help: `python -m cfr_agency_counter.main --help`
3. Check the logs for detailed error information

### CFR Document Analyzer
1. Review the [CSV Format Specification](CSV_FORMAT_SPECIFICATION.md)
2. Check the [Migration Guide](CSV_MIGRATION_GUIDE.md) for format changes
3. Examine example files in the `examples/` directory
4. Review the command-line help: `python -m cfr_document_analyzer.cli --help`

For both tools:
- Open an issue on the project repository
- Check the logs for detailed error information

## Changelog

### Version 2.0.0 (CFR Document Analyzer)
- Restructured CSV export format with pipe-separated statutory references
- Removed Justification Preview column for cleaner data structure
- Added standardized category codes (SR, NSR, NRAN, UNKNOWN)
- Integrated LLM-based agency synopsis generation
- Comprehensive documentation and migration guides
- Full unit and integration test coverage

### Version 1.0.0 (CFR Agency Document Counter)
- Initial release
- Complete CFR agency document counting functionality
- CSV, JSON, and summary report generation
- Comprehensive error handling and logging
- Progress tracking with time estimation
- Full test coverage with integration tests