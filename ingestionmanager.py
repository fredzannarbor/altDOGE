To address your request, I'll consolidate the AltDOGE initialization and operational logic into at most two scripts: one for setup (`init_altdoge.py`) and one for repeated operations (`run_altdoge.py`). The setup script will handle environment configuration, dependency installation, and database initialization, while the operations script will manage data ingestion, analysis, and Streamlit app execution. These scripts will align with your specified stack (Python 3.12.3, Streamlit 1.46.0, SQLite, etc.) and patterns (Manager Class, centralized database, error handling, environment configuration). I'll also update the `README.md` to reflect these changes.

### Approach
- **Setup Script (`init_altdoge.py`)**: Handles one-time setup tasks (Python version check, dependency installation, database initialization, `.env` creation).
- **Operations Script (`run_altdoge.py`)**: Combines the Streamlit app (`app.py`) and data ingestion/processing logic (`ingestionmanager.py`) for repeated operations like fetching Federal Register data, analyzing it, and running the UI.
- **Updated Files**: Modify `ingestionmanager.py` to integrate with the operations script and update `README.md` for clarity.
- **Constraints**: Ensure scripts are standalone, idempotent, and adhere to your stack (e.g., Streamlit, SQLite, litellm) and patterns (e.g., centralized database, error handling).

Below are the updated artifacts, keeping the repository structure and existing files intact where possible.

```python
import subprocess
import sys
import os
import platform
import sqlite3
import logging
from pathlib import Path
from dotenv import load_dotenv, dotenv_values
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AltDOGEInitializer:
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.db_path = self.project_dir / "xtuff_collections.db"
        self.env_path = self.project_dir / ".env"
        self.requirements_path = self.project_dir / "requirements.txt"
        self.python_version = "3.12.3"

    def check_python_version(self) -> bool:
        """Check if the correct Python version is installed."""
        try:
            current_version = platform.python_version()
            if current_version != self.python_version:
                logger.warning(f"Python {self.python_version} required, found {current_version}")
                return self.install_python()
            logger.info(f"Python {current_version} is correct")
            return True
        except Exception as e:
            logger.error(f"Error checking Python version: {str(e)}")
            return False

    def install_python(self) -> bool:
        """Install Python 3.12.3 using system package manager."""
        try:
            if sys.platform.startswith("linux"):
                subprocess.run(["sudo", "apt-get", "update"], check=True)
                subprocess.run(["sudo", "apt-get", "install", "-y", f"python{self.python_version}"], check=True)
            elif sys.platform == "darwin":
                subprocess.run(["brew", "install", f"python@{self.python_version}"], check=True)
            else:
                logger.error("Unsupported platform for automatic Python installation")
                return False
            logger.info(f"Python {self.python_version} installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install Python: {str(e)}")
            return False

    def install_dependencies(self) -> bool:
        """Install dependencies from requirements.txt."""
        try:
            requirements_content = """\
python==3.12.3
streamlit==1.46.0
stripe==10.12.0
litellm==1.48.0
python-dotenv==1.0.1
pandas==2.2.3
numpy==2.1.2
requests==2.32.3
"""
            self.requirements_path.write_text(requirements_content)
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(self.requirements_path)], check=True)
            logger.info("Dependencies installed successfully")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Error installing dependencies: {str(e)}")
            return False

    def init_database(self) -> bool:
        """Initialize SQLite database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS regulations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        reg_number TEXT NOT NULL,
                        title TEXT,
                        text TEXT,
                        effective_date TEXT,
                        agency TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS subscriptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        stripe_subscription_id TEXT,
                        status TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                """)
                conn.commit()
            logger.info("Database initialized successfully")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {str(e)}")
            return False

    def create_env_file(self) -> bool:
        """Create .env file with default configuration, prompting for sensitive keys."""
        try:
            if self.env_path.exists():
                logger.info(".env file already exists, skipping creation")
                return True

            stripe_api_key = input("Enter Stripe API Key (or press Enter to skip): ").strip() or "your_stripe_api_key"
            stripe_webhook_secret = input("Enter Stripe Webhook Secret (or press Enter to skip): ").strip() or "your_stripe_webhook_secret"
            litellm_api_key = input("Enter LLM API Key (or press Enter to skip): ").strip() or "your_llm_api_key"
            federal_register_api_key = input("Enter Federal Register API Key (optional, press Enter to skip): ").strip() or "your_federal_register_api_key"

            env_content = f"""\
STRIPE_API_KEY={stripe_api_key}
STRIPE_WEBHOOK_SECRET={stripe_webhook_secret}
LITELLM_MODEL=gpt-4o
LITELLM_API_KEY={litellm_api_key}
FEDERAL_REGISTER_API_KEY={federal_register_api_key}
"""
            self.env_path.write_text(env_content)
            logger.info(".env file created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating .env file: {str(e)}")
            return False

    def write_python_version(self) -> bool:
        """Write .python-version file for pyenv compatibility."""
        try:
            (self.project_dir / ".python-version").write_text(self.python_version)
            logger.info(".python-version file created")
            return True
        except Exception as e:
            logger.error(f"Error writing .python-version: {str(e)}")
            return False

    def run(self) -> bool:
        """Run the initialization process."""
        logger.info("Starting AltDOGE initialization...")
        
        steps = [
            (self.check_python_version, "Checking Python version"),
            (self.install_dependencies, "Installing dependencies"),
            (self.init_database, "Initializing database"),
            (self.create_env_file, "Creating .env file"),
            (self.write_python_version, "Writing .python-version file")
        ]

        for step_func, step_name in steps:
            logger.info(f"Executing: {step_name}")
            if not step_func():
                logger.error(f"Initialization failed at step: {step_name}")
                return False

        logger.info("AltDOGE initialization completed successfully")
        logger.info("Run the application with: python run_altdoge.py")
        return True

if __name__ == "__main__":
    initializer = AltDOGEInitializer()
    success = initializer.run()
    sys.exit(0 if success else 1)
```

```python
import streamlit as st
from src.database import Database
from src.authmanager import AuthManager
from src.ingestionmanager import IngestionManager
from src.litellm_fallback import LiteLLMFallback
from src.stripe_integration import StripeIntegration
from src.webhook_handler import WebhookHandler
from dotenv import load_dotenv
import os
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class AltDOGERunner:
    def __init__(self):
        self.db = Database("xtuff_collections.db")
        self.llm = LiteLLMFallback()
        self.auth_manager = AuthManager(self.db)
        self.ingestion_manager = IngestionManager(self.db, self.llm)
        self.stripe_integration = StripeIntegration(self.db)
        self.webhook_handler = WebhookHandler(self.db)

    def run_streamlit_app(self):
        """Run the Streamlit application."""
        try:
            st.set_page_config(page_title="AltDOGE", layout="wide")
            
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
                                st.success("Logged in successfully!")
                                st.rerun()
                            else:
                                st.error("Invalid credentials")
                        except Exception as e:
                            st.error("Login failed. Please try again.")
                            logger.error(f"Login error: {str(e)}")
            else:
                st.title("AltDOGE - Regulatory Reform Platform")
                st.write("Welcome to AltDOGE. Use the sidebar to navigate.")
                
                # Sidebar for operations
                operation = st.sidebar.selectbox(
                    "Select Operation",
                    ["View Dashboard", "Ingest Federal Register Data", "Analyze Regulations"]
                )
                
                if operation == "Ingest Federal Register Data":
                    start_date = st.text_input("Start Date (YYYY-MM-DD)", "2025-01-20")
                    if st.button("Start Ingestion"):
                        with st.spinner("Fetching and processing Federal Register data..."):
                            result = self.ingestion_manager.process_federal_register(start_date)
                            if result["status"] == "success":
                                st.success(f"Processed {len(result['results'])} documents")
                                st.json(result["results"][:10])  # Show sample results
                            else:
                                st.error(f"Ingestion failed: {result['message']}")
                
                elif operation == "Analyze Regulations":
                    reg_id = st.number_input("Regulation ID", min_value=1, step=1)
                    if st.button("Analyze"):
                        with st.spinner("Analyzing regulation..."):
                            result = self.ingestion_manager.analyze_regulation(reg_id)
                            if "error" not in result:
                                st.success("Analysis complete")
                                st.json(result)
                            else:
                                st.error(f"Analysis failed: {result['error']}")
                
                elif operation == "View Dashboard":
                    st.write("Overview of regulatory analysis progress.")
                    st.empty()  # Placeholder for dashboard metrics

        except Exception as e:
            st.error("An error occurred in the application.")
            logger.error(f"Streamlit app error: {str(e)}")

    def run_ingestion(self, start_date: str = "2025-01-20"):
        """Run Federal Register data ingestion and analysis."""
        try:
            result = self.ingestion_manager.process_federal_register(start_date)
            if result["status"] == "success":
                logger.info(f"Processed {len(result['results'])} documents")
                return result
            else:
                logger.error(f"Ingestion failed: {result['message']}")
                return result
        except Exception as e:
            logger.error(f"Ingestion error: {str(e)}")
            return {"status": "error", "message": str(e)}

    def run(self, mode: str = "app", start_date: str = "2025-01-20"):
        """Main entry point for operations."""
        if mode == "app":
            self.run_streamlit_app()
        elif mode == "ingest":
            return self.run_ingestion(start_date)
        else:
            logger.error(f"Invalid mode: {mode}")
            return {"status": "error", "message": f"Invalid mode: {mode}"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AltDOGE Operations Script")
    parser.add_argument("--mode", choices=["app", "ingest"], default="app", help="Operation mode: app or ingest")
    parser.add_argument("--start-date", default="2025-01-20", help="Start date for Federal Register ingestion (YYYY-MM-DD)")
    args = parser.parse_args()
    
    runner = AltDOGERunner()
    result = runner.run(mode=args.mode, start_date=args.start_date)
    if result and isinstance(result, dict):
        print(result)
```

```python
import requests
import xml.etree.ElementTree as ET
from src.database import Database
from src.litellm_fallback import LiteLLMFallback
from typing import Dict, Any, List, Tuple
import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv
import logging
import backoff

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class IngestionManager:
    def __init__(self, db: Database, llm: LiteLLMFallback):
        self.db = db
        self.llm = llm
        self.api_key = os.getenv("FEDERAL_REGISTER_API_KEY")
        self.base_url = "https://www.federalregister.gov/api/v1/documents"
        self.chunk_size = 100  # Number of documents per chunk

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
    def fetch_federal_register_data(self, start_date: str = "2025-01-20") -> List[Dict[str, Any]]:
        """Fetch Federal Register documents published after the start date."""
        try:
            params = {
                "fields[]": ["title", "full_text_xml_url", "agencies", "publication_date", "document_number"],
                "per_page": 1000,
                "publication_date_gte": start_date,
                "order": "newest"
            }
            if self.api_key:
                params["api_key"] = self.api_key

            all_documents = []
            page = 1
            while True:
                params["page"] = page
                response = requests.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                documents = data.get("results", [])
                all_documents.extend(documents)
                
                if not data.get("next_page_url"):
                    break
                page += 1

            logger.info(f"Fetched {len(all_documents)} documents from Federal Register")
            return all_documents
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Federal Register data: {str(e)}")
            return []

    def parse_xml_content(self, xml_url: str) -> str:
        """Parse XML content from a given URL."""
        try:
            response = requests.get(xml_url)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            text_elements = root.findall(".//{http://www.w3.org/XML/1998/namespace}text")
            return " ".join([elem.text for elem in text_elements if elem.text])[:10000]  # Limit text size
        except (requests.exceptions.RequestException, ET.ParseError) as e:
            logger.error(f"Error parsing XML from {xml_url}: {str(e)}")
            return ""

    def ingest_regulation(self, reg_data: Dict[str, Any]) -> bool:
        """Store regulation data in the database."""
        try:
            query = """
                INSERT OR IGNORE INTO regulations (reg_number, title, text, effective_date, agency)
                VALUES (?, ?, ?, ?, ?)
            """
            params = (
                reg_data.get("document_number", ""),
                reg_data.get("title", ""),
                reg_data.get("text", ""),
                reg_data.get("publication_date", ""),
                reg_data.get("agency", "")
            )
            self.db.execute_query(query, params)
            return True
        except Exception as e:
            logger.error(f"Error ingesting regulation {reg_data.get('document_number', 'unknown')}: {str(e)}")
            return False

    def chunk_by_agency(self, documents: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Organize documents by agency, chunking large datasets."""
        agency_chunks = {}
        for doc in documents:
            agencies = [agency.get("name", "Unknown") for agency in doc.get("agencies", [])]
            agency_name = agencies[0] if agencies else "Unknown"
            
            if agency_name not in agency_chunks:
                agency_chunks[agency_name] = []
            agency_chunks[agency_name].append(doc)
            
            if len(agency_chunks[agency_name]) > self.chunk_size:
                agency_chunks[f"{agency_name}_{len(agency_chunks[agency_name]) // self.chunk_size}"] = \
                    agency_chunks[agency_name][-self.chunk_size:]
                agency_chunks[agency_name] = agency_chunks[agency_name][:-self.chunk_size]
        
        return agency_chunks

    def define_alternative_prompts(self) -> List[str]:
        """Define alternative prompts for analysis."""
        return [
            "Analyze the following regulation text and categorize as Statutorily Required (SR), Not Statutorily Required (NSR), or Not Required but Agency Needs (NRAN). Provide a detailed justification citing statutory provisions if applicable:\n{text}",
            "Evaluate the following regulation for potential reform actions (deletion, simplification, harmonization, modernization). Suggest specific changes with justifications:\n{text}",
            "Identify any outdated terminology or processes in the following regulation and propose modernized alternatives:\n{text}",
            "Assess the clarity of the following regulation and suggest rephrasing to reduce ambiguity:\n{text}"
        ]

    def analyze_regulation(self, reg_id: int) -> Dict[str, Any]:
        """Analyze a single regulation by ID."""
        try:
            query = "SELECT text FROM regulations WHERE id = ?"
            result = self.db.execute_query(query, (reg_id,))
            if not result:
                return {"error": "Regulation not found"}
            
            reg_text = result[0][0]
            prompts = self.define_alternative_prompts()
            analysis_results = []
            
            for prompt_template in prompts:
                prompt = prompt_template.format(text=reg_text[:4000])  # Limit prompt size
                try:
                    result = self.llm.completion_with_fallback(prompt)
                    if result["status"] == "success":
                        analysis_results.append({
                            "prompt": prompt_template.split("\n")[0],
                            "result": result["response"]
                        })
                    else:
                        analysis_results.append({
                            "prompt": prompt_template.split("\n")[0],
                            "error": result["message"]
                        })
                except Exception as e:
                    logger.error(f"LLM analysis failed for regulation {reg_id}: {str(e)}")
                    analysis_results.append({
                        "prompt": prompt_template.split("\n")[0],
                        "error": str(e)
                    })
            
            return {"category": analysis_results}
        except Exception as e:
            logger.error(f"Analysis error for regulation {reg_id}: {str(e)}")
            return {"