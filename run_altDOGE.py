
import streamlit as st
from src.database import Database
from src.authmanager import AuthManager
from src.ingestionmanager import IngestionManager
from src.stripe_integration import StripeIntegration
from src.webhook_handler import WebhookHandler
from dotenv import load_dotenv
import os
import logging
import argparse
import json
from datetime import datetime
from pathlib import Path
import sys
import signal
from tqdm import tqdm
from src.logger_config import setup_logging
from typing import Optional, Dict, List

# Configure logging at the very beginning
setup_logging()
logger = logging.getLogger(__name__)

# Set project root and add to sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
load_dotenv()


def load_prompt_strategies() -> Dict[str, List[str]]:
    """Loads prompt strategies from the JSON file."""
    strategies_path = PROJECT_ROOT / "prompt_strategies.json"
    try:
        with open(strategies_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.error("prompt_strategies.json not found or invalid. Using empty dict.")
        return {}


class AltDOGERunner:
    def __init__(self):
        self.db = Database(str(PROJECT_ROOT / "altDOGE.db"))
        self.auth_manager = AuthManager(self.db)
        self.ingestion_manager = IngestionManager(self.db)
        self.stripe_integration = StripeIntegration(self.db)
        self.webhook_handler = WebhookHandler(self.db)
        self.output_dir = PROJECT_ROOT / "output"
        self.output_dir.mkdir(exist_ok=True)

    def run_streamlit_app(self):
        """Run the Streamlit application."""
        st.set_page_config(page_title="AltDOGE", layout="wide")

        # Store the runner instance in session state for pages to use
        if 'runner' not in st.session_state:
            st.session_state.runner = self

        if "user_id" not in st.session_state:
            st.session_state.user_id = None

        if not st.session_state.user_id:
            st.title("AltDOGE - Login")
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login")
                if submitted:
                    try:
                        user_id = self.auth_manager.authenticate(username, password)
                        if user_id:
                            st.session_state.user_id = user_id
                            st.rerun()
                        else:
                            st.error("Invalid credentials")
                    except Exception as e:
                        st.error("Login failed. Please try again.")
                        logger.error(f"Login error: {str(e)}")
        else:
            # This is the main landing page after login
            st.title("AltDOGE - Regulatory Reform Platform")
            st.write("Welcome! Please select a page from the sidebar to begin.")
            st.sidebar.success("Logged In")

    def run_ingestion(self, start_date: str, end_date: str, agency: Optional[str] = None,
                      doc_limit: Optional[int] = None, llm_call_limit: Optional[int] = None,
                      prompt_strategy_name: str = "DOGE Criteria"):
        """Run Federal Register data ingestion and analysis for a date range."""
        pbar = None

        def cli_progress_callback(current, total, message):
            nonlocal pbar
            if pbar is None and total > 0:
                pbar = tqdm(total=total, desc="Ingesting Documents", unit="doc")
            if pbar:
                pbar.update(current - pbar.n)
                pbar.set_description(message.split('...')[0])

        def signal_handler(sig, frame):
            if pbar:
                pbar.close()
            logger.info("Job interrupted by user")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        try:
            logger.info(
                f"Starting ingestion for {start_date} to {end_date}" + (f" for agency: {agency}" if agency else ""))
            result = self.ingestion_manager.process_federal_register(start_date, end_date, agency,
                                                                     doc_limit=doc_limit,
                                                                     llm_call_limit=llm_call_limit,
                                                                     prompt_strategy_name=prompt_strategy_name,
                                                                     progress_callback=cli_progress_callback)

            if pbar:
                pbar.close()

            if result["status"] == "success":
                logger.info(f"Processed {len(result['results'])} documents")
                output_file = self.output_dir / f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(output_file, "w") as f:
                    json.dump(result["results"], f, indent=2)
                logger.info(f"Results saved to {output_file}")
                return result
            else:
                logger.error(f"Ingestion failed: {result['message']}")
                return result
        except Exception as e:
            if pbar:
                pbar.close()
            logger.error(f"Ingestion error: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def run(self, mode: str, start_date: str, end_date: str, agency: Optional[str] = None,
            doc_limit: Optional[int] = None, llm_call_limit: Optional[int] = None,
            prompt_strategy_name: str = "DOGE Criteria"):
        """Main entry point for operations."""
        if mode == "app":
            self.run_streamlit_app()
        elif mode == "ingest":
            return self.run_ingestion(start_date, end_date, agency, doc_limit, llm_call_limit, prompt_strategy_name)
        else:
            logger.error(f"Invalid mode: {mode}")
            return {"status": "error", "message": f"Invalid mode: {mode}"}


if __name__ == "__main__":
    prompt_strategies = load_prompt_strategies()

    parser = argparse.ArgumentParser(description="AltDOGE Operations Script")
    parser.add_argument("--mode", choices=["app", "ingest"], default="app", help="Operation mode: app or ingest")
    parser.add_argument("--start-date", default="2025-07-01",
                        help="Start date for Federal Register ingestion (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2025-07-31", help="End date for Federal Register ingestion (YYYY-MM-DD)")
    parser.add_argument("--agency", default=None,
                        help="Agency to filter documents (e.g., securities-and-exchange-commission)")
    parser.add_argument("--doc-limit", type=int, default=3,
                        help="Limit the number of documents for which LLM calls are requested. Default is 3.")
    parser.add_argument("--llm-call-limit", type=int, default=4,
                        help="Limit the total number of LLM calls per session. Default is 4.")
    parser.add_argument("--strategy", default="DOGE Criteria", choices=list(prompt_strategies.keys()),
                        help="The prompt strategy to use for analysis.")
    args = parser.parse_args()

    runner = AltDOGERunner()
    # In a multi-page app, Streamlit runs the script from the top.
    # We check the mode argument to decide whether to run the CLI logic or the app.
    if args.mode == 'ingest':
        result = runner.run(mode=args.mode, start_date=args.start_date, end_date=args.end_date, agency=args.agency,
                            doc_limit=args.doc_limit, llm_call_limit=args.llm_call_limit,
                            prompt_strategy_name=args.strategy)
        if result and isinstance(result, dict):
            print(json.dumps(result, indent=2))
    else:
        # This will run when executing `streamlit run run_altDOGE.py`
        runner.run_streamlit_app()
