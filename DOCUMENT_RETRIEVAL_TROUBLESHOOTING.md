# Document Retrieval Troubleshooting Guide

This guide helps diagnose and fix common issues with the CFR Document Analyzer's document retrieval system.

## Common Issues and Solutions

### 1. No Documents Retrieved for Agency

**Symptoms:**
- `Retrieved 0 documents with content for [agency-name]`
- Analysis completes with no results

**Possible Causes:**
- Invalid agency slug
- Agency has no published documents
- Network connectivity issues

**Solutions:**
1. Verify the agency slug is correct:
   ```bash
   python -m cfr_document_analyzer.cli list-agencies
   ```

2. Test with a known working agency:
   ```bash
   python -m cfr_document_analyzer.cli analyze --agency national-credit-union-administration --limit 5
   ```

3. Check network connectivity:
   ```bash
   curl -I https://www.federalregister.gov/api/v1/documents.json
   ```

### 2. HTTP 404 Errors During Content Retrieval

**Symptoms:**
- `HTTP error fetching content from [URL]: 404 Client Error`
- Documents found but no content retrieved

**Possible Causes:**
- Malformed XML URLs
- Documents moved or removed from Federal Register
- URL construction errors

**Solutions:**
1. The system now automatically falls back to HTML extraction when XML fails
2. Check the logs for successful HTML fallback messages
3. If both XML and HTML fail, the document may no longer be available

### 3. Rate Limiting Issues

**Symptoms:**
- `429 Too Many Requests` errors
- Slow document retrieval
- Connection timeouts

**Solutions:**
1. The system automatically handles rate limiting with exponential backoff
2. Increase the rate limit delay in configuration:
   ```python
   FR_API_RATE_LIMIT = 2.0  # Increase from default 1.0
   ```

3. For large document sets, consider processing in smaller batches

### 4. Content Extraction Failures

**Symptoms:**
- `No content retrieved for document [number]`
- Documents with very short or empty content

**Possible Causes:**
- Document format changes
- Parsing errors
- Content validation failures

**Solutions:**
1. Check if content is too short (minimum 50 characters required)
2. Verify document URLs are accessible manually
3. Enable debug logging to see detailed extraction attempts:
   ```bash
   python -m cfr_document_analyzer.cli analyze --agency [agency] --verbose
   ```

### 5. Pagination Issues

**Symptoms:**
- Only getting first 20-100 documents
- Missing recent documents

**Solutions:**
1. The system now automatically handles pagination
2. Increase document limit if needed:
   ```bash
   python -m cfr_document_analyzer.cli analyze --agency [agency] --limit 500
   ```

3. Check logs for pagination progress messages

## Configuration Options

### Environment Variables

Set these environment variables to customize document retrieval behavior:

```bash
# Pagination settings
export CDA_DEFAULT_PAGE_SIZE=100
export CDA_MAX_PAGE_SIZE=1000

# Retry settings
export CDA_MAX_RETRY_ATTEMPTS=3
export CDA_RETRY_BASE_DELAY=1.0
export CDA_RETRY_MAX_DELAY=60.0
export CDA_RETRY_BACKOFF_FACTOR=2.0

# Content extraction settings
export CDA_ENABLE_HTML_FALLBACK=true
export CDA_CONTENT_EXTRACTION_TIMEOUT=30

# Rate limiting
export FR_API_RATE_LIMIT=1.0
```

### Logging Configuration

Enable detailed logging for troubleshooting:

```bash
export LOG_LEVEL=DEBUG
python -m cfr_document_analyzer.cli analyze --agency [agency] --verbose
```

## Monitoring Document Retrieval

### Success Rate Monitoring

The system now provides detailed statistics after each retrieval:

```
Document retrieval summary for [agency]:
  Total documents attempted: 50
  Successful retrievals: 48
  Failed retrievals: 2
  Success rate: 96.0%
```

### Content Source Tracking

Check logs to see which content sources are being used:

- `Content retrieved from xml for document [number]` - Primary XML source
- `Content retrieved from html for document [number]` - HTML fallback
- `No content retrieved for document [number]` - All sources failed

## Testing Document Retrieval

### Quick Test Script

Use the provided test script to validate retrieval:

```bash
python test_document_retrieval_fixes.py
```

### Manual Testing

Test specific agencies:

```bash
# Test with small agency
python -m cfr_document_analyzer.cli analyze --agency farm-credit-administration --limit 5

# Test with larger agency
python -m cfr_document_analyzer.cli analyze --agency national-credit-union-administration --limit 20
```

## Performance Optimization

### For Large Document Sets

1. **Use appropriate limits:**
   ```bash
   python -m cfr_document_analyzer.cli analyze --agency [agency] --limit 100
   ```

2. **Monitor memory usage** for very large document sets

3. **Consider batch processing** for agencies with thousands of documents

### Network Optimization

1. **Adjust rate limiting** based on your network capacity
2. **Use caching** to avoid re-downloading documents:
   ```python
   retriever = DocumentRetriever(database, use_cache=True)
   ```

## Getting Help

### Log Analysis

When reporting issues, include:

1. **Full command used**
2. **Complete error logs** with `--verbose` flag
3. **Agency slug** being tested
4. **Expected vs actual behavior**

### Debug Information

Enable maximum debugging:

```bash
export LOG_LEVEL=DEBUG
export CDA_ENABLE_HTML_FALLBACK=true
python -m cfr_document_analyzer.cli analyze --agency [agency] --limit 5 --verbose
```

### Common Log Messages

**Normal Operation:**
- `JSON API retrieved X total documents for [agency]`
- `Content retrieved from xml for document [number]`
- `Document retrieval summary: Success rate: X%`

**Warning Signs:**
- `No content retrieved for document [number]`
- `HTTP error fetching content from [URL]`
- `All content extraction methods failed for [number]`

**Error Conditions:**
- `JSON API failed for [agency]`
- `Error fetching documents for [agency]`
- `Failed to retrieve documents for [agency]`

## Recent Improvements

The document retrieval system has been significantly improved with:

1. **Proper pagination handling** - No more 20-document limits
2. **HTML fallback extraction** - When XML fails, try HTML
3. **Comprehensive retry logic** - Exponential backoff for temporary failures
4. **Better error classification** - Distinguish temporary vs permanent errors
5. **Enhanced logging** - Detailed statistics and debugging information
6. **Rate limit compliance** - Automatic handling of API rate limits

These improvements should resolve most common document retrieval issues.