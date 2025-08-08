# Design Document

## Overview

The CFR Agency Document Counter is a Python script that retrieves document counts for all 466 agencies listed in the Code of Federal Regulations. The script leverages the Federal Register API to query document counts for each agency and generates comprehensive reports in multiple formats.

Based on research of the Federal Register API structure and the agencies.csv data file, the system will:

1. Extract active agencies from the Federal Register agencies dataset
2. Use the Federal Register API's facet endpoint to get document counts by agency
3. Cross-reference with CFR citation data to ensure all 466 CFR agencies are covered
4. Generate detailed reports with document counts and metadata

## Architecture

The system follows a modular architecture with clear separation of concerns:

```
CFR Agency Document Counter
├── Data Layer
│   ├── Agency Data Loader
│   ├── API Client
│   └── Results Storage
├── Processing Layer
│   ├── Agency Filter
│   ├── Document Counter
│   └── Progress Tracker
└── Output Layer
    ├── Report Generator
    ├── CSV Exporter
    └── JSON Exporter
```

### Key Design Decisions

1. **API Strategy**: Use the Federal Register API's `/documents/facets/agency` endpoint to get bulk document counts rather than individual agency queries for efficiency
2. **Data Source**: Parse the agencies.csv file to identify all agencies with CFR citations, filtering for active agencies
3. **Rate Limiting**: Implement exponential backoff and respect API rate limits to ensure reliable operation
4. **Error Handling**: Graceful degradation with detailed logging for failed queries

## Components and Interfaces

### 1. Agency Data Loader
**Purpose**: Load and parse agency information from the Federal Register dataset

**Interface**:
```python
class AgencyDataLoader:
    def load_agencies(self, file_path: str) -> List[Agency]
    def filter_cfr_agencies(self, agencies: List[Agency]) -> List[Agency]
    def get_active_agencies(self, agencies: List[Agency]) -> List[Agency]
```

**Key Functionality**:
- Parse agencies.csv file
- Filter for agencies with CFR citations (cfr_citation field populated)
- Identify active agencies (active=1)
- Extract agency slugs for API queries

### 2. Federal Register API Client
**Purpose**: Interface with the Federal Register API to retrieve document counts

**Interface**:
```python
class FederalRegisterClient:
    def __init__(self, base_url: str, rate_limit: float)
    def get_agency_document_counts(self) -> Dict[str, int]
    def get_agency_details(self, agency_slug: str) -> Dict
    def _make_request(self, endpoint: str, params: Dict) -> Dict
```

**Key Functionality**:
- Query `/documents/facets/agency` endpoint for bulk document counts
- Implement retry logic with exponential backoff
- Handle API rate limiting (default: 1 request per second)
- Parse JSON responses and extract count data

### 3. Document Counter
**Purpose**: Process API responses and match agencies with document counts

**Interface**:
```python
class DocumentCounter:
    def __init__(self, api_client: FederalRegisterClient)
    def count_documents_by_agency(self, agencies: List[Agency]) -> Dict[str, AgencyDocumentCount]
    def handle_missing_agencies(self, agencies: List[Agency], api_results: Dict) -> List[str]
```

**Key Functionality**:
- Match agency slugs from CSV with API response data
- Handle agencies with zero documents
- Identify agencies missing from API results
- Generate comprehensive count mapping

### 4. Progress Tracker
**Purpose**: Provide user feedback during long-running operations

**Interface**:
```python
class ProgressTracker:
    def __init__(self, total_items: int)
    def update(self, current: int, message: str = "")
    def complete(self, summary: str)
```

### 5. Report Generator
**Purpose**: Generate formatted reports with document counts and metadata

**Interface**:
```python
class ReportGenerator:
    def generate_csv_report(self, results: Dict, output_path: str)
    def generate_json_report(self, results: Dict, output_path: str)
    def generate_summary_report(self, results: Dict) -> str
```

## Data Models

### Agency
```python
@dataclass
class Agency:
    name: str
    slug: str
    cfr_citation: str
    parent_agency: str
    active: bool
    description: str
```

### AgencyDocumentCount
```python
@dataclass
class AgencyDocumentCount:
    agency: Agency
    document_count: int
    last_updated: datetime
    query_successful: bool
    error_message: Optional[str] = None
```

### CountingResults
```python
@dataclass
class CountingResults:
    total_agencies: int
    successful_queries: int
    failed_queries: int
    agencies_with_documents: int
    agencies_without_documents: int
    total_documents: int
    execution_time: float
    timestamp: datetime
    results: List[AgencyDocumentCount]
```

## Error Handling

### API Error Handling
- **Rate Limiting**: Implement exponential backoff starting at 1 second, max 60 seconds
- **Network Errors**: Retry up to 3 times with increasing delays
- **HTTP Errors**: Log specific error codes and continue processing other agencies
- **Timeout Handling**: 30-second timeout per request with graceful fallback

### Data Processing Errors
- **Missing Agency Data**: Log warning and continue with available data
- **Invalid CSV Format**: Validate headers and data types, fail fast with clear error message
- **File I/O Errors**: Handle permission issues and disk space problems

### Recovery Strategies
- **Partial Results**: Save intermediate results to allow resume functionality
- **Graceful Degradation**: Continue processing even if some agencies fail
- **Detailed Logging**: Comprehensive logs for debugging and monitoring

## Testing Strategy

### Unit Tests
- **Agency Data Loader**: Test CSV parsing, filtering logic, and edge cases
- **API Client**: Mock API responses, test rate limiting and retry logic
- **Document Counter**: Test matching algorithms and error handling
- **Report Generator**: Validate output formats and data integrity

### Integration Tests
- **End-to-End Flow**: Test complete pipeline with sample data
- **API Integration**: Test against Federal Register API sandbox/staging
- **File Operations**: Test CSV/JSON generation with various data sets

### Performance Tests
- **Load Testing**: Simulate processing all 466 agencies
- **Memory Usage**: Monitor memory consumption during large data processing
- **API Rate Limiting**: Verify compliance with API rate limits

### Error Scenario Tests
- **Network Failures**: Test behavior with intermittent connectivity
- **Invalid Data**: Test handling of malformed CSV or API responses
- **Partial Failures**: Test recovery when some agencies fail to process

## Configuration

The script will support configuration through command-line arguments and environment variables:

### Command Line Options
```bash
python cfr_agency_counter.py \
  --agencies-file agencies.csv \
  --output-format csv,json \
  --output-dir ./results \
  --rate-limit 1.0 \
  --max-retries 3 \
  --verbose
```

### Environment Variables
- `FR_API_BASE_URL`: Federal Register API base URL (default: https://www.federalregister.gov/api/v1)
- `FR_API_RATE_LIMIT`: Requests per second (default: 1.0)
- `OUTPUT_DIRECTORY`: Default output directory
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)

## Output Formats

### CSV Format
```csv
agency_name,agency_slug,cfr_citation,parent_agency,document_count,last_updated,query_status
"Agriculture Department","agriculture-department","07 CFR 0-26, 3000-3099","",1234,"2025-01-08T10:30:00Z","success"
```

### JSON Format
```json
{
  "metadata": {
    "total_agencies": 466,
    "successful_queries": 465,
    "failed_queries": 1,
    "execution_time": 120.5,
    "timestamp": "2025-01-08T10:30:00Z"
  },
  "results": [
    {
      "agency_name": "Agriculture Department",
      "agency_slug": "agriculture-department",
      "cfr_citation": "07 CFR 0-26, 3000-3099",
      "parent_agency": "",
      "document_count": 1234,
      "last_updated": "2025-01-08T10:30:00Z",
      "query_status": "success"
    }
  ]
}
```

## Performance Considerations

### API Rate Limiting
- Default rate limit: 1 request per second
- Configurable rate limiting to respect API terms
- Exponential backoff for rate limit violations

### Memory Management
- Stream processing for large datasets
- Lazy loading of agency data
- Garbage collection of processed results

### Execution Time
- Estimated runtime: 8-10 minutes for all 466 agencies (with 1 req/sec rate limit)
- Progress indicators every 10% completion
- Option to process subset of agencies for testing

## Security Considerations

### API Security
- No authentication required for Federal Register API
- HTTPS-only communication
- Input validation for all API parameters

### Data Handling
- No sensitive data processing
- Public domain government data only
- Secure file handling for output generation