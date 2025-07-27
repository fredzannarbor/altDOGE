# init.py
import subprocess
import sys
import os
import platform
import sqlite3
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
import hashlib
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set project root and add to sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


class AltDOGEInitializer:
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.db_path = self.project_dir / "altDOGE.db"
        self.env_path = self.project_dir / ".env"
        self.requirements_path = self.project_dir / "requirements.txt"
        self.prompts_path = self.project_dir / "prompt_strategies.json"
        self.python_version = "3.12.3"
        self.src_dir = self.project_dir / "src"
        self.pages_dir = self.project_dir / "pages"

    def create_prompt_strategies_file(self) -> bool:
        """Creates the prompt_strategies.json file with default content."""
        try:
            if self.prompts_path.exists():
                logger.info(f"{self.prompts_path.name} already exists, skipping creation.")
                return True

            strategies = {
                "DOGE Criteria": [
                    "Analyze the following regulation text and categorize as Statutorily Required (SR), Not Statutorily Required (NSR), or Not Required but Agency Needs (NRAN). Provide a detailed justification citing statutory provisions if applicable:\n{text}",
                    "Evaluate the following regulation for potential reform actions (deletion, simplification, harmonization, modernization). Suggest specific changes with justifications:\n{text}",
                    "Identify any outdated terminology or processes in the following regulation and propose modernized alternatives:\n{text}",
                    "Assess the clarity of the following regulation and suggest rephrasing to reduce ambiguity:\n{text}"
                ],
                "Statutory Alignment": [
                    "Statutory Alignment: Ensure the regulation fully implements the statutory requirements and intent, addressing all mandated objectives without omission.\n{text}",
                    "Clarity and Accessibility: Enhance the regulation’s language and structure to make it clear, concise, and understandable to the general public.\n{text}",
                    "Outcome: Evaluate whether the regulation achieves its intended outcomes. Include assessment of public sentiment.\n{text}",
                    "Adaptability to Modern Contexts: Identify opportunities to update the regulation so that the effective scope of the legislation fully adapts to t current technological, economic, and social conditions.\n{text}"
                ]
            }
            with open(self.prompts_path, "w", encoding="utf-8") as f:
                json.dump(strategies, f, indent=2)
            logger.info(f"{self.prompts_path.name} created successfully.")
            return True
        except Exception as e:
            logger.error(f"Error creating {self.prompts_path.name}: {e}")
            return False

    def create_repository_structure(self) -> bool:
        """Create the repository structure with necessary directories and files."""
        try:
            # Create directories
            self.src_dir.mkdir(exist_ok=True)
            self.pages_dir.mkdir(exist_ok=True)

            # Create __init__.py in src
            (self.src_dir / "__init__.py").touch(exist_ok=True)

            # --- Create functional Streamlit page files ---
            page_contents = {
                "1_Ingest_Data.py": """
import streamlit as st
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)
st.set_page_config(page_title="Ingest Data - AltDOGE", layout="wide")

if "runner" not in st.session_state:
    st.error("Application not initialized. Please return to the main page.")
    st.page_link("run_altDOGE.py", label="Go to Home", icon="🏠")
    st.stop()
runner = st.session_state.runner

if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.error("Please log in to access this page.")
    st.page_link("run_altDOGE.py", label="Go to Login", icon="🏠")
    st.stop()

st.title("Ingest Federal Register Data")
start_date = st.text_input("Start Date (YYYY-MM-DD)", "2025-07-01")
end_date = st.text_input("End Date (YYYY-MM-DD)", "2025-07-31")

# --- Agency Dropdown ---
all_agencies = runner.ingestion_manager.agencies
if all_agencies:
    agency_options = {agency['name']: agency['slug'] for agency in all_agencies}
    agency_names = ["All Agencies"] + list(agency_options.keys())
    selected_agency_name = st.selectbox(
        "Select an Agency (optional)",
        options=agency_names,
        index=0  # Default to "All Agencies"
    )
    agency_slug = agency_options.get(selected_agency_name)
else:
    st.warning("Could not fetch agency list. Please enter agency slug manually.")
    agency_slug = st.text_input("Agency Slug (e.g., securities-and-exchange-commission)", "")

prompt_strategies = runner.ingestion_manager.prompt_strategies.keys()
selected_strategy = st.selectbox("Select Prompt Strategy", options=list(prompt_strategies))
doc_limit = st.number_input("Document Limit", min_value=1, value=3, help="Max number of documents for LLM analysis.")
llm_call_limit = st.number_input("Total LLM Call Limit", min_value=1, value=4, help="Max total LLM calls for this session.")

if st.button("Start Ingestion"):
    progress_bar = st.progress(0, text="Starting ingestion...")
    def streamlit_progress_callback(current, total, message):
        if total > 0:
            progress_bar.progress(current / total, text=message)
        else:
            progress_bar.progress(0, text=message)

    result = runner.ingestion_manager.process_federal_register(
        start_date, end_date, agency=agency_slug,
        doc_limit=doc_limit, llm_call_limit=llm_call_limit,
        prompt_strategy_name=selected_strategy,
        progress_callback=streamlit_progress_callback
    )

    if result["status"] == "success":
        st.success(f"Processed {len(result['results'])} documents")
        output_file = runner.output_dir / f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(result["results"], f, indent=2)
        st.write(f"Results saved to {output_file}")
        st.info("You can now view the results on the 'View Ingestion Results' page.")
        st.json(result["results"][:5])
    else:
        st.error(f"Ingestion failed: {result['message']}")
""",
                "2_View_Results.py": """
import streamlit as st
import logging
import json
import os

logger = logging.getLogger(__name__)
st.set_page_config(page_title="View Results - AltDOGE", layout="wide")

if "runner" not in st.session_state:
    st.error("Application not initialized. Please return to the main page.")
    st.page_link("run_altDOGE.py", label="Go to Home", icon="🏠")
    st.stop()
runner = st.session_state.runner

if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.error("Please log in to access this page.")
    st.page_link("run_altDOGE.py", label="Go to Login", icon="🏠")
    st.stop()

st.header("View Ingestion Results")
try:
    result_files = sorted(runner.output_dir.glob("analysis_results_*.json"), key=os.path.getmtime, reverse=True)
    if not result_files:
        st.warning("No result files found. Please run an ingestion first.")
    else:
        selected_file = st.selectbox("Select a result file to view:", options=result_files, format_func=lambda p: p.name)
        if selected_file:
            with open(selected_file, "r", encoding='utf-8') as f:
                results_data = json.load(f)
            st.write(f"Displaying results from `{selected_file.name}`")
            st.write(f"Total documents analyzed: {len(results_data)}")
            for doc_result in results_data:
                title = doc_result.get('title', 'No Title Provided')
                doc_num = doc_result.get('document_number', 'Unknown Document')
                with st.expander(f"**{doc_num}**: {title}"):
                    st.write(f"**Agency:** {doc_result.get('agency', 'N/A')}")
                    st.subheader("Analyses:")
                    for analysis in doc_result.get('analyses', []):
                        st.markdown(f"**Prompt:** `{analysis.get('prompt')}`")
                        st.markdown(analysis.get('result'))
                        st.markdown("---")
except Exception as e:
    st.error(f"An error occurred while reading result files: {e}")
    logger.error(f"Error reading result files: {e}", exc_info=True)
""",
                "3_Analyze_Regulation.py": """
import streamlit as st
import logging

logger = logging.getLogger(__name__)
st.set_page_config(page_title="Analyze Regulation - AltDOGE", layout="wide")

if "runner" not in st.session_state:
    st.error("Application not initialized. Please return to the main page.")
    st.page_link("run_altDOGE.py", label="Go to Home", icon="🏠")
    st.stop()
runner = st.session_state.runner

if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.error("Please log in to access this page.")
    st.page_link("run_altDOGE.py", label="Go to Login", icon="🏠")
    st.stop()

st.title("Analyze a Specific Regulation by ID")
prompt_strategies = runner.ingestion_manager.prompt_strategies.keys()
selected_strategy = st.selectbox("Select Prompt Strategy", options=list(prompt_strategies))
reg_id = st.number_input("Regulation ID from Database", min_value=1, step=1)
if st.button("Analyze"):
    with st.spinner(f"Analyzing regulation {reg_id} with '{selected_strategy}' strategy..."):
        result = runner.ingestion_manager.analyze_regulation(reg_id, prompt_strategy_name=selected_strategy)
        if "error" not in result:
            st.success("Analysis complete")
            st.json(result)
        else:
            st.error(f"Analysis failed: {result['error']}")
""",
                "4_Review_Summary.py": """
import streamlit as st
import pandas as pd
import logging
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)
st.set_page_config(page_title="Review Summary - AltDOGE", layout="wide")

@st.cache_data
def load_all_results(output_dir: Path) -> pd.DataFrame:
    all_results = []
    result_files = sorted(output_dir.glob("analysis_results_*.json"), key=os.path.getmtime, reverse=True)
    for file_path in result_files:
        try:
            with open(file_path, "r", encoding='utf-8') as f:
                data = json.load(f)
                all_results.extend(data)
        except Exception as e:
            logger.error(f"Could not read file {file_path}: {e}")
    return pd.DataFrame(all_results) if all_results else pd.DataFrame()

def create_summary_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    processed_rows = []
    for _, row in df.iterrows():
        meta_analysis = row.get('meta_analysis', {})
        if not isinstance(meta_analysis, dict):
            meta_analysis = {}
        bullet_summary_list = meta_analysis.get('bullet_summary', [])
        if isinstance(bullet_summary_list, list):
            bullet_summary = "\\n".join(f"- {item}" for item in bullet_summary_list)
        else:
            bullet_summary = "Summary not available."
        new_row = {
            'document_number': row.get('document_number'),
            'title': row.get('title'),
            'agency': row.get('agency'),
            'Strategy': row.get('prompt_strategy_name', 'Unknown'),
            'Recommended Action': meta_analysis.get('recommended_action', 'N/A'),
            'Goal Alignment': meta_analysis.get('goal_alignment', 'N/A'),
            'Summary': bullet_summary
        }
        processed_rows.append(new_row)
    return pd.DataFrame(processed_rows)

if "runner" not in st.session_state:
    st.error("Application not initialized. Please return to the main page.")
    st.page_link("run_altDOGE.py", label="Go to Home", icon="🏠")
    st.stop()
runner = st.session_state.runner

if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.error("Please log in to access this page.")
    st.page_link("run_altDOGE.py", label="Go to Login", icon="🏠")
    st.stop()

st.title("Review Summary of All Ingestions")
raw_df = load_all_results(runner.output_dir)

if raw_df.empty:
    st.warning("No result files found in the output directory. Please run an ingestion first.")
    st.stop()

total_results = len(raw_df)
unique_df = raw_df.drop_duplicates(subset=['document_number'], keep='last').copy()
unique_results = len(unique_df)

st.metric("Total Results Analyzed (All Runs)", total_results)
st.metric("Unique Regulations Analyzed", unique_results)

processed_df = create_summary_dataframe(unique_df)

st.subheader("Summary by Regulation")

if not processed_df.empty:
    st.write("### Recommended Actions Breakdown")
    action_counts = processed_df['Recommended Action'].value_counts()
    st.bar_chart(action_counts)
    st.dataframe(
        processed_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Recommended Action": st.column_config.TextColumn(width="medium"),
            "Goal Alignment": st.column_config.TextColumn(width="medium"),
            "Summary": st.column_config.TextColumn(width="large")
        }
    )
else:
    st.info("Could not process results into a summary view.")
""",
                "5_Public_Results.py": """
import streamlit as st
import pandas as pd
import logging
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)
st.set_page_config(page_title="Public Results - AltDOGE", layout="wide")

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
OUTPUT_DIR = PROJECT_ROOT / "output"

@st.cache_data
def load_all_results(output_dir: Path) -> pd.DataFrame:
    all_results = []
    if not output_dir.exists():
        logger.warning(f"Output directory does not exist: {output_dir}")
        return pd.DataFrame()
    result_files = sorted(output_dir.glob("analysis_results_*.json"), key=os.path.getmtime, reverse=True)
    for file_path in result_files:
        try:
            with open(file_path, "r", encoding='utf-8') as f:
                data = json.load(f)
                all_results.extend(data)
        except Exception as e:
            logger.error(f"Could not read file {file_path}: {e}")
    return pd.DataFrame(all_results) if all_results else pd.DataFrame()

def create_summary_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    processed_rows = []
    for _, row in df.iterrows():
        meta_analysis = row.get('meta_analysis', {})
        if not isinstance(meta_analysis, dict):
            meta_analysis = {}
        bullet_summary_list = meta_analysis.get('bullet_summary', [])
        if isinstance(bullet_summary_list, list):
            bullet_summary = "\\n".join(f"- {item}" for item in bullet_summary_list)
        else:
            bullet_summary = "Summary not available."
        new_row = {
            'document_number': row.get('document_number'),
            'title': row.get('title'),
            'agency': row.get('agency'),
            'Strategy': row.get('prompt_strategy_name', 'Unknown'),
            'Recommended Action': meta_analysis.get('recommended_action', 'N/A'),
            'Goal Alignment': meta_analysis.get('goal_alignment', 'N/A'),
            'Summary': bullet_summary
        }
        processed_rows.append(new_row)
    return pd.DataFrame(processed_rows)

st.title("Public Dashboard: Summary of All Analyses")
st.info("This page displays a cached summary of all previously completed regulation analyses.")
raw_df = load_all_results(OUTPUT_DIR)

if raw_df.empty:
    st.warning("No result files found. Analysis may not have been run yet.")
    st.stop()

unique_df = raw_df.drop_duplicates(subset=['document_number'], keep='last').copy()
processed_df = create_summary_dataframe(unique_df)

st.subheader("Summary by Regulation")

if not processed_df.empty:
    st.metric("Unique Regulations Analyzed", len(unique_df))
    st.write("#### Recommended Actions Breakdown")
    action_counts = processed_df['Recommended Action'].value_counts()
    st.bar_chart(action_counts)
    st.dataframe(processed_df, use_container_width=True, hide_index=True)
else:
    st.info("Could not process results into a summary view.")
"""
            }

            for file_name, content in page_contents.items():
                page_path = self.pages_dir / file_name
                page_path.write_text(content)

            old_placeholders = ["1_dashboard.py", "2_analysis.py", "3_proposals.py", "4_comments.py", "5_settings.py"]
            for old_file in old_placeholders:
                if old_file not in page_contents:
                    old_path = self.pages_dir / old_file
                    if old_path.exists():
                        old_path.unlink()

            src_files = {
                "app.py": """# This file is deprecated and can be removed. run_altDOGE.py is the main entrypoint.""",
                "database.py": """import sqlite3
from typing import Any, List, Tuple
from contextlib import contextmanager

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, query: str, params: Tuple = ()) -> List[Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.fetchall()
""",
                "authmanager.py": """from src.database import Database
from typing import Optional
import hashlib

class AuthManager:
    def __init__(self, db: Database):
        self.db = db

    def authenticate(self, username: str, password: str) -> Optional[int]:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        query = "SELECT id FROM users WHERE username = ? AND password_hash = ?"
        result = self.db.execute_query(query, (username, password_hash))
        return result[0][0] if result else None
""",
                "logger_config.py": """import logging
import sys
from pathlib import Path

def setup_logging():
    project_root = Path(__file__).parent.parent.resolve()
    log_file_path = project_root / "altdoge.log"
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    root_logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)
    logging.info("Logging configured to write to console and altdoge.log")
""",
                "llm_caller.py": """import logging
import json
import time
from typing import List, Dict, Any, Optional
import litellm
from litellm.exceptions import APIError, RateLimitError, ServiceUnavailableError, BadRequestError
from json_repair import repair_json

litellm.telemetry = False
litellm.set_verbose = False
logger = logging.getLogger(__name__)

def _parse_llm_response(response_content: str, response_format_type: str) -> Any:
    if response_format_type == "json_object":
        try:
            return json.loads(repair_json(response_content))
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to decode JSON: {e}. Content: {response_content[:200]}...")
            return {"error": "JSON parsing failed"}
    return response_content

def call_model_with_prompt(
        model_name: str, prompt_config: Dict[str, Any], response_format_type: str = "text",
        max_retries: int = 3, initial_delay: int = 5) -> Dict[str, Any]:
    messages = prompt_config.get("messages", [])
    model_params = prompt_config.get("params", {}).copy()
    model_params.pop('model', None)
    for attempt in range(max_retries):
        try:
            logger.info(f"Querying {model_name} (Attempt {attempt + 1}/{max_retries})...")
            response = litellm.completion(model=model_name, messages=messages, **model_params)
            raw_content = response.choices[0].message.content
            parsed_content = _parse_llm_response(raw_content, response_format_type)
            return {"parsed_content": parsed_content, "raw_content": raw_content}
        except (RateLimitError, ServiceUnavailableError) as e:
            delay = initial_delay * (2 ** attempt)
            logger.warning(f"Rate limit/service unavailable for {model_name}: {e}. Retrying in {delay}s...")
            time.sleep(delay)
        except Exception as e:
            logger.critical(f"Unexpected error calling {model_name}: {e}", exc_info=True)
            return {"parsed_content": {"error": "Unexpected Error"}, "raw_content": str(e)}
    logger.error(f"Final failure after {max_retries} retries for {model_name}.")
    return {"parsed_content": {"error": "Final failure after retries"}, "raw_content": "Max retries exceeded."}

def get_responses_from_multiple_models(
        prompt_configs: List[Dict[str, Any]], models: List[str], response_format_type: str = "text",
        per_model_params: Optional[Dict[str, Any]] = None) -> Dict[str, List[Dict[str, Any]]]:
    default_model = models[0] if models else None
    all_responses: Dict[str, List[Dict[str, Any]]] = {}
    for i, config_wrapper in enumerate(prompt_configs):
        prompt_config = config_wrapper.get("prompt_config", {})
        prompt_key = config_wrapper.get("key", f"unknown_prompt_{i}")
        model_to_use = prompt_config.get("params", {}).get("model", default_model)
        if not model_to_use:
            logger.error(f"No model for prompt '{prompt_key}'. Skipping.")
            continue
        if model_to_use not in all_responses:
            all_responses[model_to_use] = []
        final_prompt_config = prompt_config.copy()
        if per_model_params and model_to_use in per_model_params:
            final_prompt_config.setdefault("params", {}).update(per_model_params[model_to_use])
        response_data = call_model_with_prompt(
            model_name=model_to_use, prompt_config=final_prompt_config,
            response_format_type=response_format_type)
        response_data['prompt_key'] = prompt_key
        all_responses[model_to_use].append(response_data)
    return all_responses
""",
            }
            for file_name, content in src_files.items():
                file_path = self.src_dir / file_name
                if not file_path.exists() or "deprecated" in content:
                    file_path.write_text(content)

            logger.info("Repository structure created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating repository structure: {str(e)}")
            return False

    def install_dependencies(self) -> bool:
        """Install dependencies using uv."""
        try:
            requirements_content = """streamlit==1.46.0
stripe==10.12.0
litellm==1.48.0
python-dotenv==1.0.1
pandas==2.2.3
numpy==2.1.2
requests==2.32.3
tqdm
json-repair
backoff
"""
            self.requirements_path.write_text(requirements_content)
            subprocess.run(["uv", "pip", "install", "-r", str(self.requirements_path)], check=True)
            logger.info("Dependencies installed successfully with uv")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Error installing dependencies: {str(e)}")
            return False

    def init_database(self) -> bool:
        """Initialize SQLite database with required tables and default users."""
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
                        reg_number TEXT NOT NULL UNIQUE,
                        title TEXT,
                        text TEXT,
                        effective_date TEXT,
                        agency TEXT
                    )
                """)
                default_users = [("admin", "AdminPass123"), ("test", "TestPass123")]
                for username, password in default_users:
                    password_hash = hashlib.sha256(password.encode()).hexdigest()
                    cursor.execute("INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)",
                                   (username, password_hash))
                conn.commit()
            logger.info("Database initialized successfully")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {str(e)}")
            return False

    def run(self) -> bool:
        """Run the initialization process."""
        logger.info("Starting AltDOGE initialization...")
        steps = [
            (self.create_repository_structure, "Creating repository structure"),
            (self.create_prompt_strategies_file, "Creating prompt strategies file"),
            (self.install_dependencies, "Installing dependencies"),
            (self.init_database, "Initializing database"),
        ]
        for step_func, step_name in steps:
            logger.info(f"Executing: {step_name}")
            if not step_func():
                logger.error(f"Initialization failed at step: {step_name}")
                return False

        logger.info("AltDOGE initialization completed successfully")
        return True


if __name__ == "__main__":
    initializer = AltDOGEInitializer()
    success = initializer.run()
    sys.exit(0 if success else 1)
