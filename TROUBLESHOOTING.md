# CFR Agency Document Counter - Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the CFR Agency Document Counter.

## Quick Diagnostics

### 1. Check System Requirements

```bash
# Check Python version (requires 3.8+)
python --version

# Check if required packages are installed
pip list | grep -E "(requests|pytest)"

# Test basic functionality
python -c "import requests; print('Requests working')"
```

### 2. Validate Configuration

```bash
# Test configuration validation
python -m cfr_agency_counter.main agencies.csv --validate-config

# Test with dry run
python -m cfr_agency_counter.main agencies.csv --dry-run --limit 1
```

### 3. Test API Connectivity

```bash
# Test Federal Register API directly
curl -s "https://www.federalregister.gov/api/v1/agencies" | head -100
```

## Common Issues and Solutions

### File and Path Issues

#### Issue: "Agencies file not found"
```
Error: Agencies file not found: agencies.csv
```

**Causes:**
- File doesn't exist
- Incorrect file path
- Permission issues

**Solutions:**
```bash
# Check if file exists
ls -la agencies.csv

# Use absolute path
python -m cfr_agency_counter.main /full/path/to/agencies.csv

# Check permissions
chmod 644 agencies.csv
```

#### Issue: "Cannot create output directory"
```
Error: Cannot create output directory ./results: Permission denied
```

**Solutions:**
```bash
# Check current directory permissions
ls -la .

# Create directory manually
mkdir -p ./results
chmod 755 ./results

# Use different output directory
python -m cfr_agency_counter.main agencies.csv --output-dir ~/reports
```

### CSV Format Issues

#### Issue: "Missing required columns in CSV"
```
Error: Missing required columns in CSV: {'active', 'agency_name'}
```

**Required columns:**
- `active` - 1 for active, 0 for inactive
- `cfr_citation` - CFR citation (e.g., "12 CFR 100-199")
- `parent_agency_name` - Parent agency name
- `agency_name` - Agency name
- `description` - Agency description

**Solutions:**
```bash
# Check CSV headers
head -1 agencies.csv

# Validate CSV format
python -c "
import csv
with open('agencies.csv', 'r') as f:
    reader = csv.DictReader(f)
    print('Headers:', reader.fieldnames)
    print('First row:', next(reader))
"
```

#### Issue: "Invalid active status"
```
Warning: Skipping invalid row 5: Invalid active status: yes
```

**Solution:** Ensure `active` column contains only `0` or `1`:
```csv
active,cfr_citation,parent_agency_name,agency_name,description
1,12 CFR 100-199,Treasury,Test Agency,Description
0,13 CFR 200-299,Commerce,Inactive Agency,Description
```

### API Connection Issues

#### Issue: "Received HTML response - API may be rate limiting or blocking requests"
```
Error: Received HTML response - API may be rate limiting or blocking requests
```

**Causes:**
- Federal Register API is rate limiting your IP
- API is returning HTML error pages instead of JSON
- User agent is being blocked
- API endpoint has changed

**Solutions:**
```bash
# RECOMMENDED: Use direct fetch mode to bypass API issues
python -m cfr_agency_counter.main agencies.csv --direct-fetch

# Use direct fetch with custom rate limiting
python -m cfr_agency_counter.main agencies.csv --direct-fetch --rate-limit 0.5

# Test with a single agency first
python -m cfr_agency_counter.main agencies.csv --direct-fetch --limit 1 --verbose
```

#### Issue: "Connection failed after all retries"
```
Error: Connection failed after all retries
```

**Causes:**
- No internet connection
- Firewall blocking requests
- Federal Register API is down
- DNS resolution issues

**Solutions:**
```bash
# Test internet connectivity
ping google.com

# Test Federal Register API
curl -I https://www.federalregister.gov/api/v1/agencies

# Check DNS resolution
nslookup www.federalregister.gov

# Try direct fetch mode as alternative
python -m cfr_agency_counter.main agencies.csv --direct-fetch

# Use more conservative settings
python -m cfr_agency_counter.main agencies.csv \
  --rate-limit 0.5 \
  --timeout 120 \
  --max-retries 5
```

#### Issue: "Rate limited by server"
```
Warning: Rate limited by server, waiting 60s
```

**Solutions:**
```bash
# Reduce rate limit
python -m cfr_agency_counter.main agencies.csv --rate-limit 0.5

# Use more conservative settings
python -m cfr_agency_counter.main agencies.csv \
  --rate-limit 0.3 \
  --timeout 90
```

#### Issue: "Request timed out"
```
Error: Request timed out after all retries
```

**Solutions:**
```bash
# Increase timeout
python -m cfr_agency_counter.main agencies.csv --timeout 60

# Reduce rate limit and increase timeout
python -m cfr_agency_counter.main agencies.csv \
  --rate-limit 0.5 \
  --timeout 90 \
  --max-retries 5
```

### Memory and Performance Issues

#### Issue: High memory usage
```
Warning: High memory usage detected
```

**Solutions:**
```bash
# Process in smaller batches
python -m cfr_agency_counter.main agencies.csv --limit 100

# Use only essential output formats
python -m cfr_agency_counter.main agencies.csv --format csv

# Monitor memory usage
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"
```

#### Issue: Slow processing
```
Processing is taking too long
```

**Causes:**
- Network latency
- Conservative rate limiting
- Large dataset
- API response delays

**Solutions:**
```bash
# Try direct fetch mode (may be faster for some cases)
python -m cfr_agency_counter.main agencies.csv --direct-fetch --rate-limit 1.0

# Increase rate limit (carefully)
python -m cfr_agency_counter.main agencies.csv --rate-limit 1.5

# Reduce timeout for faster failure detection
python -m cfr_agency_counter.main agencies.csv --timeout 30

# Process subset for testing
python -m cfr_agency_counter.main agencies.csv --limit 50
```

### Output and Report Issues

#### Issue: "Failed to write CSV report"
```
Error: Failed to write CSV report to ./results/report.csv: Permission denied
```

**Solutions:**
```bash
# Check output directory permissions
ls -la ./results/

# Change permissions
chmod 755 ./results/

# Use different output directory
python -m cfr_agency_counter.main agencies.csv --output-dir ~/reports
```

#### Issue: Empty or incomplete reports
```
Warning: Some agencies returned zero documents
```

**This is often normal behavior. Check:**
```bash
# Review summary report for details
cat results/*_summary.txt

# Check for failed queries in CSV
grep "False" results/*.csv

# Review logs for specific errors
tail -50 cfr_agency_counter.log
```

### Configuration Issues

#### Issue: "Invalid rate limit"
```
Error: Rate limit must be positive
```

**Solution:**
```bash
# Use positive rate limit
python -m cfr_agency_counter.main agencies.csv --rate-limit 1.0
```

#### Issue: "Cannot specify both --verbose and --quiet"
```
Error: Cannot specify both --verbose and --quiet
```

**Solution:**
```bash
# Use only one logging option
python -m cfr_agency_counter.main agencies.csv --verbose
# OR
python -m cfr_agency_counter.main agencies.csv --quiet
```

## Advanced Troubleshooting

### Enable Debug Logging

```bash
# Maximum verbosity
python -m cfr_agency_counter.main agencies.csv \
  --verbose \
  --log-file debug.log \
  --limit 5

# Check debug log
tail -f debug.log
```

### Network Debugging

```bash
# Test with curl
curl -v "https://www.federalregister.gov/api/v1/documents/facets/agency"

# Check proxy settings
echo $HTTP_PROXY
echo $HTTPS_PROXY

# Test without proxy
unset HTTP_PROXY HTTPS_PROXY
python -m cfr_agency_counter.main agencies.csv --limit 1
```

### Python Environment Issues

```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Check installed packages
pip list

# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Create clean virtual environment
python -m venv clean_env
source clean_env/bin/activate  # On Windows: clean_env\Scripts\activate
pip install -r requirements.txt
```

### System Resource Monitoring

```bash
# Monitor during processing
# Terminal 1: Run the tool
python -m cfr_agency_counter.main agencies.csv --verbose

# Terminal 2: Monitor resources
watch -n 5 'ps aux | grep python; free -h; df -h'
```

## Error Code Reference

| Exit Code | Meaning | Common Causes |
|-----------|---------|---------------|
| 0 | Success | Normal completion |
| 1 | General error | Configuration, file, or processing error |
| 130 | Interrupted | User pressed Ctrl+C |

## Log Analysis

### Understanding Log Levels

```bash
# Filter by log level
grep "ERROR" cfr_agency_counter.log
grep "WARNING" cfr_agency_counter.log
grep "INFO" cfr_agency_counter.log
```

### Common Log Messages

#### Normal Operation
```
INFO - CFR Agency Document Counter starting
INFO - Loaded 466 agencies from agencies.csv
INFO - Filtered to 450 agencies with CFR citations
INFO - API client configured: https://www.federalregister.gov/api/v1, rate limit: 1.0/s
INFO - Starting document counting for 450 agencies
INFO - Document counting completed successfully
```

#### Warning Messages
```
WARNING - Rate limited by server, waiting 60s
WARNING - Agency not found in Federal Register API: test-agency
WARNING - Invalid count for agency test-agency: -1
```

#### Error Messages
```
ERROR - Failed to retrieve document counts from API: Connection timeout
ERROR - Failed to load agencies: Missing required columns
ERROR - Failed to write CSV report: Permission denied
```

## Performance Tuning

### For Slow Networks
```bash
python -m cfr_agency_counter.main agencies.csv \
  --rate-limit 0.3 \
  --timeout 120 \
  --max-retries 5 \
  --progress-interval 5.0
```

### For Fast Networks
```bash
python -m cfr_agency_counter.main agencies.csv \
  --rate-limit 2.0 \
  --timeout 30 \
  --max-retries 2
```

### For Large Datasets
```bash
python -m cfr_agency_counter.main agencies.csv \
  --rate-limit 1.0 \
  --format csv \
  --progress-interval 2.0 \
  --quiet
```

## Getting Help

### 1. Check Built-in Help
```bash
python -m cfr_agency_counter.main --help
```

### 2. Run Diagnostics
```bash
# System info
python -c "
import sys, platform
print(f'Python: {sys.version}')
print(f'Platform: {platform.platform()}')
print(f'Architecture: {platform.architecture()}')
"

# Package versions
pip show requests pytest responses
```

### 3. Create Minimal Test Case
```bash
# Create minimal test CSV
echo "active,cfr_citation,parent_agency_name,agency_name,description" > test.csv
echo "1,12 CFR 100-199,Treasury,Test Agency,Test description" >> test.csv

# Test with minimal data
python -m cfr_agency_counter.main test.csv --limit 1 --verbose
```

### 4. Collect Debug Information

When reporting issues, include:

1. **Command used:**
   ```bash
   python -m cfr_agency_counter.main agencies.csv --verbose
   ```

2. **Error message:**
   ```
   Complete error message from terminal
   ```

3. **Log file contents:**
   ```bash
   tail -50 cfr_agency_counter.log
   ```

4. **System information:**
   ```bash
   python --version
   pip list | grep -E "(requests|pytest|responses)"
   ```

5. **Sample CSV (first few lines):**
   ```bash
   head -5 agencies.csv
   ```

This information helps diagnose issues quickly and accurately.