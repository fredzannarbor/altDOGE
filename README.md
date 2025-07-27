# AltDOGE: An Open-Source Platform for Customizable Regulatory Reform

## Vision
AltDOGE democratizes regulatory reform by providing an open-source platform for analyzing, proposing, and implementing diverse regulatory strategies. It leverages AI for regulatory analysis, supports human-in-the-loop workflows, and ensures extensibility for government agencies, legal professionals, and the public.

## Features
- **Multi-Page Web Application**: A Streamlit-based dashboard for all user interactions.
  - Secure login for authenticated users.
  - **Ingest Data**: Fetch documents from the Federal Register for a given date range and agency.
  - **View Ingestion Results**: Review the detailed, multi-prompt analysis for each document in a specific run.
  - **Analyze Regulation**: Re-run analysis on any single, already-ingested regulation from the database.
  - **Review Summary**: A consolidated dashboard showing a high-level, actionable summary of all unique regulations analyzed.
  - **Public Dashboard**: A read-only, public-facing page to view cached analysis results without needing to log in.
- **Customizable Analytical Engine**:
  - **Prompt Strategies**: Define and switch between different analytical frameworks by editing a simple `prompt_strategies.json` file. No code changes needed to change the analysis.
  - **Meta-Analysis**: After running the base prompts, a second AI call synthesizes the results into a high-level summary, including a recommended action, goal alignment, and a bullet-point summary.
- **CLI for Batch Processing**: Ingest and analyze data via the command line for automated workflows.
- **Local Database**: Uses SQLite to store ingested regulations for re-analysis and persistence.
- **Open-Source**: Licensed under Apache 2.0.

## Setup Instructions
1.  **Clone the repository** (if not already done):
    
2. Run the initialization script: `python init_altdoge.py`
   - This script creates the repository structure, installs Python 3.12.3 (if needed), installs uv and dependencies, initializes the database, sets up environment variables, and initializes a Git repository.
3. Run the application: `python run_altdoge.py --mode app`
   - Access the app at `http://localhost:8501`.
   - To ingest Federal Register data: `python run_altdoge.py --mode ingest --start-date 2025-01-20`

## Requirements
- Python 3.12.3 (automatically installed by `init_altdoge.py`)
- uv 0.4.24 (installed by `init_altdoge.py`)
- SQLite (`xtuff_collections.db`)
- See `requirements.txt` for dependencies.

## Environment Variables
The `init_altdoge.py` script creates a `.env` file, prompting for:
```
STRIPE_API_KEY=your_stripe_api_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
LITELLM_MODEL=gpt-4o
LITELLM_API_KEY=your_llm_api_key
FEDERAL_REGISTER_API_KEY=your_federal_register_api_key
```

## Contribution Guidelines
- Follow the [Contribution Guide](CONTRIBUTING.md) (TBD).
- Submit issues and pull requests via GitHub.
- Join our community forum (TBD) for discussions.

## License
Apache 2.0 License
