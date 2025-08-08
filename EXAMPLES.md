# CFR Agency Document Counter - Usage Examples

This document provides practical examples of using the CFR Agency Document Counter for various scenarios.

## Basic Examples

### 1. Simple Document Count

Count documents for all active CFR agencies:

```bash
python -m cfr_agency_counter.main agencies.csv
```

**Output**: Creates CSV, JSON, and summary reports in `./results/`

### 2. Custom Output Directory

Save reports to a specific directory:

```bash
python -m cfr_agency_counter.main agencies.csv --output-dir /path/to/reports
```

### 3. Specific Output Format

Generate only CSV reports:

```bash
python -m cfr_agency_counter.main agencies.csv --format csv
```

Generate multiple specific formats:

```bash
python -m cfr_agency_counter.main agencies.csv --format csv summary
```

## Filtering Examples

### 4. Active Agencies Only

Process only agencies marked as active:

```bash
python -m cfr_agency_counter.main agencies.csv --active-only
```

### 5. Include Inactive Agencies

Process both active and inactive agencies:

```bash
python -m cfr_agency_counter.main agencies.csv --include-inactive
```

### 6. Limited Processing for Testing

Process only the first 10 agencies (useful for testing):

```bash
python -m cfr_agency_counter.main agencies.csv --limit 10
```

## API Configuration Examples

### 7. Conservative Rate Limiting

Use slower rate limiting for unreliable connections:

```bash
python -m cfr_agency_counter.main agencies.csv --rate-limit 0.5 --timeout 60
```

### 8. Aggressive Processing

Use faster rate limiting (use with caution):

```bash
python -m cfr_agency_counter.main agencies.csv --rate-limit 2.0 --max-retries 5
```

### 9. Custom API Configuration

Configure all API settings:

```bash
python -m cfr_agency_counter.main agencies.csv \
  --api-url "https://www.federalregister.gov/api/v1" \
  --rate-limit 1.0 \
  --timeout 45 \
  --max-retries 3
```

## Logging and Progress Examples

### 10. Verbose Logging

Enable detailed logging for debugging:

```bash
python -m cfr_agency_counter.main agencies.csv --verbose
```

### 11. Quiet Mode

Suppress progress output (useful for scripts):

```bash
python -m cfr_agency_counter.main agencies.csv --quiet
```

### 12. Custom Log File

Save logs to a specific file:

```bash
python -m cfr_agency_counter.main agencies.csv --log-file processing.log
```

### 13. Frequent Progress Updates

Get progress updates every 5%:

```bash
python -m cfr_agency_counter.main agencies.csv --progress-interval 5.0
```

## Validation Examples

### 14. Configuration Validation

Validate configuration without processing:

```bash
python -m cfr_agency_counter.main agencies.csv --validate-config
```

### 15. Dry Run

Validate agencies and configuration without API calls:

```bash
python -m cfr_agency_counter.main agencies.csv --dry-run
```

## Advanced Examples

### 16. Complete Custom Configuration

Full example with all options:

```bash
python -m cfr_agency_counter.main agencies.csv \
  --output-dir ./custom-reports \
  --format csv json summary \
  --filename "cfr_analysis_2025" \
  --rate-limit 1.5 \
  --timeout 60 \
  --max-retries 5 \
  --active-only \
  --progress-interval 5.0 \
  --verbose \
  --log-file detailed.log
```

### 17. Production Processing

Recommended settings for production use:

```bash
python -m cfr_agency_counter.main agencies.csv \
  --output-dir ./production-reports \
  --rate-limit 1.0 \
  --timeout 60 \
  --max-retries 3 \
  --log-file production.log \
  --progress-interval 10.0
```

### 18. Development/Testing

Settings for development and testing:

```bash
python -m cfr_agency_counter.main agencies.csv \
  --limit 20 \
  --verbose \
  --rate-limit 2.0 \
  --output-dir ./test-results \
  --format summary
```

## Environment Variable Examples

### 19. Using Environment Variables

Set configuration via environment variables:

```bash
# Set environment variables
export FR_API_RATE_LIMIT="0.8"
export REQUEST_TIMEOUT="45"
export OUTPUT_DIRECTORY="./env-reports"
export LOG_LEVEL="DEBUG"

# Run with environment configuration
python -m cfr_agency_counter.main agencies.csv
```

### 20. Mixed Configuration

Combine environment variables with command-line options:

```bash
# Environment variables for API settings
export FR_API_RATE_LIMIT="1.0"
export REQUEST_TIMEOUT="60"

# Command-line options for output settings
python -m cfr_agency_counter.main agencies.csv \
  --output-dir ./mixed-config \
  --format json \
  --verbose
```

## Batch Processing Examples

### 21. Multiple Agency Files

Process multiple agency files in sequence:

```bash
#!/bin/bash
for file in agencies_*.csv; do
    echo "Processing $file..."
    python -m cfr_agency_counter.main "$file" \
      --output-dir "./results/$(basename "$file" .csv)" \
      --quiet \
      --log-file "processing_$(basename "$file" .csv).log"
done
```

### 22. Scheduled Processing

Example cron job for daily processing:

```bash
# Add to crontab (crontab -e)
# Run daily at 2 AM
0 2 * * * /usr/bin/python3 -m cfr_agency_counter.main /path/to/agencies.csv --output-dir /path/to/daily-reports --quiet --log-file /path/to/logs/daily.log
```

## Error Handling Examples

### 23. Robust Processing with Error Recovery

Configure for maximum reliability:

```bash
python -m cfr_agency_counter.main agencies.csv \
  --rate-limit 0.5 \
  --timeout 90 \
  --max-retries 5 \
  --log-file robust.log \
  --verbose
```

### 24. Quick Failure Detection

Configure for fast failure detection:

```bash
python -m cfr_agency_counter.main agencies.csv \
  --timeout 15 \
  --max-retries 1 \
  --rate-limit 2.0
```

## Output Analysis Examples

### 25. Analyzing Results

After processing, analyze the results:

```bash
# Count successful vs failed agencies
python -c "
import json
with open('./results/cfr_agency_document_counts_*.json', 'r') as f:
    data = json.load(f)
    print(f'Success rate: {data[\"metadata\"][\"success_rate_percent\"]}%')
    print(f'Total documents: {data[\"metadata\"][\"total_documents\"]:,}')
"
```

### 26. CSV Analysis

Analyze CSV results with command-line tools:

```bash
# Count agencies with zero documents
awk -F',' '$6 == 0 && $7 == "True" {count++} END {print "Agencies with zero documents:", count}' results/cfr_agency_document_counts_*.csv

# Find top 10 agencies by document count
sort -t',' -k6 -nr results/cfr_agency_document_counts_*.csv | head -10
```

## Integration Examples

### 27. Python Script Integration

Use the tool from within Python scripts:

```python
#!/usr/bin/env python3
import subprocess
import json
from pathlib import Path

# Run the counter
result = subprocess.run([
    'python', '-m', 'cfr_agency_counter.main',
    'agencies.csv',
    '--format', 'json',
    '--quiet'
], capture_output=True, text=True)

if result.returncode == 0:
    # Find and load the JSON report
    json_files = list(Path('./results').glob('*.json'))
    if json_files:
        with open(json_files[0]) as f:
            data = json.load(f)
        
        print(f"Processed {data['metadata']['total_agencies']} agencies")
        print(f"Found {data['metadata']['total_documents']:,} documents")
    else:
        print("No JSON report found")
else:
    print(f"Error: {result.stderr}")
```

### 28. Shell Script Integration

Integrate into shell scripts with error handling:

```bash
#!/bin/bash

AGENCIES_FILE="agencies.csv"
OUTPUT_DIR="./reports/$(date +%Y%m%d)"
LOG_FILE="processing_$(date +%Y%m%d).log"

echo "Starting CFR agency document counting..."

# Run the counter
python -m cfr_agency_counter.main "$AGENCIES_FILE" \
  --output-dir "$OUTPUT_DIR" \
  --log-file "$LOG_FILE" \
  --progress-interval 5.0

# Check exit code
if [ $? -eq 0 ]; then
    echo "Processing completed successfully"
    echo "Reports saved to: $OUTPUT_DIR"
    echo "Logs saved to: $LOG_FILE"
    
    # Optional: send notification
    # mail -s "CFR Processing Complete" admin@example.com < "$LOG_FILE"
else
    echo "Processing failed. Check log file: $LOG_FILE"
    exit 1
fi
```

## Performance Optimization Examples

### 29. Memory-Efficient Processing

For very large datasets:

```bash
python -m cfr_agency_counter.main agencies.csv \
  --rate-limit 0.8 \
  --timeout 120 \
  --progress-interval 2.0 \
  --format csv  # Only generate CSV to save memory
```

### 30. Network-Optimized Processing

For slow or unreliable networks:

```bash
python -m cfr_agency_counter.main agencies.csv \
  --rate-limit 0.3 \
  --timeout 180 \
  --max-retries 8 \
  --progress-interval 5.0
```

## Troubleshooting Examples

### 31. Debug Mode

Enable maximum debugging:

```bash
python -m cfr_agency_counter.main agencies.csv \
  --verbose \
  --limit 5 \
  --rate-limit 0.2 \
  --log-file debug.log
```

### 32. Connection Testing

Test API connectivity:

```bash
# First validate configuration
python -m cfr_agency_counter.main agencies.csv --validate-config

# Then do a dry run
python -m cfr_agency_counter.main agencies.csv --dry-run --limit 1

# Finally, process a small subset
python -m cfr_agency_counter.main agencies.csv --limit 3 --verbose
```

These examples cover most common use cases and scenarios. Adjust the parameters based on your specific needs, network conditions, and processing requirements.