# Design Document

## Overview

This design addresses critical issues in the CFR Document Analyzer's document retrieval system. The current implementation has three main problems: hard-coded 20-document pagination limits, HTTP 404 errors from malformed XML URLs, and lack of proper fallback mechanisms. The solution involves fixing the Federal Register API integration, implementing proper pagination, and adding robust error handling with content retrieval fallbacks.

## Architecture

### Current Issues Analysis

1. **Hard-coded pagination limit**: `per_page: min(limit or 20, 20)` caps results at 20 documents
2. **Malformed XML URLs**: Document URLs are constructed incorrectly, leading to 404 errors
3. **No pagination handling**: Only fetches first page of results
4. **Poor error handling**: Fails completely when XML retrieval fails
5. **No fallback mechanisms**: Doesn't try alternative content sources

### Proposed Architecture

```
DocumentRetriever
├── FederalRegisterAPI (new)
│   ├── search_documents()
│   ├── get_document_metadata()
│   └── handle_pagination()
├── ContentExtractor (enhanced)
│   ├── fetch_xml_content()
│   ├── fetch_html_content() (fallback)
│   └── extract_text_content()
├── URLBuilder (new)
│   ├── build_search_url()
│   ├── build_xml_url()
│   └── build_html_url()
└── RetryHandler (enhanced)
    ├── exponential_backoff()
    ├── rate_limit_handler()
    └── error_classification()
```

## Components and Interfaces

### FederalRegisterAPI Class

**Purpose**: Handle all Federal Register API interactions with proper pagination and error handling.

**Key Methods**:
- `search_documents(agency_slug, limit=None, page=1)`: Search for documents with pagination
- `get_all_documents(agency_slug, limit=None)`: Retrieve all documents across multiple pages
- `validate_response(response)`: Validate API response format and content

**Interface**:
```python
class FederalRegisterAPI:
    def __init__(self, session: requests.Session):
        self.session = session
        self.base_url = "https://www.federalregister.gov/api/v1"
    
    def search_documents(self, agency_slug: str, limit: Optional[int] = None, 
                        page: int = 1) -> Dict[str, Any]:
        """Search for documents with proper pagination."""
        
    def get_all_documents(self, agency_slug: str, limit: Optional[int] = None) -> List[Dict]:
        """Retrieve all documents handling pagination automatically."""
```

### URLBuilder Class

**Purpose**: Construct correct Federal Register URLs for different content types.

**Key Methods**:
- `build_xml_url(document_data)`: Build XML content URL from document metadata
- `build_html_url(document_data)`: Build HTML page URL as fallback
- `validate_document_number(doc_number)`: Validate document number format

**Interface**:
```python
class URLBuilder:
    @staticmethod
    def build_xml_url(document_data: Dict) -> Optional[str]:
        """Build XML URL from document metadata."""
        
    @staticmethod
    def build_html_url(document_data: Dict) -> Optional[str]:
        """Build HTML URL as fallback."""
```

### ContentExtractor Class (Enhanced)

**Purpose**: Extract document content with multiple fallback methods.

**Key Methods**:
- `extract_content(document_data)`: Main extraction method with fallbacks
- `extract_from_xml(xml_url)`: Extract from XML (primary method)
- `extract_from_html(html_url)`: Extract from HTML (fallback)
- `clean_and_validate_content(content)`: Clean and validate extracted content

**Interface**:
```python
class ContentExtractor:
    def __init__(self, session: requests.Session, retry_handler: RetryHandler):
        self.session = session
        self.retry_handler = retry_handler
    
    def extract_content(self, document_data: Dict) -> Optional[str]:
        """Extract content with fallback methods."""
```

### RetryHandler Class (Enhanced)

**Purpose**: Handle retries, rate limiting, and error classification.

**Key Methods**:
- `execute_with_retry(func, *args, **kwargs)`: Execute function with retry logic
- `handle_rate_limit(response)`: Handle rate limit responses
- `classify_error(exception)`: Classify errors as temporary or permanent

## Data Models

### DocumentMetadata (Enhanced)

```python
@dataclass
class DocumentMetadata:
    document_number: str
    title: str
    publication_date: str
    agency_slug: str
    xml_url: Optional[str] = None
    html_url: Optional[str] = None
    pdf_url: Optional[str] = None
    cfr_references: List[str] = field(default_factory=list)
    document_type: Optional[str] = None
    retrieval_attempts: int = 0
    last_error: Optional[str] = None
```

### RetrievalResult

```python
@dataclass
class RetrievalResult:
    success: bool
    content: Optional[str] = None
    content_source: Optional[str] = None  # 'xml', 'html', 'cached'
    error_message: Optional[str] = None
    attempts_made: int = 0
    retrieval_time: float = 0.0
```

### PaginationState

```python
@dataclass
class PaginationState:
    current_page: int = 1
    total_pages: Optional[int] = None
    documents_per_page: int = 20
    total_documents: Optional[int] = None
    has_more: bool = True
```

## Error Handling

### Error Classification

1. **Temporary Errors** (retry with backoff):
   - Network timeouts
   - HTTP 5xx errors
   - Rate limit responses (429)
   - Connection errors

2. **Permanent Errors** (skip and continue):
   - HTTP 404 (document not found)
   - HTTP 403 (forbidden)
   - Malformed document numbers
   - Invalid response format

3. **Critical Errors** (stop processing):
   - Authentication failures (if implemented later)
   - API endpoint changes
   - Persistent network failures

### Retry Strategy

```python
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
```

### Fallback Chain

1. **Primary**: Federal Register XML API
2. **Secondary**: Federal Register HTML scraping
3. **Tertiary**: Document page text extraction
4. **Final**: Mark as failed, continue processing

## Testing Strategy

### Unit Tests

1. **URLBuilder Tests**:
   - Test correct XML URL construction
   - Test HTML URL fallback construction
   - Test document number validation

2. **ContentExtractor Tests**:
   - Test XML content extraction
   - Test HTML content extraction
   - Test content cleaning and validation

3. **RetryHandler Tests**:
   - Test exponential backoff logic
   - Test error classification
   - Test rate limit handling

### Integration Tests

1. **API Integration**:
   - Test real Federal Register API calls
   - Test pagination handling
   - Test rate limit compliance

2. **End-to-End Tests**:
   - Test complete document retrieval workflow
   - Test error recovery scenarios
   - Test large document set processing

### Error Scenario Tests

1. **Network Failure Tests**:
   - Test timeout handling
   - Test connection error recovery
   - Test partial failure scenarios

2. **API Error Tests**:
   - Test 404 error handling
   - Test rate limit responses
   - Test malformed response handling

## Implementation Approach

### Phase 1: Fix Core Issues

1. Remove hard-coded 20-document limit
2. Fix XML URL construction
3. Implement proper pagination
4. Add basic error handling

### Phase 2: Add Fallback Mechanisms

1. Implement HTML content extraction
2. Add retry logic with exponential backoff
3. Implement rate limit handling
4. Add comprehensive logging

### Phase 3: Optimization and Monitoring

1. Add performance monitoring
2. Implement caching improvements
3. Add diagnostic tools
4. Optimize for large document sets

## Configuration Changes

### New Configuration Options

```python
class DocumentRetrievalConfig:
    # Pagination settings
    DEFAULT_PAGE_SIZE: int = 100  # Increased from 20
    MAX_PAGE_SIZE: int = 1000
    
    # Retry settings
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_BASE_DELAY: float = 1.0
    RETRY_MAX_DELAY: float = 60.0
    
    # Content extraction settings
    ENABLE_HTML_FALLBACK: bool = True
    CONTENT_EXTRACTION_TIMEOUT: int = 30
    
    # Rate limiting
    REQUESTS_PER_SECOND: float = 2.0
    BURST_LIMIT: int = 10
```

## Monitoring and Diagnostics

### Metrics to Track

1. **Retrieval Success Rate**: Percentage of successful document retrievals
2. **Content Source Distribution**: XML vs HTML vs failed retrievals
3. **Error Rate by Type**: 404s, timeouts, rate limits, etc.
4. **Average Retrieval Time**: Performance monitoring
5. **Pagination Efficiency**: Documents retrieved per API call

### Logging Enhancements

1. **Structured Logging**: JSON format for better parsing
2. **Request/Response Logging**: Full HTTP details for debugging
3. **Performance Logging**: Timing information for optimization
4. **Error Context**: Detailed error information with stack traces

This design addresses all the identified issues while maintaining compatibility with the existing system and providing a robust foundation for reliable document retrieval.