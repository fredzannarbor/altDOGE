#!/bin/bash
set -e

# CFR Document Analyzer Entrypoint Script

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check environment variables
check_env() {
    if [ -z "$GEMINI_API_KEY" ]; then
        log "WARNING: GEMINI_API_KEY not set. LLM functionality will not work."
    fi
}

# Function to initialize database
init_database() {
    log "Initializing database..."
    python -c "
from cfr_document_analyzer.database import Database
db = Database('/app/data/cfr_analyzer.db')
print('Database initialized successfully')
"
}

# Function to run health checks
health_check() {
    log "Running health checks..."
    python -c "
from cfr_document_analyzer.config import Config
try:
    Config.validate()
    print('Configuration validation passed')
except Exception as e:
    print(f'Configuration validation failed: {e}')
    exit(1)
"
}

# Main execution
main() {
    log "Starting CFR Document Analyzer..."
    
    # Check environment
    check_env
    
    # Initialize database if it doesn't exist
    if [ ! -f "/app/data/cfr_analyzer.db" ]; then
        init_database
    fi
    
    # Run health checks
    health_check
    
    # Execute the requested command
    case "$1" in
        "streamlit")
            log "Starting Streamlit web interface..."
            exec streamlit run cfr_document_analyzer/streamlit_app.py \
                --server.port=8501 \
                --server.address=0.0.0.0 \
                --server.headless=true \
                --server.fileWatcherType=none \
                --browser.gatherUsageStats=false
            ;;
        "cli")
            log "Starting CLI mode..."
            shift
            exec python -m cfr_document_analyzer.cli "$@"
            ;;
        "test")
            log "Running tests..."
            exec pytest tests/ -v
            ;;
        "shell")
            log "Starting interactive shell..."
            exec /bin/bash
            ;;
        *)
            log "Unknown command: $1"
            log "Available commands: streamlit, cli, test, shell"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"