# Implementation Plan

- [x] 1. Fix hard-coded pagination limit in document retrieval
  - Remove the `min(limit or 20, 20)` constraint in `_fetch_documents_from_web` method
  - Update the `per_page` parameter to use the actual limit or a higher default (100)
  - Modify the JSON API fallback to also respect the proper limit
  - Test with agencies that have more than 20 documents
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Implement proper pagination handling for complete document retrieval
  - Add pagination logic to `_fetch_documents_from_web` method to handle multiple pages
  - Create a loop to fetch all pages until no more results are available
  - Update progress logging to show pagination progress
  - Implement proper handling of Federal Register API pagination metadata
  - _Requirements: 1.4, 1.5_

- [x] 3. Create URLBuilder class for correct Federal Register URL construction
  - Create new `URLBuilder` class with static methods for URL construction
  - Implement `build_xml_url` method that correctly formats Federal Register XML URLs
  - Add `build_html_url` method for fallback HTML document URLs
  - Add `validate_document_number` method to check document number format
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 4. Fix XML URL construction and document number parsing
  - Update `_extract_document_info_from_element` to use URLBuilder for correct URL construction
  - Fix the document number extraction regex patterns to handle all Federal Register formats
  - Implement proper date-based URL construction for XML documents
  - Add validation of constructed URLs before making requests
  - _Requirements: 4.1, 4.2, 4.4_

- [x] 5. Implement HTML content extraction as fallback mechanism
  - Create `ContentExtractor` class with multiple extraction methods
  - Implement `extract_from_html` method to scrape document content from HTML pages
  - Add text cleaning and formatting for HTML-extracted content
  - Integrate HTML fallback into the main content retrieval workflow
  - _Requirements: 2.2, 2.3_

- [x] 6. Add comprehensive retry logic with exponential backoff
  - Create `RetryHandler` class with configurable retry parameters
  - Implement exponential backoff with jitter for failed requests
  - Add error classification to determine which errors should be retried
  - Integrate retry logic into both XML and HTML content retrieval
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 7. Enhance error handling and logging for better diagnostics
  - Add detailed logging for each document retrieval attempt with URL and response details
  - Implement structured error logging with error types and context
  - Add summary statistics logging for successful vs failed retrievals
  - Create diagnostic information for troubleshooting common issues
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 8. Implement rate limiting and API compliance
  - Add proper rate limiting between Federal Register API requests
  - Implement automatic rate limit detection and backoff from API responses
  - Add configurable delays between requests to respect API guidelines
  - Update request headers with appropriate user agent and accept headers
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 9. Update DocumentRetriever to use new components and fix main workflow
  - Refactor `get_agency_documents` method to use new URLBuilder and ContentExtractor
  - Update `_create_document_with_content` to handle multiple content sources
  - Integrate the new retry and error handling mechanisms
  - Ensure backward compatibility with existing database and caching
  - _Requirements: 2.1, 2.4, 3.4_

- [x] 10. Add comprehensive testing for document retrieval fixes
  - Create unit tests for URLBuilder class with various document number formats
  - Add integration tests for ContentExtractor with real Federal Register URLs
  - Test pagination handling with agencies that have many documents
  - Create error scenario tests for network failures and API errors
  - _Requirements: All requirements - testing coverage_

- [x] 11. Test fixes with problematic agencies and validate results
  - Test with Bureau of Engraving and Printing (the failing agency from logs)
  - Verify that documents are successfully retrieved and contain actual content
  - Test with agencies that have more than 20 documents to verify pagination
  - Validate that error handling works gracefully for unavailable documents
  - _Requirements: Integration testing and validation_

- [x] 12. Update configuration and documentation for new retrieval system
  - Add new configuration options for pagination, retry, and rate limiting
  - Update documentation to reflect the improved retrieval capabilities
  - Add troubleshooting guide for common document retrieval issues
  - Create monitoring guidelines for tracking retrieval success rates
  - _Requirements: 5.5, 6.5_